# Training Framework

Three tools to automatically find better decks and agents using your simulator.

## Setup

```bash
pip install pandas numpy
```

Place `EN_Card_Data.csv` (from Kaggle competition data) in the `train/` directory.

## 1. Deck Search (`deck_search.py`)

Evolutionary algorithm that finds the optimal 60-card deck.

**How it works:**
- Population of 50 random decks
- Each generation: evaluate all decks in your simulator, keep best 5
- Create next generation via crossover + mutation
- 200 generations = 10,000 deck evaluations

**To use:**

```python
# Edit deck_search.py, replace dummy_evaluate():
def evaluate_deck(deck):
    # Save deck to temp file
    with open('/tmp/deck.csv', 'w') as f:
        for cid in deck:
            f.write(f'{cid}\n')
    
    # Run your simulator
    wins = 0
    for opponent_deck in OPPONENT_DECKS:
        result = run_simulator('/tmp/deck.csv', opponent_deck, games=10)
        wins += result.wins
    return wins / (len(OPPONENT_DECKS) * 10)

# Then run:
best_deck, fitness, history = run_evolution(evaluate_deck)
save_deck(best_deck)
```

**Expected runtime:** ~2-8 hours depending on simulator speed. Run overnight.

## 2. Weight Tuner (`weight_tuner.py`)

Optimizes the phase weight matrix (5 phases × 6 actions = 30 parameters).

**How it works:**
- 30% random exploration, 70% hill climbing with restarts
- Each iteration: mutate weights → test in simulator → keep if better
- 500 iterations recommended

**To use:**

```python
# Edit weight_tuner.py, replace dummy_evaluate():
def evaluate_weights(weights):
    # Write weights into main.py
    write_weights_to_agent(weights, '../agent/main.py')
    
    # Run simulator
    result = run_simulator('../agent/main.py', '../agent/deck.csv', 
                          OPPONENT_DECKS, games=50)
    return result.win_rate

# Then run:
best_w, fitness, history = optimize(evaluate_weights, iterations=500)
# Copy the printed W = {...} into main.py
```

**Expected runtime:** ~1-3 hours.

## 3. RL Policy (`rl_policy.py`)

Trains a neural network to make decisions via self-play.

**Architecture:** 20 input features → 32 hidden → 1 output score.

**How it works:**
- Self-play: policy plays against itself, collects (state, action, reward)
- Train: regress state features → game outcome
- Export: hardcoded numpy arrays → paste into main.py (no imports needed)

**To use:** This requires integrating your simulator into the training loop. See `rl_policy.py` inline comments.

**Expected runtime:** 5-20 hours for meaningful training.

## Recommended Workflow

```
Day 1:  deck_search.py  → find best deck       (overnight)
Day 2:  weight_tuner.py → optimize weights      (afternoon)
Day 3+: rl_policy.py    → train neural policy   (optional, higher ceiling)
```

Each tool builds on the previous — the best deck from step 1 becomes the baseline for step 2, etc.

## Tips

- **Diverse opponents:** Test against multiple deck archetypes, not just mirrors
- **Position balancing:** Equal games going first and second
- **Enough games:** At least 50 per evaluation for deck search, 100+ for weight tuning
- **Save checkpoints:** Each tool prints progress — pipe to a log file
