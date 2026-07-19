"""
Evolutionary Deck Optimizer
============================
Genetic algorithm that finds the optimal 60-card deck using your simulator
as the fitness function.

Quickstart:
  1. Put EN_Card_Data.csv in this directory
  2. Replace evaluate_deck() with your simulator call (line ~60)
  3. python deck_search.py

Your simulator runs 1,500 games/sec, so 50 decks × 10 opponents × 10 games
= 5,000 games per generation ≈ 3 seconds. 200 generations ≈ 10 minutes.
"""

import random, json, time, os, pickle
from collections import Counter
from pathlib import Path
import pandas as pd

# ── Card Database ────────────────────────────────────────────────────────────
# Try multiple paths for the card data CSV
for db_path in ["EN_Card_Data.csv", "../EN_Card_Data (1).csv",
                "/kaggle/input/datasets/kiyotah/en-card-data/EN_Card_Data.csv"]:
    if os.path.exists(db_path):
        CARD_DB = pd.read_csv(db_path)
        break
else:
    raise FileNotFoundError("EN_Card_Data.csv not found. Place it in train/ or parent dir.")

STAGE_COL = 'Stage (Pokémon)/Type (Energy and Trainer)'

# Parse card types
BASIC_POKEMON   = set(CARD_DB[CARD_DB[STAGE_COL] == 'Basic Pokémon']['Card ID'])
STAGE1_POKEMON  = set(CARD_DB[CARD_DB[STAGE_COL] == 'Stage 1 Pokémon']['Card ID'])
STAGE2_POKEMON  = set(CARD_DB[CARD_DB[STAGE_COL] == 'Stage 2 Pokémon']['Card ID'])
ALL_POKEMON     = BASIC_POKEMON | STAGE1_POKEMON | STAGE2_POKEMON
TRAINERS        = set(CARD_DB[CARD_DB[STAGE_COL].isin(
    ['Item', 'Supporter', 'Pokémon Tool', 'Stadium'])]['Card ID'])
ENERGY          = set(CARD_DB[CARD_DB[STAGE_COL].str.contains('Energy', na=False)]['Card ID'])
VALID_IDS       = set(CARD_DB['Card ID'])

# Evolution chain lookup: Stage 2 → Stage 1 → Basic
PREV_STAGE = dict(zip(CARD_DB['Card ID'], CARD_DB['Previous stage']))
PREV_NAME  = {}
for _, row in CARD_DB.iterrows():
    if pd.notna(row.get('Previous stage')):
        prev_name = str(row['Previous stage']).strip()
        if prev_name:
            PREV_NAME[row['Card ID']] = prev_name

# Build evolution chains: given a Stage 2 ID, find its Basic
def get_evo_chain(card_id):
    """Return set of pre-evolutions needed for a given evolution card."""
    chain = set()
    current = card_id
    for _ in range(2):
        prev = PREV_STAGE.get(current)
        if pd.isna(prev):
            break
        # Find card IDs matching the previous stage name
        prev_name = PREV_NAME.get(current, '')
        prev_ids = set(CARD_DB[(CARD_DB['Card Name'] == prev_name) & 
                                (CARD_DB['Card ID'].isin(BASIC_POKEMON | STAGE1_POKEMON))
                               ]['Card ID'])
        if prev_ids:
            chain.update(prev_ids)
            current = list(prev_ids)[0]
        else:
            break
    return chain

# Precompute chains for all evolution cards
EVO_CHAIN = {}
for cid in STAGE1_POKEMON | STAGE2_POKEMON:
    chain = get_evo_chain(cid)
    if chain:
        EVO_CHAIN[cid] = chain

# Card metadata for reporting
ID_TO_NAME = dict(zip(CARD_DB['Card ID'], CARD_DB['Card Name']))
ID_TO_STAGE = dict(zip(CARD_DB['Card ID'], CARD_DB[STAGE_COL]))

# ── Configuration ────────────────────────────────────────────────────────────
POPULATION_SIZE = 50
GENERATIONS     = 200
MUTATION_RATE   = 0.12
CROSSOVER_RATE  = 0.65
ELITE_SIZE      = 5
TOURNAMENT_SIZE = 4
PATIENCE        = 30  # Stop if no improvement for N generations

