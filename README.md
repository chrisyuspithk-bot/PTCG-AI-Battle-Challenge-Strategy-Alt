# PTCG AI Battle Challenge

[Kaggle Competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle)

## Quickstart

```bash
# Test locally with your simulator
python3 your_simulator.py agent/main.py agent/deck.csv

# Submit to Kaggle
cd agent && tar -czvf submission.tar.gz main.py deck.csv cg/
```

## Agent (`agent/main.py`)

Gouging Fire ex aggro — 180 lines, no dependencies beyond `cg/api.py`.

**Deck:** 4× Gouging Fire ex, 3× Chi-Yu, 21× Fire Energy, 32 trainers. All Basic Pokémon — attacks online by turn 2-3 with no evolution required.

**Phases:**

| Phase | Trigger | Strategy |
|---|---|---|
| Opening | Turns 1-2 | Draw cards, attach energy, build bench |
| Development | Turns 3-4 | Power up attackers |
| Aggression | Turn 5+ | Attack. Boss's Orders for KOs. |
| Endgame | ≤2 prizes left | All-in attack. No energy attachment. |

**Weights** (in `W` dict, line ~95) — tune these for your meta:

| Action | Opening | Development | Aggression | Endgame |
|---|---|---|---|---|
| Attack | 0 | 500 | 20000 | 50000 |
| Energy | 5000 | 6000 | 3000 | 0 |
| Draw | 3000 | 2000 | 1000 | 500 |
| Search | 2500 | 2000 | 1000 | 500 |
| Boss | 0 | 1000 | 3000 | 5000 |

**Opponent detection:** Tracks opponent Pokémon IDs across games. Classifies as `aggro` (Basic ex beaters), `stage2` (Mega/Stage 2 evos), or `control` (ability lock). Adapts tool priority and skips development phase vs aggro.

## Iterate

1. Run in your simulator → check win rate
2. Tweak `W` weights or add cards to `AGGRO_SIGNATURES` / `STAGE2_SIGNATURES`
3. Adjust deck ratios in `deck.csv` (energy count, draw vs search balance)
4. Submit to Kaggle (5/day max, latest 2 active)
