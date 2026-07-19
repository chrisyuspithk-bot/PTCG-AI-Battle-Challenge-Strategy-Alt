"""
Mega Emboar ex — Phase-Aware Heuristic Agent
=============================================
Pokémon TCG AI Battle Challenge — Strategy Category Submission

Architecture:
  1. Game Phase Classifier — determines Opening/Development/Aggression/Endgame
  2. Threat Evaluator — calculates KO potential for each possible action
  3. Dynamic Scorer — phase-dependent weights for action prioritization
  4. Opponent Tracker — monitors patterns for adaptation

Deck Strategy:
  Primary Attacker: Mega Emboar ex (ID 932) — 380 HP, 320 DMG, 2 {R} Energy
  Backup Attacker:  Gouging Fire ex (ID 46) — 230 HP, 260 DMG, 2 Energy
  Draw Engine:     Carmine, Lillie's Determination, Chi-Yu
  Acceleration:    Grand Tree (ACE SPEC), Rare Candy, Emboar (Inferno Fandango)
"""

import os
import sys
from collections import defaultdict

# ── Path Setup ──────────────────────────────────────────────────────────────
CUSTOM_CG_PATH = '/kaggle/input/datasets/kiyotah/cg-lib'
COMP_CG_PATH = '/kaggle/input/competitions/pokemon-tcg-ai-battle/sample_submission/sample_submission'

if os.path.exists(CUSTOM_CG_PATH):
    if CUSTOM_CG_PATH not in sys.path:
        sys.path.insert(0, CUSTOM_CG_PATH)
else:
    if COMP_CG_PATH not in sys.path:
        sys.path.insert(0, COMP_CG_PATH)

from cg.api import (
    AreaType, CardType, EnergyType, Observation,
    SelectContext, OptionType, Card, Pokemon,
    all_card_data, to_observation_class
)

# ── Deck Loading ─────────────────────────────────────────────────────────────
my_deck_path = "/kaggle/input/datasets/kiyotah/mega-emboar-ex-deck/deck.csv"
my_deck = []

if os.path.exists(my_deck_path):
    with open(my_deck_path, "r") as file:
        my_deck = [int(line.strip()) for line in file.read().splitlines() if line.strip() != ""]
else:
    for fallback in ["deck.csv", "/kaggle_simulations/agent/deck.csv"]:
        if os.path.exists(fallback):
            with open(fallback, "r") as file:
                my_deck = [int(line.strip()) for line in file.read().splitlines() if line.strip() != ""]
            break

# ── Card Database ────────────────────────────────────────────────────────────
try:
    all_card = all_card_data()
    card_table = {c.cardId: c for c in all_card}
except Exception:
    card_table = {}

# ── Card ID Constants ────────────────────────────────────────────────────────
# Evolution Line
Tepig           = 930
Pignite         = 931
Mega_Emboar_ex  = 932
Emboar          = 569   # Regular Emboar with Inferno Fandango ability

# Attackers
Gouging_Fire_ex = 46
Chi_Yu          = 31

# Trainers
Carmine              = 1192
Lillie_Determination = 1227
Boss_Orders          = 1182
Switch_Card          = 1123
Rare_Candy           = 1124  # approximate
Grand_Tree           = 1249  # ACE SPEC Stadium
Hero_Cape            = 1159  # ACE SPEC Tool
Maximum_Belt         = 1158
Prime_Catcher        = 1088
Master_Ball          = 1125
Dusk_Ball            = 1102
Ultra_Ball           = 1103
Poke_Pad             = 1152
Firebreather         = 1232

# Energy
Basic_Fire_Energy = 2

# ── Agent State ──────────────────────────────────────────────────────────────
class AttackPlan:
    def __init__(self):
        self.attacker = -1
        self.target = -1
        self.attack_index = -1
        self.remain_hp = -1
        self.energy_ready = False

agent_state = {
    "plan": AttackPlan(),
    "pre_turn": 0,
    "phase": "opening",
    "opponent_active_ids": defaultdict(int),   # Track opponent active Pokémon across games
    "opponent_attack_count": 0,                # How many times opponent has attacked this game
    "opponent_archetype": "unknown",           # aggrieved/stage2/control
    "games_played": 0,
}

# ── Utility Functions ────────────────────────────────────────────────────────
def get_card(obs: Observation, area: AreaType, index: int, player_index: int):
    """Safely extract card information without crashes."""
    try:
        ps = obs.current.players[player_index]
        if area == AreaType.DECK:
            return obs.select.deck[index] if obs.select and obs.select.deck else None
        if area == AreaType.HAND:
            return ps.hand[index] if index < len(ps.hand) else None
        if area == AreaType.DISCARD:
            return ps.discard[index] if index < len(ps.discard) else None
        if area == AreaType.ACTIVE:
            return ps.active[index] if ps.active and index < len(ps.active) else None
        if area == AreaType.BENCH:
            return ps.bench[index] if index < len(ps.bench) else None
        if area == AreaType.PRIZE:
            return ps.prize[index] if ps.prize and index < len(ps.prize) else None
        if area == AreaType.STADIUM:
            return obs.current.stadium[index] if obs.current.stadium and index < len(obs.current.stadium) else None
        return None
    except Exception:
        return None


