"""
Gouging Fire ex Aggro — Pokémon TCG AI Agent
==============================================
Fast, consistent Basic-ex beatdown. No evolution dependency.
Primary: Gouging Fire ex (230 HP, 260 DMG, 2 Energy)
Engine:  Chi-Yu (draw), Carmine/Lillie (hand refresh)
Tools:   Hero's Cape (+100 HP), Maximum Belt (+50 vs ex)
"""

import os, sys
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────────
for p in [
    '/kaggle/input/datasets/kiyotah/cg-lib',
    '/kaggle/input/competitions/pokemon-tcg-ai-battle/sample_submission/sample_submission',
]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from cg.api import (
    AreaType, OptionType, SelectContext, Observation,
    all_card_data, to_observation_class,
)

# ── Deck ─────────────────────────────────────────────────────────────────────
DECK = []
for path in [
    "/kaggle/input/datasets/kiyotah/gouging-fire-aggro/deck.csv",
    "/kaggle_simulations/agent/deck.csv",
    "deck.csv",
]:
    if os.path.exists(path):
        with open(path) as f:
            DECK = [int(x) for x in f.read().split() if x.strip()]
        break

# ── Card IDs ─────────────────────────────────────────────────────────────────
Gouging_Fire_ex  = 46
Chi_Yu           = 31
Carmine          = 1192
Lillie_Determination = 1227
Boss_Orders      = 1182
Switch_Card      = 1123
Hero_Cape        = 1159
Maximum_Belt     = 1158
Master_Ball      = 1125
Dusk_Ball        = 1102
Ultra_Ball       = 1121
Poke_Pad         = 1152
Prime_Catcher    = 1088
Firebreather     = 1232
Basic_Fire_Energy = 2

# All attackers in deck
ATTACKERS = {Gouging_Fire_ex, Chi_Yu}

# ── State ────────────────────────────────────────────────────────────────────
class Plan:
    __slots__ = ('attacker', 'target', 'attack_idx', 'energy_ready')
    def __init__(self):
        self.attacker = -1
        self.target = -1
        self.attack_idx = -1
        self.energy_ready = False

state = {
    'plan': Plan(),
    'turn': 0,
    'phase': 'opening',
    'opponent_ids': defaultdict(int),
    'opponent_arch': 'unknown',
}

# ── Phase detection ──────────────────────────────────────────────────────────
AGGRO_SIGNATURES  = {46, 210, 44, 313, 179, 1062, 328}   # Basic ex beaters
STAGE2_SIGNATURES = {932, 652, 904, 747, 772, 678, 569}   # Stage 2/Mega evos
CONTROL_SIGNATURES = {37, 74, 1247}                        # Ability lock

def detect_phase(turn, my_prizes, opp_prizes, opp_arch):
    if my_prizes <= 2 or opp_prizes <= 2:
        return 'endgame'
    if turn <= 2:
        return 'opening'
    if opp_arch == 'aggro':
        return 'aggression'  # Skip development — race them
    if turn <= 4:
        return 'development'
    return 'aggression'

def detect_archetype(seen):
    scores = {'aggro': 0, 'stage2': 0, 'control': 0}
    for cid, n in seen.items():
        if cid in CONTROL_SIGNATURES:   scores['control'] += n * 3
        elif cid in AGGRO_SIGNATURES:   scores['aggro'] += n
        elif cid in STAGE2_SIGNATURES:  scores['stage2'] += n
    if scores['control']:  return 'control'
    if scores['aggro'] > scores['stage2'] and scores['aggro'] > 0: return 'aggro'
    if scores['stage2'] > 0: return 'stage2'
    return 'unknown'

