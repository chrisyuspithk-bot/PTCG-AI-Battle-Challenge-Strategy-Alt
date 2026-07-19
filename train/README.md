# Training Framework

Three tools that use your simulator as a black-box fitness function to automatically find better decks and agents.

## Setup

```bash
pip install pandas numpy matplotlib
```

The card database CSV is already in this directory. If it's missing, copy `EN_Card_Data.csv` from the Kaggle competition dataset.

---

## 1. Deck Search — `deck_search.py`

Genetic algorithm that finds the optimal 60-card deck.

### How it works

```
Population of 50 decks
    ↓
Evaluate each deck in your simulator (win rate)
    ↓
Keep top 5 (elitism)
    ↓
Crossover + mutate to create 45 new decks
    ↓
Repeat 200 generations
    ↓
Best deck found
```

### Features

| Feature | What it does |
|---|---|
| Evolution chains | Auto-adds pre-evolutions to seed decks, removes orphaned evolutions from mutations |
| Fitness cache | Identical deck compositions evaluated once |
| Duplicate prevention | No two decks in population are the same |
| Checkpoints | Saves every 10 gens — survives crashes, resumes where it left off |
| Early stopping | Halts after 30 generations without improvement |
| Seed decks | Starts with 6 known-good decks (Gouging Fire ex, Mega Lucario ex, etc.) |
| Progress chart | Outputs `evolution_progress.png` |

### Integration — the only code you write

Open `deck_search.py`, find `evaluate_deck()` at ~line 325, and replace it:

```python
# Add your known opponent decks here
OPPONENT_DECKS = [
    # list of 60 card IDs each — decks your simulator can play against
]

def evaluate_deck(deck):
    """deck: list of 60 card IDs → returns win rate 0.0 to 1.0"""
    
    # Save deck to temp file
    with open('/tmp/test_deck.csv', 'w') as f:
        for cid in deck:
            f.write(f'{cid}\n')
    
    wins = 0
    total = 0
    for opp_deck in OPPONENT_DECKS:
        with open('/tmp/opp_deck.csv', 'w') as f:
            for cid in opp_deck:
                f.write(f'{cid}\n')
        
        # CALL YOUR SIMULATOR HERE
        result = your_simulator.run(
            deck1='/tmp/test_deck.csv',
            deck2='/tmp/opp_deck.csv',
            games=10,                     # per matchup
            position_balanced=True,       # equal P1/P2
        )
        wins += result.wins
        total += result.games
    
    return wins / total if total > 0 else 0.0
```

Then:
```bash
python3 deck_search.py
```

### Runtime estimate

At 1,500 games/sec with 3 opponents × 10 games each = 30 games per eval:
- 50 decks × 30 games = 1,500 games per generation ≈ **1 second**
- 200 generations ≈ **3-4 minutes**

More opponents or games per eval = proportionally longer. Run overnight for thorough search.

### Output

```
best_deck_gen042.csv     # Saved each time a better deck is found
best_deck_final.csv      # Final best deck
evolution_progress.png   # Fitness over generations chart
evo_checkpoint.pkl       # Resume file (auto-saved every 10 gens)
```

---

## 2. Weight Tuner — `weight_tuner.py`

Optimizes the 30 phase weights (5 phases × 6 action types).

### How it works

- 30% random exploration, 70% hill climbing with restarts
- Mutates weights → tests in simulator → keeps improvements
- Simulated annealing: occasionally accepts worse weights to escape local optima
- 500 iterations recommended

### Integration

Replace `dummy_evaluate()` with a function that writes weights into `main.py` and runs your simulator. See inline comments at ~line 190.

### Runtime

~1-3 hours depending on games per evaluation.

---

## 3. RL Policy — `rl_policy.py`

Trains a neural network (20→32→1) to score actions via self-play.

Exports as hardcoded Python arrays — zero imports needed, runs on Kaggle.

This requires deeper simulator integration. See inline comments.

---

## Recommended Workflow

| Order | Tool | When | Output |
|---|---|---|---|
| 1 | `deck_search.py` | Overnight | Optimal 60-card deck |
| 2 | `weight_tuner.py` | Next day | Tuned phase weights |
| 3 | `rl_policy.py` | Optional | Neural decision policy |

Each builds on the previous — the best deck from step 1 feeds into step 2, etc.

## Important

- **Diverse opponents**: test against multiple archetypes, not just mirror matches
- **Position balancing**: equal games going first and second
- **Enough games**: ≥ 30 per evaluation for deck search, ≥ 50 for weight tuning
- **Checkpoints work**: kill the process anytime, restart resumes from last save
