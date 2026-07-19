"""
Phase Weight Optimizer
=======================
Tunes the W (phase weight) matrix using black-box optimization.

Usage:
  1. Copy your agent's W dict and evaluate_weights function
  2. Run: python weight_tuner.py
  3. Best weights printed — paste into main.py

Strategy:
  - Random search for exploration (first N iterations)
  - Hill climbing with restarts for exploitation
  - Designed for noisy fitness (simulator win rates have variance)
"""

import random, math, time, json
from copy import deepcopy
from itertools import product

# ── Current weights (from main.py) ──────────────────────────────────────────
BASE_WEIGHTS = {
    'opening':     {'attack': 0,    'energy': 5000,  'evolve': 3000,  'draw': 3000,  'search': 2500, 'boss': 0},
    'development': {'attack': 500,  'energy': 6000,  'evolve': 4000,  'draw': 2000,  'search': 2000, 'boss': 1000},
    'aggression':  {'attack': 20000,'energy': 3000,  'evolve': 2000,  'draw': 1000,  'search': 1000, 'boss': 3000},
    'endgame':     {'attack': 50000,'energy': 0,     'evolve': 0,     'draw': 500,   'search': 500,  'boss': 5000},
}

PHASES = list(BASE_WEIGHTS.keys())
ACTIONS = list(BASE_WEIGHTS['opening'].keys())

# ── Weight space definition ─────────────────────────────────────────────────
# Each weight has: (min, max, step) for discrete search, or (min, max) for continuous
WEIGHT_RANGES = {
    'attack':  (0, 100000),
    'energy':  (0, 20000),
    'evolve':  (0, 10000),
    'draw':    (0, 10000),
    'search':  (0, 10000),
    'boss':    (0, 20000),
}

def random_weights():
    """Generate random weight matrix."""
    w = {}
    for phase in PHASES:
        w[phase] = {}
        for action in ACTIONS:
            lo, hi = WEIGHT_RANGES[action]
            # Log-uniform sampling for wide ranges
            if hi / max(lo, 1) > 100:
                w[phase][action] = int(10 ** random.uniform(math.log10(max(lo, 1)), math.log10(hi)))
            else:
                w[phase][action] = random.randint(lo, hi)
    return w

def mutate_weights(w, scale=0.3):
    """Mutate weights by multiplying/dividing or adding/subtracting."""
    new_w = deepcopy(w)
    for phase in PHASES:
        for action in ACTIONS:
            if random.random() < 0.3:  # Mutate ~30% of weights
                lo, hi = WEIGHT_RANGES[action]
                if random.random() < 0.5:
                    # Multiplicative change (for large ranges)
                    factor = 1 + random.uniform(-scale, scale)
                    new_w[phase][action] = int(max(lo, min(hi, w[phase][action] * factor)))
                else:
                    # Additive change (for small ranges)
                    delta = int(random.uniform(-scale * 1000, scale * 1000))
                    new_w[phase][action] = max(lo, min(hi, w[phase][action] + delta))
    return new_w

def crossover_weights(w1, w2):
    """Crossover: take each weight from either parent."""
    child = deepcopy(w1)
    for phase in PHASES:
        for action in ACTIONS:
            if random.random() < 0.5:
                child[phase][action] = w2[phase][action]
    return child

def weights_to_flat(w):
    """Flatten weight dict to list for serialization."""
    flat = []
    for phase in PHASES:
        for action in ACTIONS:
            flat.append(w[phase][action])
    return flat

def flat_to_weights(flat):
    """Reconstruct weight dict from flat list."""
    w = {p: {} for p in PHASES}
    idx = 0
    for phase in PHASES:
        for action in ACTIONS:
            w[phase][action] = flat[idx]
            idx += 1
    return w

def format_weights(w):
    """Format weights as Python dict string for copy-paste."""
    lines = ["W = {"]
    for phase in PHASES:
        lines.append(f"    '{phase}': {{")
        items = [f"'{a}': {w[phase][a]}" for a in ACTIONS]
        lines.append("        " + ", ".join(items) + ",")
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


# ── Optimization ────────────────────────────────────────────────────────────
def optimize(evaluate_weights, iterations=500, random_frac=0.3):
    """
    Find optimal weights via random search + hill climbing.
    
    Args:
        evaluate_weights: function(weights_dict) -> float (win rate 0-1)
        iterations: total evaluations
        random_frac: fraction of iterations to use pure random search
    """
    best_w = BASE_WEIGHTS
    best_fitness = evaluate_weights(best_w)
    current_w = deepcopy(best_w)
    current_fitness = best_fitness
    
    print(f"Starting weight optimization: {iterations} iterations")
    print(f"Baseline fitness: {best_fitness:.4f}")
    
    history = []
    restart_every = max(10, iterations // 20)
    steps_since_improvement = 0
    
    for i in range(iterations):
        t0 = time.time()
        
        if i < iterations * random_frac or steps_since_improvement > restart_every:
            # Random exploration
            candidate = random_weights()
        else:
            # Hill climbing: mutate current best
            candidate = mutate_weights(current_w, scale=0.3 * (1 - i/iterations))
        
        fitness = evaluate_weights(candidate)
        
        if fitness > best_fitness:
            best_fitness = fitness
            best_w = deepcopy(candidate)
            steps_since_improvement = 0
            print(f"  [{i:4d}] NEW BEST: {fitness:.4f} (+{fitness - current_fitness:.4f})")
        else:
            steps_since_improvement += 1
        
        # Always accept improvements, sometimes accept worse (simulated annealing)
        if fitness >= current_fitness or random.random() < 0.1:
            current_w = candidate
            current_fitness = fitness
        
        history.append({'iteration': i, 'best': best_fitness, 'current': fitness})
        
        elapsed = time.time() - t0
        if i % 20 == 0:
            print(f"  [{i:4d}] best={best_fitness:.4f} curr={fitness:.4f} | {elapsed:.1f}s")
    
    print(f"\nBest fitness: {best_fitness:.4f}")
    print(format_weights(best_w))
    
    return best_w, best_fitness, history


# ── Example evaluator ────────────────────────────────────────────────────────
def dummy_evaluate(weights):
    """Placeholder — replace with your simulator call."""
    # Your code:
    # write_weights_to_agent(weights, 'main.py')
    # result = run_simulator('main.py', 'deck.csv', opponent_decks, games=50)
    # return result.win_rate
    return random.random()


if __name__ == "__main__":
    print("Weight Tuner ready.")
    print(f"Parameters: {len(PHASES)} phases × {len(ACTIONS)} actions = {len(PHASES)*len(ACTIONS)} weights")
    print()
    print("Replace dummy_evaluate() with your simulator call, then:")
    print("  best_w, fitness, history = optimize(dummy_evaluate)")