# ── Weights by phase ─────────────────────────────────────────────────────────
W = {
    'opening':     {'attack': 0,    'energy': 5000,  'evolve': 3000,  'draw': 3000,  'search': 2500, 'boss': 0},
    'development': {'attack': 500,  'energy': 6000,  'evolve': 4000,  'draw': 2000,  'search': 2000, 'boss': 1000},
    'aggression':  {'attack': 20000,'energy': 3000,  'evolve': 2000,  'draw': 1000,  'search': 1000, 'boss': 3000},
    'endgame':     {'attack': 50000,'energy': 0,     'evolve': 0,     'draw': 500,   'search': 500,  'boss': 5000},
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_card(obs, area, idx, pi):
    try:
        ps = obs.current.players[pi]
        if area == AreaType.HAND:    return ps.hand[idx]
        if area == AreaType.DISCARD: return ps.discard[idx]
        if area == AreaType.ACTIVE:  return ps.active[idx] if ps.active else None
        if area == AreaType.BENCH:   return ps.bench[idx]
        if area == AreaType.DECK and obs.select:
            return obs.select.deck[idx] if obs.select.deck else None
    except Exception:
        pass
    return None

def safe_respond(select, indices=None):
    if indices is None: indices = []
    valid = list(dict.fromkeys(i for i in indices if 0 <= i < len(select.option)))
    need = select.minCount - len(valid)
    if need > 0:
        for i in range(len(select.option)):
            if i not in valid:
                valid.append(i)
                need -= 1
                if need == 0: break
    if len(valid) > select.maxCount:
        valid = valid[:select.maxCount]
    return valid

def count_energy_on(pokemon):
    """Count how many energy are attached to a Pokémon."""
    if pokemon is None: return 0
    return len(pokemon.energies) if hasattr(pokemon, 'energies') and pokemon.energies else 0

# ── Scoring ──────────────────────────────────────────────────────────────────
def score_action(o, obs, my_state, my_idx, phase, opp_arch, discard_counts, my_prizes):
    score = 0
    t = o.type

    if t == OptionType.ATTACK:
        score += W[phase]['attack']
        active = my_state.active[0] if (my_state.active and len(my_state.active) > 0) else None
        if active and active.id == Gouging_Fire_ex:
            score += 2000  # Main attacker bonus
            if my_prizes <= 2:
                score += 5000  # Endgame: must KO
        elif active and active.id in ATTACKERS:
            score += 800

    elif t == OptionType.ENERGY and score < W[phase]['attack'] - 500:
        score += W[phase]['energy']
        card = get_card(obs, AreaType.HAND, o.index, my_idx)
        if card and card.id == Basic_Fire_Energy:
            score += 2000
            if o.inPlayArea == AreaType.ACTIVE:
                score += 1000  # Power up active first

    elif t == OptionType.EVOLVE and score < W[phase]['attack'] - 1000:
        score += W[phase]['evolve']

    elif t == OptionType.PLAY and score < W[phase]['attack'] - 1000:
        card = get_card(obs, AreaType.HAND, o.index, my_idx)
        if card is None: return score
        cid = card.id

        if cid in (Carmine, Lillie_Determination):
            score += W[phase]['draw']
        elif cid in (Master_Ball, Dusk_Ball, Ultra_Ball, Poke_Pad):
            score += W[phase]['search']
        elif cid == Boss_Orders:
            score += W[phase]['boss']
        elif cid == Hero_Cape:
            score += 2500 if opp_arch == 'aggro' else 1500
        elif cid == Maximum_Belt:
            score += 2000 if opp_arch in ('stage2', 'control') else 1200
        elif cid == Firebreather:
            score += 1800 if phase in ('opening', 'development') else 600
        elif cid in (Switch_Card, Prime_Catcher):
            score += 1000
        else:
            score += 200

    return score

# ── Agent ────────────────────────────────────────────────────────────────────
def agent(obs_dict: dict) -> list[int]:
    global state

    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        return [0]

    # Init: return deck
    if obs.select is None:
        return DECK if len(DECK) == 60 else [Basic_Fire_Energy] * 60

    s = obs.current
    sel = obs.select
    ctx = sel.context
    my_idx = s.yourIndex
    my = s.players[my_idx]
    opp = s.players[1 - my_idx]
    my_p = len(my.prize) if my.prize else 0
    opp_p = len(opp.prize) if opp.prize else 0

    # Track opponent
    if opp.active:
        for p in opp.active:
            state['opponent_ids'][p.id] += 1
    if opp.bench:
        for p in opp.bench:
            state['opponent_ids'][p.id] += 1

    # Turn reset
    if state['turn'] != s.turn:
        state['turn'] = s.turn
        state['plan'] = Plan()

    # Classify
    opp_arch = detect_archetype(state['opponent_ids'])
    state['opponent_arch'] = opp_arch
    phase = detect_phase(s.turn, my_p, opp_p, opp_arch)
    state['phase'] = phase

    # Discard counts
    disc = defaultdict(int)
    if my.discard:
        for c in my.discard:
            disc[c.id] += 1

    # MAIN: score & pick
    if ctx == SelectContext.MAIN:
        best_idx, best_score = -1, -100000
        for i, o in enumerate(sel.option):
            sc = score_action(o, obs, my, my_idx, phase, opp_arch, disc, my_p)
            if sc > best_score:
                best_score, best_idx = sc, i
        if best_idx != -1:
            return safe_respond(sel, [best_idx])

    # Fallback
    return safe_respond(sel, [0] if sel.minCount > 0 else [])
