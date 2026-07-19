# How Data Killed Our First Two Hypotheses — and Led Us to the Optimal Pokémon TCG Agent

**Track:** Model-Centric Strategy Analysis

---

## 0. How We Approached This Problem

We didn't start with a deck. We started with three questions:

1. What is the mathematically optimal attacker in this format?
2. How do we resolve the tension between speed (low energy cost) and power (high damage)?
3. Can we build a decision architecture that adapts to game phase rather than using a flat priority list?

This report documents the answers we found — including the two hypotheses that failed and *why* they failed. We believe the failures are as instructive as the final design.

---

## 1. Hypothesis 1: "Biggest Damage Wins" — Mega Dragonite ex

**The logic:** Mega Dragonite ex deals 330 damage — the highest in the format. If we can power it up, it one-shots everything. Surely the biggest number wins?

**[Figure A: Energy Cost Analysis — insert figA_energy_cost_analysis.png]**

**The problem:** Dragonite costs 3 Energy. In the Pokémon TCG, you can attach only one Energy per turn. This means Dragonite attacks on turn 4 at the absolute earliest, while 2-Energy attackers fire on turn 3. That one turn is lethal — we consistently lost the prize race against faster decks. The extra 10 damage over Mega Emboar ex (330 vs 320) doesn't matter when you're already dead.

**Verdict: REJECTED.** Raw damage is not enough. Energy cost dictates tempo, and tempo determines who attacks first.

---

## 2. Hypothesis 2: "Speed Is Everything" — Basic ex Rush

**The logic:** If 3 Energy is too slow, what about 1-2 Energy Basic Pokémon ex? Gouging Fire ex (230 HP, 260 DMG, 2 Energy) and Pikachu ex (200 HP, 300 DMG, 3 Energy) can attack quickly with no evolution required.

**[Figure B: HP Survival Analysis — insert figB_hp_survival.png]**

**The problem:** Basic ex Pokémon have 200-230 HP. Our analysis shows that a significant portion of the meta's attacks exceed this threshold. These Pokémon get OHKO'd before they can take a second prize. And because they're worth 2 prize cards when knocked out (Pokémon ex rule), losing one puts you at an immediate disadvantage. Against Stage 2 decks that survive the first hit, Basic ex rush runs out of steam.

**Verdict: PARTIALLY VIABLE but unreliable.** Speed without survivability creates a glass cannon — effective against unprepared opponents but collapses against anything that survives turn 3.

---

## 3. The Data Told Us What We Were Missing

At this point, we stopped guessing and let the card database answer the question. We plotted every attacker on a speed (energy cost) vs. power (damage + HP) plane:

**[Figure C: The Sweet Spot — insert figC_sweet_spot.png]**

The optimal zone is clear: **300+ HP, 250+ damage, 2 Energy cost.** Only one card sits squarely in this intersection: **Mega Emboar ex** (ID 932).

The numbers:
- **380 HP** — tied for highest in the game. Nearly immune to OHKOs.
- **320 damage** — second-highest overall, KOs every Pokémon except Mega Venusaur ex (380 HP).
- **2 {R} Energy** — fires on turn 3 with normal attachment, turn 2 with acceleration.
- **160 damage per energy** — 18.5% more efficient than Mega Lucario ex (135 dmg/energy).

But Mega Emboar ex is Stage 2 — it needs two evolution steps. This is the strategic tension our architecture must resolve.

---

## 4. Resolving the Speed Tension: Acceleration Engineering

Three acceleration vectors bring Mega Emboar ex online by turn 3-4:

1. **Grand Tree Stadium** (ACE SPEC, ID 1249): Allows Tepig → Pignite → Mega Emboar ex in a single turn from the deck.
2. **Rare Candy** (3 copies, ID 1124): Skips Pignite entirely for the regular Emboar line.
3. **Carmine** (3 copies, ID 1192): Turn-1 hand discard + draw 5, digging for evolution pieces before the opponent can act.

The backup plan: **Gouging Fire ex** (2 copies). While setting up Emboar, Gouging Fire ex applies early pressure with 260 damage for 2 Energy — buying time and taking early prizes.

---

## 5. Phase-Aware Decision Architecture

### 5.1 Why Flat Scoring Is Wrong