# ── Deck Generation ──────────────────────────────────────────────────────────
def random_deck():
    """Generate a random 60-card deck with reasonable type ratios."""
    deck = []
    n_energy    = random.randint(16, 22)
    n_basic     = random.randint(8, 14)
    n_stage1    = random.randint(0, 4)
    n_stage2    = random.randint(0, 2)
    
    deck.extend(random.choices(list(ENERGY), k=n_energy))
    deck.extend(random.choices(list(BASIC_POKEMON), k=n_basic))
    deck.extend(random.choices(list(STAGE1_POKEMON), k=n_stage1))
    deck.extend(random.choices(list(STAGE2_POKEMON), k=n_stage2))
    
    # Fill remaining slots with trainers
    n_remaining = 60 - len(deck)
    if n_remaining > 0:
        deck.extend(random.choices(list(TRAINERS), k=n_remaining))
    deck = deck[:60]
    deck = repair_deck(deck)
    random.shuffle(deck)
    return deck

def seed_deck(card_id, count, energy_id=2, support_ids=None):
    """Create a seed deck focused on one attacker with its evolution line."""
    deck = [card_id] * count
    
    # Add pre-evolutions if needed
    if card_id in EVO_CHAIN:
        for pre_id in EVO_CHAIN[card_id]:
            stage = ID_TO_STAGE.get(pre_id, '')
            copies = 3 if 'Basic' in str(stage) else 2
            deck.extend([pre_id] * copies)
    
    deck.extend([energy_id] * 18)
    
    # Add key support cards if specified
    if support_ids:
        for sid, scount in support_ids:
            deck.extend([sid] * scount)
    
    # Fill with random trainers
    while len(deck) < 60:
        deck.append(random.choice(list(TRAINERS)))
    return deck[:60]

def repair_deck(deck):
    """Remove orphaned evolutions (no basic), ensure at least 1 basic + 1 energy."""
    deck = deck.copy()
    counts = Counter(deck)
    
    # Remove evolution cards that have no basic in deck
    for cid in list(counts):
        if cid in (STAGE1_POKEMON | STAGE2_POKEMON):
            if cid in EVO_CHAIN:
                if not any(pre_id in counts for pre_id in EVO_CHAIN[cid]):
                    # Remove orphaned evolutions
                    deck = [c for c in deck if c != cid]
                    counts = Counter(deck)
    
    # Ensure at least 1 Basic Pokémon
    if not any(cid in BASIC_POKEMON for cid in deck):
        deck.append(random.choice(list(BASIC_POKEMON)))
    
    # Ensure at least 1 Energy
    if not any(cid in ENERGY for cid in deck):
        deck.append(random.choice(list(ENERGY)))
    
    # Trim or pad to exactly 60
    while len(deck) < 60:
        deck.append(random.choice(list(TRAINERS)))
    return deck[:60]

# ── Genetic Operators ────────────────────────────────────────────────────────
def mutate(deck):
    """Mutate by swapping individual cards, biased toward valid categories."""
    deck = deck.copy()
    for i in range(len(deck)):
        if random.random() < MUTATION_RATE:
            r = random.random()
            if r < 0.25:
                deck[i] = random.choice(list(ENERGY))
            elif r < 0.55:
                deck[i] = random.choice(list(BASIC_POKEMON))
            elif r < 0.65:
                deck[i] = random.choice(list(STAGE1_POKEMON))
            elif r < 0.70:
                deck[i] = random.choice(list(STAGE2_POKEMON))
            else:
                deck[i] = random.choice(list(TRAINERS))
    return repair_deck(deck)

def crossover(parent1, parent2):
    """Two-point crossover: take segments from each parent."""
    p1, p2 = random.randint(5, 25), random.randint(30, 55)
    child = parent1[:p1] + parent2[p1:p2] + parent1[p2:]
    if len(child) < 60:
        child.extend(random.choices(parent1, k=60 - len(child)))
    return repair_deck(child[:60])

def tournament_select(population, fitnesses):
    """Tournament selection with size TOURNAMENT_SIZE."""
    candidates = random.sample(range(len(population)), 
                               min(TOURNAMENT_SIZE, len(population)))
    return population[max(candidates, key=lambda i: fitnesses[i])]

