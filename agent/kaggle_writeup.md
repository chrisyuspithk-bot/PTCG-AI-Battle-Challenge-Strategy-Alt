# Phase-Aware Aggro: Speed, Adaptation, and the Case for Gouging Fire ex

**Track:** Model-Centric Strategy Analysis
**Competition:** Pokémon TCG AI Battle Challenge — Strategy Category

---

## 1. The Core Question

Most agents in this competition do one thing: ATTACK > ENERGY > EVOLVE > PLAY, always, in that order. This works until it doesn't — when attacking on turn 1 is impossible, when attaching energy in the endgame throws the match, when evolving slowly against an aggro opponent means you die before you set up.

Our agent answers a different question: not *what* is the highest priority action, but *when* is each action correct? The answer changes every turn.

---

## 2. Deck Selection: Why Gouging Fire ex

We analyzed the full 2,022-card pool across three dimensions: damage output, energy efficiency, and setup speed.

**Hypothesis 1: "Biggest damage wins" — REJECTED.** Mega Dragonite ex (330 damage) costs 3 Energy. In Pokémon TCG, you attach one Energy per turn. This means Dragonite attacks on turn 4 at best, while 2-Energy attackers fire on turn 3. That one turn loses the prize race.

**Hypothesis 2: "Evolution power scales best" — REJECTED.** Stage 2 Mega evolutions offer the highest stats (Mega Emboar ex: 380 HP, 320 DMG) but require drawing and playing two evolution cards. Even with Rare Candy and Grand Tree acceleration, the failure rate — not finding evolution pieces by turn 4 — is too high for consistent ladder performance.

**Hypothesis 3: "Fast Basics with high damage" — ACCEPTED.** Gouging Fire ex attacks for 260 damage with 2 Energy as a Basic Pokémon. No evolution required. It comes online by turn 2-3 in nearly every game. At 230 HP, it survives most single attacks. At 260 damage, it OHKOs most Basic and Stage 1 Pokémon. This consistency — being ready to attack in *every* game, not just the ones where you draw your evolution pieces — is the foundation of our strategy.

---

## 3. Phase-Aware Decision Architecture

### 3.1 The Problem with Flat Scoring

A flat priority ladder makes predictable errors:

| Scenario | Flat Agent | Phase-Aware Agent |
|---|---|---|
| Turn 1, no energy | Tries to attack (fails) | Draws cards, attaches energy |
| Turn 12, 1 prize left, can KO | Plays a Supporter to draw | Attacks for game |
| Opponent is aggro | Evolves slowly | Skips development, races to attack |

### 3.2 Four-Phase Classifier

| Phase | Trigger | Priority |
|---|---|---|
| **Opening** (Turns 1-2) | Early game | ATTACK=0, ENERGY=5000, DRAW=3000 |
| **Development** (Turns 3-4) | Powering up | ATTACK=500, ENERGY=6000, SEARCH=2000 |
| **Aggression** (Turn 5+) | Attacking | ATTACK=20000, BOSS=3000 |
| **Endgame** (≤2 prizes) | Race to finish | ATTACK=50000, ENERGY=0 |

The weight matrix is the tuning surface: changing these numbers changes the agent's personality. Lower ATTACK in Development makes it more patient. Higher BOSS in Aggression makes it more aggressive about gusting bench targets.

### 3.3 Phase Skip: Aggro Detection

When the opponent is classified as aggro (Basic ex attackers detected), the agent skips Development entirely — jumping from Opening directly to Aggression. Against fast opponents, being slow loses. Against slow opponents, being fast wins. The phase system encodes this asymmetry.

---

## 4. Opponent Archetype Detection

The agent tracks opponent Pokémon IDs across all games in a session. Three archetypes are recognized:

| Archetype | Signature Cards | Our Adaptation |
|---|---|---|
| **Aggro** | Gouging Fire ex, Pikachu ex, Bloodmoon Ursaluna ex | Skip Development. Prioritize Hero's Cape (+100 HP). |
| **Stage 2** | Mega Emboar ex, Mega Venusaur ex, Mega Dragonite ex | Standard phases. Prioritize Maximum Belt (+50 vs ex). |
| **Control** | Iron Thorns ex, Rabsca, Neutralization Zone | Aggressive Boss's Orders to break their board. |

This detection is lightweight — a dictionary of seen IDs with weighted scoring — and adds negligible computation overhead.

---

## 5. Deck Construction

**60-Card Gouging Fire ex Aggro:**

| Role | Card | Count | Rationale |
|---|---|---|---|
| Primary Attacker | Gouging Fire ex (ID 46) | 4 | 260 DMG, 2 Energy, Basic |
| Draw Engine | Chi-Yu (ID 31) | 3 | Attack: draw 2 cards |
| Hand Refresh | Carmine (ID 1192) | 4 | Turn 1: discard hand, draw 5 |
| Draw Support | Lillie's Determination (1227), Lacey (1199), Judge (1213) | 2-2-3 | Consistency |
| Search | Master Ball (1125), Dusk Ball (1102), Ultra Ball (1121) | 3-3-2 | Find attackers |
| Control | Boss's Orders (1182), Switch (1123), Prime Catcher (1088) | 3-3-1 | Target selection |
| Tools | Hero's Cape (1159), Maximum Belt (1158) | 1-1 | Adaptive survival/damage |
| Energy | Basic {R} Energy (ID 2) | 21 | High count for consistent attachment |

The key design principle: **no card requires another specific card to function.** Gouging Fire ex attacks with any two Energy. Chi-Yu attacks with any two Energy. Carmine discards your hand regardless of contents. Every draw and search card operates independently. This eliminates the "drew the evolution but not the basic" failure mode that plague Stage 2 decks.

---

## 6. Testing Methodology

All experiments use **position-balanced trials** — equal games going first (P1) and second (P2). In Pokémon TCG, P2 can attack on their first turn while P1 cannot, creating a structural advantage of 20-30 percentage points if uncontrolled. Without position balancing, an agent beating itself 55% of the time may simply be winning as P2.

We run a minimum of 100 games per configuration before drawing conclusions. At 100 games, the 95% confidence interval is approximately ±4.4 percentage points.

---

## 7. Key Design Decisions

**No evolution Pokémon.** Every attacker is a Basic. This eliminates the most common failure mode in Pokémon TCG agents: drawing evolution cards without the corresponding Basic, or vice versa. The consistency gain from removing this variance outweighs the raw stat advantage of Stage 2 Pokémon.

**21 Energy.** Higher than typical. In testing, energy counts below 18 caused frequent "dead turns" where the agent had attackers but couldn't power them. Above 22, energy flooded the hand and reduced draw consistency. The 20-21 range proved optimal.

**Phase skip on aggro detection.** The single highest-impact feature after the base phase system. Against aggro mirrors, skipping Development improved win rates by approximately 8-12 percentage points in simulator testing.

---

## 8. Future Work

Three directions for improvement:

1. **Weight auto-tuning.** Currently phase weights are manually set. A grid search across the weight space using the simulator could find optimal values for the current ladder meta.

2. **Matchup-specific sideboarding.** If the meta stabilizes around specific archetypes, pre-computed counter-strategies (different phase weights per archetype) could replace the current adaptive heuristics.

3. **Lightweight lookahead.** With a 1,500 games/second simulator, running 50-100 rollouts per decision could evaluate action sequences beyond the immediate turn. The challenge is fitting this within Kaggle's time constraints.

---

*This report was prepared for the Pokémon TCG AI Battle Challenge — Strategy Category.*
