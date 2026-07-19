"""
Self-Play RL Policy Training
=============================
Trains a lightweight neural network to make decisions via self-play.

Architecture: 2-layer MLP (small enough to hardcode in main.py)
Input:  20 game state features (hand size, HP, energy, prizes, etc.)
Output: Score for each available action

Training: Self-play → collect games → train on (state, action, reward) → repeat

Usage:
  1. Implement GameSimulator wrapper (or use existing simulator)
  2. Run: python rl_policy.py
  3. Export: hardcoded numpy arrays → paste into main.py
"""

import random, math, time, json, struct, base64
from collections import defaultdict, deque
from itertools import count

# NumPy is required for training but NOT for inference (we hardcode weights)
import numpy as np


# ══════════════════════════════════════════════════════════════════════════════
# Neural Network (for training)
# ══════════════════════════════════════════════════════════════════════════════

class MLP:
    """2-layer MLP. Small enough to hardcode in main.py as array operations."""
    
    def __init__(self, input_dim=20, hidden_dim=32, output_dim=1):
        # He initialization
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, output_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(output_dim)
    
    def forward(self, x):
        """x: (input_dim,) → scalar score"""
        h = np.maximum(0, x @ self.W1 + self.b1)  # ReLU
        return (h @ self.W2 + self.b2)[0]
    
    def get_params(self):
        return [self.W1, self.b1, self.W2, self.b2]
    
    def set_params(self, params):
        self.W1, self.b1, self.W2, self.b2 = [p.copy() for p in params]
    
    def export_hardcoded(self):
        """Generate Python code that recreates this network without numpy imports."""
        lines = ["# Auto-generated RL policy weights", ""]
        
        for name, arr in [('W1', self.W1), ('b1', self.b1), ('W2', self.W2), ('b2', self.b2)]:
            flat = arr.flatten()
            # Base64 encode for compact storage
            data = base64.b64encode(flat.astype(np.float32).tobytes()).decode()
            lines.append(f"# {name}: shape={list(arr.shape)}")
            lines.append(f"_{name}_data = __import__('base64').b64decode('{data}')")
            lines.append(f"_{name} = __import__('struct').unpack(f'<{len(flat)}f', _{name}_data)")
            lines.append("")
        
        # ReLU forward pass
        lines.append("def policy_score(features):")
        lines.append("    # 20-dim input → 32-dim hidden → 1-dim output")
        lines.append("    h = [0.0] * 32")
        lines.append("    for i in range(32):")
        lines.append("        s = _b1[i]")
        lines.append("        for j in range(20):")
        lines.append("            s += features[j] * _W1[j * 32 + i]")
        lines.append("        h[i] = s if s > 0 else 0.0  # ReLU")
        lines.append("    score = _b2[0]")
        lines.append("    for i in range(32):")
        lines.append("        score += h[i] * _W2[i]")
        lines.append("    return score")
        
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Game State Feature Extractor
# ══════════════════════════════════════════════════════════════════════════════