# ── Main Evolution Loop ──────────────────────────────────────────────────────
def run_evolution(evaluate_deck, population=None, generations=GENERATIONS,
                  checkpoint_path="evo_checkpoint.pkl"):
    """
    Run evolutionary deck optimization.
    
    Args:
        evaluate_deck: function(deck: list[int]) -> float  (win rate 0-1)
        population: initial population (list of decks), or None for random init
        generations: max generations
        checkpoint_path: path to save/load progress
    
    Returns:
        best_deck, best_fitness, history
    """
    # Resume from checkpoint if available
    start_gen = 0
    history = []
    best_overall = None
    best_overall_fitness = -1
    stale_generations = 0
    
    if os.path.exists(checkpoint_path):
        print(f"Resuming from checkpoint: {checkpoint_path}")
        ckpt = pickle.load(open(checkpoint_path, 'rb'))
        population = ckpt['population']
        start_gen = ckpt['generation'] + 1
        history = ckpt.get('history', [])
        best_overall = ckpt.get('best_deck')
        best_overall_fitness = ckpt.get('best_fitness', -1)
        stale_generations = ckpt.get('stale_generations', 0)
    
    if population is None:
        population = [random_deck() for _ in range(POPULATION_SIZE - 6)]
        # Strong seed decks to guide early search
        seeds = [
            seed_deck(46, 4),           # Gouging Fire ex (Basic, fast)
            seed_deck(678, 3),          # Mega Lucario ex (Stage 1, 2 energy)
            seed_deck(662, 3),          # Mega Camerupt ex (Stage 1, Fire)
            seed_deck(107, 3),          # Palafin ex (Stage 1, Water)
            seed_deck(44, 4),           # Bloodmoon Ursaluna ex (Basic, Colorless)
            seed_deck(313, 3),          # Miraidon ex (Basic, Dragon)
        ]
        population.extend(seeds)
    
    population = population[:POPULATION_SIZE]
    evaluated = {}  # Cache: deck signature → fitness
    
    print(f"Card pool: {len(VALID_IDS)} total")
    print(f"  Basic: {len(BASIC_POKEMON)} | Stage1: {len(STAGE1_POKEMON)} | Stage2: {len(STAGE2_POKEMON)}")
    print(f"  Trainers: {len(TRAINERS)} | Energy: {len(ENERGY)}")
    print(f"Evolution: {generations} gens × {POPULATION_SIZE} decks = {generations * POPULATION_SIZE} evals")
    print()
    
    for gen in range(start_gen, generations):
        t0 = time.time()
        
        # Evaluate population (with caching)
        fitnesses = []
        cache_hits = 0
        for deck in population:
            sig = tuple(sorted(Counter(deck).items()))
            if sig in evaluated:
                fitnesses.append(evaluated[sig])
                cache_hits += 1
            else:
                fitness = evaluate_deck(deck)
                evaluated[sig] = fitness
                fitnesses.append(fitness)
        
        # Track best
        best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        gen_best = fitnesses[best_idx]
        avg_fitness = sum(fitnesses) / len(fitnesses)
        diversity = len(set(tuple(sorted(Counter(d).items())) for d in population))
        
        improved = False
        if gen_best > best_overall_fitness + 0.001:
            best_overall_fitness = gen_best
            best_overall = population[best_idx].copy()
            improved = True
            stale_generations = 0
            
            # Save best deck immediately
            counts = Counter(best_overall)
            deck_path = f"best_deck_gen{gen:03d}.csv"
            with open(deck_path, 'w') as f:
                for cid in best_overall:
                    f.write(f"{cid}\n")
            print(f"  >>> SAVED: {deck_path}")
            
            # Print deck summary
            n_poke = sum(1 for cid in best_overall if cid in ALL_POKEMON)
            n_nrg  = sum(1 for cid in best_overall if cid in ENERGY)
            n_tr   = sum(1 for cid in best_overall if cid in TRAINERS)
            top = counts.most_common(5)
            cards_str = ", ".join(f"{ID_TO_NAME.get(c, '?')}×{n}" for c, n in top)
            print(f"  >>> P{n_poke} E{n_nrg} T{n_tr} | {cards_str}")
        else:
            stale_generations += 1
        
        elapsed = time.time() - t0
        
        print(f"  Gen {gen:3d} | best={gen_best:.4f} avg={avg_fitness:.4f} "
              f"div={diversity}/{POPULATION_SIZE} cache={cache_hits} | {elapsed:.1f}s")
        
        history.append({
            'generation': gen, 'best_fitness': gen_best,
            'avg_fitness': avg_fitness, 'diversity': diversity,
        })
        
        # Early stopping
        if stale_generations >= PATIENCE and gen > 50:
            print(f"\nNo improvement for {PATIENCE} generations. Converged.")
            break
        
        if gen == generations - 1:
            break
        
        # Create next generation
        next_pop = []
        
        # Elitism: carry forward best decks
        sorted_idx = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
        for i in sorted_idx[:ELITE_SIZE]:
            next_pop.append(population[i].copy())
        
        # Fill with crossover + mutation
        attempts = 0
        while len(next_pop) < POPULATION_SIZE and attempts < POPULATION_SIZE * 5:
            if random.random() < CROSSOVER_RATE and len(population) >= 2:
                p1 = tournament_select(population, fitnesses)
                p2 = tournament_select(population, fitnesses)
                child = crossover(p1, p2)
            else:
                parent = tournament_select(population, fitnesses)
                child = mutate(parent.copy())
            
            # Check uniqueness (avoid duplicate decks in population)
            child_sig = tuple(sorted(Counter(child).items()))
            if child_sig not in [tuple(sorted(Counter(d).items())) for d in next_pop]:
                next_pop.append(child)
            attempts += 1
        
        # Fill any remaining slots with random decks
        while len(next_pop) < POPULATION_SIZE:
            next_pop.append(random_deck())
        
        population = next_pop
        
        # Save checkpoint every 10 generations
        if gen % 10 == 0:
            pickle.dump({
                'population': population, 'generation': gen,
                'history': history, 'best_deck': best_overall,
                'best_fitness': best_overall_fitness,
                'stale_generations': stale_generations,
            }, open(checkpoint_path, 'wb'))
    
    return best_overall, best_overall_fitness, history


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION POINT — Replace this function with your simulator call
# ══════════════════════════════════════════════════════════════════════════════

