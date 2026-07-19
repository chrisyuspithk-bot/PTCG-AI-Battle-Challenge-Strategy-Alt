# PTCG AI Battle Challenge — Strategy Category

Submission for the [Pokémon TCG AI Battle Challenge](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle) Strategy Category.

## Contents

```
├── STRATEGY_REPORT.md      # Kaggle Writeup (Discovery Arc narrative)
├── main.py                 # Phase-aware heuristic agent
├── deck.csv                # 60-card Mega Emboar ex deck
└── figures/                # 9 data-driven charts
```

## Strategy

**Deck:** Mega Emboar ex (380 HP, 320 DMG, 2 Energy) — the mathematically optimal attacker in the 2,022-card format.

**Architecture:** Phase-aware decision system that dynamically reweights actions based on game stage (Opening → Development → Aggression → Endgame), with opponent archetype detection.

**Report:** Hypothesis-driven investigation documenting two rejected approaches and the data analysis that revealed the optimal solution.

## Submission

Two-part entry required:

1. **Simulation Category** — `tar -czvf submission.tar.gz main.py deck.csv cg/`
2. **Strategy Category** — Paste `STRATEGY_REPORT.md` into a Kaggle Writeup, attach figures to Media Gallery