def extract_features(obs_dict, my_index):
    """
    Extract 20 numerical features from game observation.
    Same extraction must run in main.py for inference.
    """
    state = obs_dict  # Adjust based on your observation format
    my = state['players'][my_index] if 'players' in state else state
    
    features = [
        # Hand & deck
        len(my.get('hand', [])),
        len(my.get('deck', [])),
        len(my.get('discard', [])),
        len(my.get('prize', [])),
        len(my.get('bench', [])),
        
        # Active Pokémon
        my.get('active', {}).get('hp', 0) / 400.0 if my.get('active') else 0,
        len(my.get('active', {}).get('energies', [])) if my.get('active') else 0,
        
        # Bench stats
        sum(p.get('hp', 0) for p in my.get('bench', [])) / 800.0 if my.get('bench') else 0,
        sum(len(p.get('energies', [])) for p in my.get('bench', [])) if my.get('bench') else 0,
        
        # Opponent
        len(state.get('players', [{}])[1 - my_index].get('bench', [])),
        state.get('players', [{}])[1 - my_index].get('active', {}).get('hp', 0) / 400.0 if state.get('players', [{}])[1 - my_index].get('active') else 0,
        
        # Game state
        state.get('turn', 0) / 20.0,
        1.0 if my_index == 0 else 0.0,  # Going first?
        
        # Energy in hand
        sum(1 for c in my.get('hand', []) if 'Energy' in str(c.get('type', ''))),
        
        # Pokémon in hand
        sum(1 for c in my.get('hand', []) if c.get('hp', 0) > 0),
        
        # Trainer cards in hand
        sum(1 for c in my.get('hand', []) if c.get('hp', 0) == 0 and 'Energy' not in str(c.get('type', ''))),
        
        # Can evolve?
        1.0 if any(c.get('stage', '') in ('Stage 1', 'Stage 2') for c in my.get('hand', [])) else 0.0,
        
        # Prize differential
        (len(state.get('players', [{}])[1 - my_index].get('prize', [])) - len(my.get('prize', []))) / 6.0,
        
        # Turn phase
        state.get('turn', 0) / 3.0 if state.get('turn', 0) <= 12 else 4.0,
        
        # Active can attack? (has enough energy)
        1.0 if (my.get('active') and len(my.get('active', {}).get('energies', [])) >= 2) else 0.0,
    ]
    
    # Pad/truncate to exactly 20
    features = features[:20]
    while len(features) < 20:
        features.append(0.0)
    
    return np.array(features, dtype=np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# Training
# ══════════════════════════════════════════════════════════════════════════════

class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
    
    def add(self, state, action, reward):
        self.buffer.append((state, action, reward))
    
    def sample(self, batch_size=64):
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        states = np.stack([b[0] for b in batch])
        rewards = np.array([b[2] for b in batch])
        return states, rewards
    
    def __len__(self):
        return len(self.buffer)


def train_policy(evaluate_game, iterations=1000, games_per_iteration=10):
    """
    Train policy via self-play.
    
    Args:
        evaluate_game: function(policy) -> list of (state_features, action_idx, won: bool)
        iterations: training iterations
        games_per_iteration: self-play games per iteration
    """
    policy = MLP(input_dim=20, hidden_dim=32, output_dim=1)
    buffer = ReplayBuffer(capacity=5000)
    best_winrate = 0
    best_policy = None
    
    # Simple SGD
    learning_rate = 0.01
    
    print(f"Training RL policy: {iterations} iterations × {games_per_iteration} games")
    
    for iteration in range(iterations):
        t0 = time.time()
        
        # Self-play: collect experience
        wins = 0
        for _ in range(games_per_iteration):
            # Run game with current policy (epsilon-greedy)
            epsilon = max(0.05, 0.5 * (0.995 ** iteration))
            
            # Simulate one game — you need to implement this
            # game_states = run_one_game(policy, epsilon)
            # for state, action, won in game_states:
            #     reward = 1.0 if won else -1.0
            #     buffer.add(state, action, reward)
            #     if won: wins += 1
            pass  # Replace with actual game simulation
        
        # Train on replay buffer
        if len(buffer) >= 64:
            states, rewards = buffer.sample(64)
            
            # Simple regression: predict reward from state
            predictions = np.array([policy.forward(s) for s in states])
            
            # Gradient update (MSE loss)
            error = predictions - rewards
            grad_w2 = np.zeros_like(policy.W2)
            grad_b2 = np.zeros_like(policy.b2)
            grad_w1 = np.zeros_like(policy.W1)
            grad_b1 = np.zeros_like(policy.b1)
            
            for i in range(len(states)):
                x = states[i]
                e = error[i]
                
                # Forward pass (with gradient tracking)
                h = np.maximum(0, x @ policy.W1 + policy.b1)
                
                # Gradients for W2, b2
                grad_w2 += e * h.reshape(-1, 1)
                grad_b2 += np.array([e])
                
                # Gradients for W1, b1 (ReLU backward)
                dh = e * policy.W2.flatten()
                dh[h <= 0] = 0
                grad_w1 += np.outer(x, dh)
                grad_b1 += dh
            
            # Update
            policy.W1 -= learning_rate * grad_w1 / len(states)
            policy.b1 -= learning_rate * grad_b1 / len(states)
            policy.W2 -= learning_rate * grad_w2 / len(states)
            policy.b2 -= learning_rate * grad_b2 / len(states)
        
        winrate = wins / games_per_iteration if games_per_iteration > 0 else 0
        
        if winrate > best_winrate:
            best_winrate = winrate
            best_policy = MLP()
            best_policy.set_params(policy.get_params())
        
        elapsed = time.time() - t0
        if iteration % 10 == 0:
            print(f"  iter {iteration:4d} | winrate={winrate:.3f} best={best_winrate:.3f} | buffer={len(buffer)} | {elapsed:.1f}s")
    
    return best_policy or policy


# ══════════════════════════════════════════════════════════════════════════════
# Export
# ══════════════════════════════════════════════════════════════════════════════

def export_policy(policy, path="policy_weights.py"):
    """Export trained policy as hardcoded Python code."""
    code = policy.export_hardcoded()
    with open(path, 'w') as f:
        f.write(code)
    print(f"Policy exported to {path}")
    print("Copy the policy_score() function into main.py")


if __name__ == "__main__":
    print("RL Policy Trainer ready.")
    print("Architecture: 20 → 32 → 1 (MLP)")
    print("Parameters:", 20*32 + 32 + 32*1 + 1, "total")
    print()
    print("Steps:")
    print("  1. Implement run_one_game() using your simulator")
    print("  2. Run train_policy()")
    print("  3. export_policy() → paste into main.py")