# Example opponent decks to test against (add real deck lists)
OPPONENT_DECKS = [
    # [card_id1, card_id2, ...] × 60  — your strongest known opponent decks
]

def evaluate_deck(deck):
    """
    Run your simulator with this deck against opponents.
    
    Args:
        deck: list of 60 card IDs
    
    Returns:
        float: win rate from 0.0 to 1.0
    
    IMPLEMENT THIS: Replace with your actual simulator integration.
    
    Example:
        # Save deck to temp file
        with open('/tmp/test_deck.csv', 'w') as f:
            for cid in deck:
                f.write(f'{cid}\\n')
        
        # Run simulator
        wins = 0
        total = 0
        for opp_deck in OPPONENT_DECKS:
            with open('/tmp/opp_deck.csv', 'w') as f:
                for cid in opp_deck:
                    f.write(f'{cid}\\n')
            
            result = your_simulator.run(
                deck1='/tmp/test_deck.csv',
                deck2='/tmp/opp_deck.csv',
                games=10,
                position_balanced=True,
            )
            wins += result.wins
            total += result.games
        
        return wins / total if total > 0 else 0.0
    """
    # PLACEHOLDER — returns random fitness for testing structure
    return random.random()


# ══════════════════════════════════════════════════════════════════════════════
# Run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    best_deck, fitness, history = run_evolution(evaluate_deck)
    
    print(f"\n{'='*60}")
    print(f"EVOLUTION COMPLETE — best fitness: {fitness:.4f}")
    print(f"{'='*60}")
    print()
    
    # Final deck breakdown
    counts = Counter(best_deck)
    print("FINAL DECK:")
    for cid, count in sorted(counts.items()):
        name = ID_TO_NAME.get(cid, f"Unknown-{cid}")
        stage = ID_TO_STAGE.get(cid, '')
        print(f"  {count:2d}x {name:<30s} {stage}")
    
    n_basic = sum(1 for cid in best_deck if cid in BASIC_POKEMON)
    n_evo   = sum(1 for cid in best_deck if cid in (STAGE1_POKEMON | STAGE2_POKEMON))
    n_energy = sum(1 for cid in best_deck if cid in ENERGY)
    n_trainer = sum(1 for cid in best_deck if cid in TRAINERS)
    print(f"\n  Pokémon: {n_basic+n_evo} ({n_basic} basic + {n_evo} evolution)")
    print(f"  Energy: {n_energy}")
    print(f"  Trainers: {n_trainer}")
    
    # Save final deck
    with open("best_deck_final.csv", 'w') as f:
        for cid in best_deck:
            f.write(f"{cid}\n")
    print(f"\nSaved: best_deck_final.csv")
    
    # Plot fitness history if matplotlib available
    try:
        import matplotlib.pyplot as plt
        gens = [h['generation'] for h in history]
        bests = [h['best_fitness'] for h in history]
        avgs = [h['avg_fitness'] for h in history]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(gens, bests, 'b-', linewidth=2, label='Best fitness')
        ax.plot(gens, avgs, 'orange', alpha=0.6, label='Avg fitness')
        ax.fill_between(gens, avgs, bests, alpha=0.1, color='blue')
        ax.set_xlabel('Generation')
        ax.set_ylabel('Win Rate')
        ax.set_title('Deck Evolution Progress')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('evolution_progress.png', dpi=120)
        print("Saved: evolution_progress.png")
    except ImportError:
        pass
