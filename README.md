# PTCG AI Battle Challenge

[Kaggle Competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle)

## Agent

```
agent/
├── main.py      # Gouging Fire ex aggro — phase-aware heuristic agent
└── deck.csv     # 60-card deck (4 Gouging Fire ex, 3 Chi-Yu, 20 Fire Energy, trainers)
```

**Deck:** Gouging Fire ex (230 HP, 260 DMG, 2 Energy) — fast Basic-ex beatdown. No evolution dependency.

**Architecture:** Phase-aware scoring (opening/development/aggression/endgame) + opponent archetype detection + adaptive tool priority.

## Iterate

1. Test in simulator
2. Tweak `W` weights in `main.py`
3. Adjust deck ratios in `deck.csv`
4. Submit to Kaggle (5/day max)

## Submit

```bash
tar -czvf submission.tar.gz main.py deck.csv cg/
```
