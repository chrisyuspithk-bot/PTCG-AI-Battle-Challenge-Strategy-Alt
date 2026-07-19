"""
Evolutionary Deck Optimizer
============================
Finds the optimal 60-card deck via genetic algorithm.

Usage:
  1. Implement evaluate_deck(deck) → float  (win rate 0-1)
  2. Run: python deck_search.py
  3. Best deck saved to best_deck.csv

The evaluate_deck function should run your simulator with the given deck
against a diverse set of opponents and return the win rate.
"""

import random, json, time
from collections import Counter
from pathlib import Path

# ── Card Pool ────────────────────────────────────────────────────────────────
# Load valid card IDs from the competition database
import pandas as pd

CARD_DB = pd.read_csv("EN_Card_Data.csv")  # Adjust path if needed
VALID_IDS = set(CARD_DB['Card ID'].tolist())

# Separate cards by type for smart mutation
BASIC_POKEMON = set(CARD_DB[CARD_DB['Stage (Pokémon)/Type (Energy and Trainer)'] == 'Basic Pokémon']['Card ID'])
EVOLUTION_POKEMON = set(CARD_DB[CARD_DB['Stage (Pokémon)/Type (Energy and Trainer)'].str.contains('Stage', na=False)]['Card ID'])
TRAINERS = set(CARD_DB[CARD_DB['Stage (Pokémon)/Type (Energy and Trainer)'].isin(['Item', 'Supporter', 'Pokémon Tool', 'Stadium'])]['Card ID'])
ENERGY = set(CARD_DB[CARD_DB['Stage (Pokémon)/Type (Energy and Trainer)'].str.contains('Energy', na=False)]['Card ID'])

# ── Configuration ────────────────────────────────────────────────────────────
POPULATION_SIZE = 50
GENERATIONS = 200
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.6
ELITE_SIZE = 5
TOURNAMENT_SIZE = 4

# ── Deck Generation ──────────────────────────────────────────────────────────
def random_deck():
    """Generate a random 60-card deck."""
    deck = []
    # 12-20 energy
    n_energy = random.randint(16, 22)
    deck.extend([random.choice(list(ENERGY)) for _ in range(n_energy)])
    # 8-16 basic pokemon
    n_basic = random.randint(8, 14)
    deck.extend([random.choice(list(BASIC_POKEMON)) for _ in range(n_basic)])
    # 0-6 evolution pokemon
    n_evo = random.randint(0, 4)
    if n_evo:
        deck.extend([random.choice(list(EVOLUTION_POKEMON)) for _ in range(n_evo)])
    # Fill rest with trainers
    n_trainer = 60 - len(deck)
    deck.extend([random.choice(list(TRAINERS)) for _ in range(n_trainer)])
    random.shuffle(deck)
    assert len(deck) == 60
    return deck

def seed_deck(card_id, count, energy_id=2):
    """Create a seed deck focused on one attacker."""
    deck = [card_id] * count
    deck.extend([energy_id] * 18)
    # Fill with random trainers
    while len(deck) < 60:
        deck.append(random.choice(list(TRAINERS)))
    return deck[:60]

# ── Genetic Operators ────────────────────────────────────────────────────────
def mutate(deck):
    """Mutate a deck by swapping cards."""
    deck = deck.copy()
    for i in range(len(deck)):
        if random.random() < MUTATION_RATE:
            r = random.random()
            if r < 0.3:
                deck[i] = random.choice(list(BASIC_POKEMON))
            elif r < 0.5:
                deck[i] = random.choice(list(ENERGY))
            elif r < 0.85:
                deck[i] = random.choice(list(TRAINERS))
            else:
                deck[i] = random.choice(list(EVOLUTION_POKEMON))
    return deck

def crossover(parent1, parent2):
    """Crossover two decks: take half from each parent."""
    split = random.randint(20, 40)
    child = parent1[:split] + parent2[split:]
    # Ensure exactly 60 cards
    if len(child) < 60:
        child.extend(random.choices(parent1, k=60 - len(child)))
    return child[:60]

def tournament_select(population, fitnesses, k=TOURNAMENT_SIZE):
    """Select parent via tournament selection."""
    candidates = random.sample(range(len(population)), k)
    return population[max(candidates, key=lambda i: fitnesses[i])]

# ── Validation ───────────────────────────────────────────────────────────────
def is_valid_deck(deck):
    """Check deck meets basic constraints."""
    counts = Counter(deck)
    if len(deck) != 60:
        return False
    if not any(cid in BASIC_POKEMON for cid in deck):
        return False  # Must have at least 1 Basic Pokémon
    if not any(cid in ENERGY for cid in deck):
        return False  # Must have energy
    if not all(cid in VALID_IDS for cid in deck):
        return False
    return True