def classify_phase(turn: int, my_prizes: int, opp_prizes: int,
                   has_emboar_in_play: bool, opp_archetype: str) -> str:
    """Determine the current game phase based on turn, prizes, and board state."""
    if my_prizes <= 2 or opp_prizes <= 2:
        return "endgame"
    if turn <= 2:
        return "opening"
    # Against aggro, skip development — go straight to aggression
    if opp_archetype == "aggro" and turn > 2:
        return "aggression"
    if turn <= 5 and not has_emboar_in_play:
        return "development"
    return "aggression"


def detect_opponent_archetype(opp_active_ids: dict, opp_attack_count: int, turn: int) -> str:
    """Classify opponent deck archetype from observed behavior."""
    # Aggro: attacks early (turn 1-2) with Basic Pokémon ex
    if opp_attack_count >= 2 and turn <= 3:
        return "aggro"
    # Stage 2: hasn't attacked by turn 4 — setting up evolutions
    if opp_attack_count == 0 and turn >= 4:
        return "stage2"
    # If opponent has played Iron Thorns ex or similar ability-lock
    for cid, count in opp_active_ids.items():
        if cid in (37,):  # Iron Thorns ex
            return "control"
    return "unknown"


def evaluate_threat(my_hp: int, my_damage: int, opp_hp: int, 
                    my_energy: int, cost: int) -> dict:
    """Calculate KO potential for an attack scenario."""
    can_ko = my_damage >= opp_hp
    energy_ready = my_energy >= cost
    return {
        "can_ko": can_ko,
        "energy_ready": energy_ready,
        "overkill": my_damage - opp_hp if can_ko else 0,
    }


# ── Phase-Specific Scoring Weights ──────────────────────────────────────────
PHASE_WEIGHTS = {
    "opening":     {"ATTACK": 20,    "ENERGY": 5000,  "EVOLVE": 3000,  "DRAW": 3000,  "SEARCH": 2500, "BOSS": 500},
    "development": {"ATTACK": 500,   "ENERGY": 8000,  "EVOLVE": 6000,  "DRAW": 2000,  "SEARCH": 1500, "BOSS": 1000},
    "aggression":  {"ATTACK": 20000, "ENERGY": 3000,  "EVOLVE": 2000,  "DRAW": 1000,  "SEARCH": 800,  "BOSS": 3000},
    "endgame":     {"ATTACK": 50000, "ENERGY": 0,     "EVOLVE": 500,   "DRAW": 500,   "SEARCH": 500,  "BOSS": 5000},
}


def score_action(o, obs, my_state, my_index, phase, discard_counts, my_prize):
    """Score a single action option based on type, phase, and board state."""
    score = 0
    opt_type = o.type
    
    if opt_type == OptionType.ATTACK:
        score += PHASE_WEIGHTS[phase]["ATTACK"]
        
        active = my_state.active[0] if (my_state.active and len(my_state.active) > 0) else None
        if active:
            # Mega Emboar ex attack bonuses
            if active.id == Mega_Emboar_ex:
                if o.attackId == 1000:  # Crimson Blast (approximate)
                    # Bonus for energy available in discard
                    energy_bonus = min(3, discard_counts[Basic_Fire_Energy]) * 60
                    score += energy_bonus
                    # In endgame, prioritize finishing
                    if my_prize <= 2:
                        score += 5000
                else:
                    score += 1000  # Secondary attack
            
            # Gouging Fire ex
            elif active.id == Gouging_Fire_ex:
                score += 1500
            
            # Regular Emboar
            elif active.id == Emboar:
                score += 800
    
    elif opt_type == OptionType.ENERGY:
        if score < PHASE_WEIGHTS[phase]["ATTACK"] - 1000:
            score += PHASE_WEIGHTS[phase]["ENERGY"]
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            if card and card.id == Basic_Fire_Energy:
                score += 3000
                # Prefer attaching to active in opening/development
                if o.inPlayArea == AreaType.ACTIVE and phase in ("opening", "development"):
                    score += 1500
                # In development, prefer attaching to bench (for Mega Emboar)
                if o.inPlayArea == AreaType.BENCH and phase == "development":
                    score += 1000
    
    elif opt_type == OptionType.EVOLVE:
        if score < PHASE_WEIGHTS[phase]["ATTACK"] - 1000:
            score += PHASE_WEIGHTS[phase]["EVOLVE"]
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            if card:
                # Prioritize evolving into Mega Emboar ex
                if card.id == Mega_Emboar_ex:
                    score += 4000
                elif card.id == Pignite:
                    score += 2500
                elif card.id == Emboar:
                    score += 2000
    
    elif opt_type == OptionType.PLAY:
        if score < PHASE_WEIGHTS[phase]["ATTACK"] - 2000:
            card = get_card(obs, AreaType.HAND, o.index, my_index)
            if card:
                cid = card.id
                # Draw supporters — highest priority in opening
                if cid in (Carmine, Lillie_Determination):
                    score += PHASE_WEIGHTS[phase]["DRAW"]
                # Search cards
                elif cid in (Master_Ball, Dusk_Ball, Ultra_Ball):
                    score += PHASE_WEIGHTS[phase]["SEARCH"]
                # Boss's Orders — high priority in aggression/endgame
                elif cid == Boss_Orders:
                    score += PHASE_WEIGHTS[phase]["BOSS"]
                # Stadium (Grand Tree for evolution acceleration)
                elif cid == Grand_Tree:
                    score += 2500 if phase in ("opening", "development") else 500
                # Tools
                elif cid in (Hero_Cape, Maximum_Belt):
                    score += 1500
                # Energy search
                elif cid == Firebreather:
                    score += 2000 if phase in ("opening", "development") else 800
                # Generic fallback
                else:
                    score += 300
    
    return score