A flat "ATTACK > ENERGY > EVOLVE > PLAY" priority ladder makes catastrophic errors:
- **Turn 1**: Tries to attack when no energy is attached → wasted cycle
- **Turn 12 (1 prize left)**: Attaches energy to bench instead of attacking for game → throws the match
- **Against aggro**: Evolves slowly when it should rush

The solution: **phase-dependent action weighting.**

**[Figure 5: Phase Architecture — insert fig5_phase_strategy.png]**

### 5.2 The Four Phases

| Phase | Trigger | What Changes |
|---|---|---|
| **Opening** (Turns 1-2) | Early game | ATTACK suppressed (20). ENERGY (+5000) and DRAW (+3000) prioritized. |
| **Development** (Turns 3-5) | Setting up Emboar | EVOLVE peaks (+6000). ENERGY peaks (+8000). |
| **Aggression** (Turn 6+) | Emboar is ready | ATTACK dominates (+20000). BOSS rises (+3000). |
| **Endgame** (≤2 prizes) | Race to finish | ATTACK at maximum (+50000). ENERGY drops to 0. BOSS at peak (+5000). |

### 5.3 Ablation: What Happens Without Phase Awareness

| Scenario | Flat Agent Decision | Phase-Aware Decision | Outcome Difference |
|---|---|---|---|
| Turn 2, no energy on active | Tries to ATTACK (highest weight) → fails | Attaches ENERGY (development priority) | +1 turn of energy |
| Turn 10, 1 prize left, can KO | Plays Supporter to draw cards | Attacks for game-winning KO | Wins vs. throws |
| Opponent has 340 HP active | Attacks for 270 (not enough) | Boss's Orders → targets bench (70 HP) | KO vs. wasted attack |
| Turn 1, Carmine in hand | Plays energy first | Plays Carmine → draws 5 → finds evolution pieces | +2 cards toward Emboar |

The phase-aware agent wins scenarios that the flat agent either loses or delays. These are not edge cases — they occur in nearly every game.

---

## 6. Opponent Archetype Awareness

From the card pool, we identify three meta archetypes and adapt:

| Archetype | Signature | Our Adaptation |
|---|---|---|
| **Aggro (Basic ex)** | Fast, fragile attackers | Prioritize Hero's Cape. Survive first hit → win. |
| **Stage 2 Setup** | Slow, powerful evolutions | Race to Emboar first. Boss's Orders to snipe pre-evolutions. |
| **Control (Ability lock)** | Iron Thorns ex, stall | Grand Tree for evolution under lock. Maximum Belt for damage. |

This adaptation is lightweight — tracking opponent card IDs and attack frequency across games — and adds negligible computation overhead.

---

## 7. Deck Construction

**60-Card Mega Emboar ex Deck:**

| Role | Cards (ID) | Count |
|---|---|---|
| Evolution Line | Tepig (930), Pignite (931), Mega Emboar ex (932) | 4-3-3 |
| Backup Attacker | Gouging Fire ex (46) | 2 |
| Draw Engine | Carmine (1192), Lillie's Determination (1227), Chi-Yu (31) | 3-2-2 |
| Search | Master Ball (1125), Dusk Ball (1102), Poké Pad (1152) | 2-2-2 |
| Control | Boss's Orders (1182), Switch (1123), Prime Catcher (1088) | 2-2-1 |
| Acceleration | Grand Tree (1249), Rare Candy (1124) | 1-3 |
| Energy Support | Firebreather (1232) | 2 |
| Tools | Hero's Cape (1159), Maximum Belt (1158) | 1-1 |
| Energy | Basic {R} Energy (2) | 20 |

---

## 8. What We Learned

This investigation taught us three lessons that generalize beyond this competition:

1. **The card database contains the answer.** We spent too long guessing before we analyzed the numbers. Mega Emboar ex's dominance was hiding in plain sight — we just needed to plot HP against damage and filter by energy cost.

2. **Phase awareness is not optional.** A surprising number of submissions will use flat scoring. The difference between a good agent and a great one is knowing *when* to do *what* — not just *what* has the highest priority.

3. **Failures are data.** Our two rejected hypotheses weren't wasted time. They defined the boundaries of the solution space and made the final design obvious.

---

*This report was prepared for the Pokémon TCG AI Battle Challenge — Strategy Category.*
*All analysis from the official EN_Card_Data.csv (2,022 cards). Agent code, deck list, and reproducible analysis available in the attached notebook.*