# ── Main Loop ────────────────────────────────────────────────────────────────
def run_evolution(evaluate_deck, population=None, generations=GENERATIONS):
    """
    Run evolutionary deck optimization.
    
    Args:
        evaluate_deck: function(deck: list[int]) -> float  (win rate 0-1)
        population: initial population (list of decks), or None for random init
        generations: number of generations to run
    
    Returns:
        best_deck, best_fitness, history
    """
    if population is None:
        population = [random_deck() for _ in range(POPULATION_SIZE)]
        # Add seed decks
        population.append(seed_deck(46, 4))   # Gouging Fire ex
        population.append(seed_deck(678, 4))  # Mega Lucario ex
        population.append(seed_deck(932, 3))  # Mega Emboar ex
    
    population = population[:POPULATION_SIZE]
    history = []
    best_overall = None
    best_overall_fitness = -1
    
    print(f"Starting evolution: {generations} generations, {len(population)} population")
    print(f"Evaluating {len(population)} decks per generation")
    
    for gen in range(generations):
        t0 = time.time()
        
        # Evaluate fitness
        fitnesses = []
        for i, deck in enumerate(population):
            if not is_valid_deck(deck):
                fitnesses.append(0.0)
            else:
                fitnesses.append(evaluate_deck(deck))
        
        # Track best
        best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        gen_best = fitnesses[best_idx]
        
        if gen_best > best_overall_fitness:
            best_overall_fitness = gen_best
            best_overall = population[best_idx].copy()
        
        # Stats
        avg_fitness = sum(fitnesses) / len(fitnesses)
        elapsed = time.time() - t0
        
        history.append({
            'generation': gen,
            'best_fitness': gen_best,
            'avg_fitness': avg_fitness,
            'best_deck_counts': dict(Counter(population[best_idx])),
        })
        
        print(f"  Gen {gen:3d} | best={gen_best:.4f} avg={avg_fitness:.4f} | {elapsed:.1f}s")
        
        if gen == generations - 1:
            break
        
        # Create next generation
        next_pop = []
        
        # Elitism: keep best
        sorted_idx = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
        for i in sorted_idx[:ELITE_SIZE]:
            next_pop.append(population[i].copy())
        
        # Fill rest with crossover + mutation
        while len(next_pop) < POPULATION_SIZE:
            if random.random() < CROSSOVER_RATE:
                p1 = tournament_select(population, fitnesses)
                p2 = tournament_select(population, fitnesses)
                child = crossover(p1, p2)
            else:
                child = tournament_select(population, fitnesses).copy()
            
            child = mutate(child)
            if is_valid_deck(child):
                next_pop.append(child)
        
        population = next_pop
    
    return best_overall, best_overall_fitness, history

# ── Export ────────────────────────────────────────────────────────────────────
def save_deck(deck, path="best_deck.csv"):
    """Save deck to CSV file."""
    with open(path, 'w') as f:
        for card_id in deck:
            f.write(f"{card_id}\n")
    
    # Print summary
    counts = Counter(deck)
    print(f"\nBest deck saved to {path}")
    print(f"Win rate: {best_overall_fitness:.4f}" if 'best_overall_fitness' in dir() else "")
    
    # Show card names
    id_to_name = dict(zip(CARD_DB['Card ID'], CARD_DB['Card Name']))
    for cid, count in sorted(counts.items()):
        name = id_to_name.get(cid, f"Unknown-{cid}")
        print(f"  {count:2d}x {name} (ID {cid})")

# ── Example evaluator (replace with your simulator) ──────────────────────────
def dummy_evaluate(deck):
    """Placeholder — replace with your simulator call."""
    # Your code:
    # result = run_simulator(deck, opponent_decks, games_per_matchup=10)
    # return result.win_rate
    return random.random()  # Replace this!


if __name__ == "__main__":
    print("Deck Search ready.")
    print(f"Card pool: {len(VALID_IDS)} cards")
    print(f"  Basic Pokémon: {len(BASIC_POKEMON)}")
    print(f"  Evolution: {len(EVOLUTION_POKEMON)}")
    print(f"  Trainers: {len(TRAINERS)}")
    print(f"  Energy: {len(ENERGY)}")
    print()
    print("Replace dummy_evaluate() with your simulator call, then:")
    print("  best_deck, fitness, history = run_evolution(dummy_evaluate)")