# ── Main Agent Function ──────────────────────────────────────────────────────
def agent(obs_dict: dict) -> list[int]:
    """Main handler — called by the Kaggle simulation environment each decision point."""
    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        return [0]
    
    # Initialization phase: return deck
    if obs.select is None:
        agent_state["games_played"] += 1
        return my_deck if len(my_deck) == 60 else [Basic_Fire_Energy] * 60
    
    state = obs.current
    select = obs.select
    context = select.context
    my_index = state.yourIndex
    my_state = state.players[my_index]
    my_prize = len(my_state.prize) if my_state.prize else 0
    
    # ── Opponent tracking ─────────────────────────────────────────────────
    opp_index = 1 - my_index
    opp_state = state.players[opp_index]
    opp_prize = len(opp_state.prize) if opp_state.prize else 0
    
    # Track opponent active Pokémon
    if opp_state.active and len(opp_state.active) > 0:
        agent_state["opponent_active_ids"][opp_state.active[0].id] += 1
    
    # Reset on new turn
    if agent_state["pre_turn"] != state.turn:
        agent_state["pre_turn"] = state.turn
        agent_state["plan"] = AttackPlan()
    
    # Detect opponent archetype
    agent_state["opponent_archetype"] = detect_opponent_archetype(
        agent_state["opponent_active_ids"],
        agent_state["opponent_attack_count"],
        state.turn
    )
    
    # Classify game phase
    active_id = my_state.active[0].id if (my_state.active and len(my_state.active) > 0) else -1
    bench_ids = [p.id for p in my_state.bench] if my_state.bench else []
    has_emboar = (active_id == Mega_Emboar_ex) or (Mega_Emboar_ex in bench_ids)
    
    phase = classify_phase(state.turn, my_prize, opp_prize, has_emboar,
                           agent_state["opponent_archetype"])
    agent_state["phase"] = phase
    
    # Count discard for energy acceleration decisions
    discard_counts = defaultdict(int)
    if my_state.discard:
        for card in my_state.discard:
            discard_counts[card.id] += 1
    
    # ── MAIN PHASE: Score all options ────────────────────────────────────────
    if context == SelectContext.MAIN:
        best_idx = -1
        best_score = -100000
        
        for i, o in enumerate(select.option):
            # Track opponent attacks for archetype detection
            if o.type == OptionType.ATTACK:
                agent_state["opponent_attack_count"] += 1
            
            current_score = score_action(o, obs, my_state, my_index, phase, 
                                         discard_counts, my_prize)
            if current_score > best_score:
                best_score = current_score
                best_idx = i
        
        if best_idx != -1:
            return safe_respond(select, [best_idx])
    
    # ── Fallback: return first valid option ──────────────────────────────────
    return safe_respond(select, [])


def safe_respond(select, indices=None) -> list[int]:
    """Validate indices against minCount/maxCount to prevent engine crashes."""
    if indices is None:
        indices = []
    
    valid = [i for i in indices if 0 <= i < len(select.option)]
    valid = list(dict.fromkeys(valid))
    
    # Fill to minCount if needed
    if len(valid) < select.minCount:
        for i in range(len(select.option)):
            if i not in valid:
                valid.append(i)
                if len(valid) == select.minCount:
                    break
    
    # Truncate to maxCount
    if len(valid) > select.maxCount:
        valid = valid[:select.maxCount]
    
    return valid
