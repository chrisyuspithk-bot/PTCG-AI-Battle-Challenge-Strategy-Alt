"""
Reproducible Card Pool Analysis
================================
Generates all figures used in the Strategy Category report.
Run: python analysis_notebook.py
Requires: pandas, numpy, matplotlib, seaborn
Input: EN_Card_Data.csv (from Kaggle competition dataset)
"""

import pandas as pd
import numpy as np
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import FancyBboxPatch
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_theme(style="whitegrid")

# ── Load & Clean Data ────────────────────────────────────────────────────────
df = pd.read_csv("EN_Card_Data.csv")

def clean_damage(val):
    if pd.isna(val): return 0
    nums = re.findall(r'\d+', str(val))
    return int(nums[0]) if nums else 0

def count_energy(val):
    if pd.isna(val): return 0
    return len(re.findall(r'\{.*?\}', str(val)))

df['Clean_Damage'] = df['Damage'].apply(clean_damage)
df['Energy_Cost'] = df['Cost'].apply(count_energy)
pokemon = df[df['HP'].notna()].copy()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE A: Energy Cost Analysis — H1: "Biggest damage wins" REJECTED
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

ax = axes[0]
cost_data = pokemon[pokemon['Clean_Damage'] > 0]
costs = cost_data['Energy_Cost'].value_counts().sort_index()
colors_energy = ['#4caf50', '#8bc34a', '#ff9800', '#f44336', '#b71c1c', '#880e4f']
ax.bar(costs.index, costs.values,
       color=[colors_energy[min(i, len(colors_energy)-1)] for i in costs.index],
       edgecolor='white', linewidth=1.2)
ax.set_xlabel('Energy Cost to Attack', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Attacks', fontsize=12, fontweight='bold')
ax.set_title('Energy Cost Distribution: Most Attacks Cost 1-2 Energy', fontsize=13, fontweight='bold')

ax = axes[1]
plot_data = cost_data[cost_data['Energy_Cost'].between(1, 4)]
bp = ax.boxplot([plot_data[plot_data['Energy_Cost'] == i]['Clean_Damage'].values
                  for i in range(1, 5)], patch_artist=True, widths=0.5)
ax.set_xticklabels(['1 Energy', '2 Energy', '3 Energy', '4 Energy'])
box_colors = ['#4caf50', '#8bc34a', '#ff9800', '#f44336']
for patch, color in zip(bp['boxes'], box_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)

# Highlight key attackers
for label, x, y, color in [
    ('Mega Emboar ex\n(320 dmg, 2\u25ca)', 2, 320, '#c62828'),
    ('Mega Dragonite ex\n(330 dmg, 3\u25ca)', 3, 330, '#e65100'),
    ('Mega Lucario ex\n(270 dmg, 2\u25ca)', 2, 270, '#4caf50'),
]:
    ax.scatter([x], [y], c=color, s=200, zorder=10, edgecolors='white', linewidth=2)
ax.set_xlabel('Energy Cost', fontsize=12, fontweight='bold')
ax.set_ylabel('Damage Output', fontsize=12, fontweight='bold')
ax.set_title('H1 Tested: 3-Energy Costs 1 Extra Turn for Only +10 Damage',
             fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig('figures/figA_energy_cost_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("[1/4] Figure A saved: Energy cost analysis")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE B: HP Survival — H2: "Speed is everything" REJECTED
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
damages = pokemon[pokemon['Clean_Damage'] > 0]['Clean_Damage'].sort_values()
cumulative = np.arange(1, len(damages) + 1) / len(damages) * 100

ax = axes[0]
ax.fill_between(damages, cumulative, alpha=0.3, color='#2196f3')
ax.plot(damages, cumulative, color='#1565c0', linewidth=2)
for dmg, label, color in [(230, 'Basic ex HP', '#4caf50'), (270, 'Stage 1 ex HP', '#ff9800'),
                            (320, 'Emboar OHKO', '#f44336'), (340, 'Stage 2 ex HP', '#9c27b0')]:
    ax.axvline(x=dmg, color=color, linestyle='--', linewidth=1.5, alpha=0.7)
ax.set_xlabel('Damage Output', fontsize=12, fontweight='bold')
ax.set_ylabel('Cumulative % of All Attacks', fontsize=12, fontweight='bold')
ax.set_title('What % of All Attacks OHKO Each HP Tier?', fontsize=13, fontweight='bold')

ax = axes[1]
attackers = [('Basic ex\n(avg 220 HP)', 220, '#4caf50'), ('Mega Lucario ex\n(340 HP)', 340, '#ff9800'),
             ('Mega Emboar ex\n(380 HP)', 380, '#f44336'), ('Mega Dragonite ex\n(370 HP)', 370, '#ff9800')]
x_pos = np.arange(len(attackers))
survival_pcts = [(damages < hp).mean() * 100 for _, hp, _ in attackers]
ax.bar(x_pos, survival_pcts, color=[a[2] for a in attackers], edgecolor='white', linewidth=1.5)
ax.set_xticks(x_pos)
ax.set_xticklabels([a[0] for a in attackers], fontsize=9)
ax.set_ylabel('% of Meta Attacks That Do NOT OHKO', fontsize=11, fontweight='bold')
ax.set_title('H2 Tested: Basic ex Gets OHKO\'d by Significant % of Meta', fontsize=13, fontweight='bold')
ax.set_ylim(0, 105)

plt.tight_layout()
fig.savefig('figures/figB_hp_survival.png', dpi=150, bbox_inches='tight')
plt.close()
print("[2/4] Figure B saved: HP survival analysis")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE C: The Sweet Spot — H3: Data reveals Mega Emboar ex
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 8))
att2plus = pokemon[(pokemon['Clean_Damage'] >= 150) & (pokemon['Energy_Cost'] >= 1)]
energy_colors = {1: '#4caf50', 2: '#2196f3', 3: '#ff9800', 4: '#f44336'}
for ec in [1, 2, 3, 4]:
    subset = att2plus[(att2plus['Energy_Cost'] == ec) & (att2plus['Clean_Damage'] >= 150)]
    ax.scatter(subset['HP'], subset['Clean_Damage'], c=energy_colors[ec],
               s=30, alpha=0.4, edgecolors='none', label=f'{ec} Energy (n={len(subset)})')

for cid, name, color in [(932, 'Mega Emboar ex', '#c62828'), (904, 'Mega Dragonite ex', '#e65100'),
                           (678, 'Mega Lucario ex', '#2e7d32'), (46, 'Gouging Fire ex', '#1565c0')]:
    card = pokemon[pokemon['Card ID'] == cid]
    if not card.empty:
        row = card.iloc[0]
        ax.scatter([row['HP']], [row['Clean_Damage']], c=color, s=250,
                   edgecolors='white', linewidth=2.5, zorder=10)

ax.axvspan(300, 400, alpha=0.08, color='#2196f3')
ax.set_xlabel('HP (Hit Points)', fontsize=12, fontweight='bold')
ax.set_ylabel('Damage Output', fontsize=12, fontweight='bold')
ax.set_title('Speed vs. Power: 2-Energy Attackers Hit the Optimal Efficiency Frontier',
             fontsize=14, fontweight='bold', pad=15)
ax.legend(loc='lower right', fontsize=10, title='Energy Cost')
plt.tight_layout()
fig.savefig('figures/figC_sweet_spot.png', dpi=150, bbox_inches='tight')
plt.close()
print("[3/4] Figure C saved: Speed vs. Power sweet spot")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5: Phase-Aware Decision Architecture
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis('off')

phases = [
    {'name': 'OPENING\n(Turns 1-2)', 'x': 1.5, 'color': '#4caf50',
     'actions': 'Deploy Basic Pokémon\nAttach Energy (ramp)\nUse draw Supporters\nSet up evolution bench',
     'priority': 'SURVIVAL & SETUP'},
    {'name': 'DEVELOPMENT\n(Turns 3-5)', 'x': 4.0, 'color': '#ff9800',
     'actions': 'Evolve to Stage 1/2\nAttach energy to attacker\nUse search Items\nPosition tech Pokémon',
     'priority': 'BOARD DEVELOPMENT'},
    {'name': 'AGGRESSION\n(Turns 6+)', 'x': 6.5, 'color': '#f44336',
     'actions': 'Attack for KOs\nBoss\'s Orders for prizes\nUse healing/swap tools\nManage prize trade',
     'priority': 'PRIZE OPTIMIZATION'},
    {'name': 'ENDGAME\n(≤2 Prizes)', 'x': 9.0, 'color': '#9c27b0',
     'actions': 'Maximize KO probability\nUse all remaining resources\nCalculate exact lethal\nPrevent opponent comeback',
     'priority': 'LETHAL CALCULATION'},
]

for phase in phases:
    rect = FancyBboxPatch((phase['x']-1.1, 0.8), 2.2, 3.8,
                          boxstyle="round,pad=0.3", facecolor=phase['color'],
                          edgecolor='white', linewidth=2, alpha=0.15)
    ax.add_patch(rect)
    rect2 = FancyBboxPatch((phase['x']-1.1, 0.8), 2.2, 3.8,
                           boxstyle="round,pad=0.3", facecolor='none',
                           edgecolor=phase['color'], linewidth=2.5)
    ax.add_patch(rect2)
    ax.text(phase['x'], 4.2, phase['name'], ha='center', va='center',
            fontsize=12, fontweight='bold', color=phase['color'])
    ax.text(phase['x'], 2.8, phase['actions'], ha='center', va='center',
            fontsize=9, color='#37474f', linespacing=1.5)
    ax.text(phase['x'], 1.2, phase['priority'], ha='center', va='center',
            fontsize=8, fontweight='bold', color=phase['color'],
            bbox=dict(boxstyle='round', facecolor='white', edgecolor=phase['color'], alpha=0.8))

for i in range(len(phases)-1):
    ax.annotate('', xy=(phases[i+1]['x']-1.15, 3.0), xytext=(phases[i]['x']+1.15, 3.0),
                arrowprops=dict(arrowstyle='->', color='#78909c', lw=2.5,
                               connectionstyle='arc3,rad=0'))

ax.text(5.0, 0.25,
        'ATTACK: 0→20→20000→50000 | ENERGY: 5000→8000→3000→0 | DRAW: 3000→2000→500→500',
        ha='center', fontsize=8, color='#78909c', style='italic')
ax.set_title('Phase-Aware Decision Architecture: Dynamic Action Priorities Across Game Stages',
             fontsize=14, fontweight='bold', pad=10)
plt.tight_layout()
fig.savefig('figures/fig5_phase_strategy.png', dpi=150, bbox_inches='tight')
plt.close()
print("[4/4] Figure 5 saved: Phase strategy diagram")


# ── Print Key Stats for Report ───────────────────────────────────────────────
all_damages = pokemon[pokemon['Clean_Damage'] > 0]['Clean_Damage']
print("\n=== KEY STATISTICS ===")
print(f"Total cards: {len(df)}, Pokémon with attacks: {len(all_damages)}")
print(f"Attacks at 1 energy: {(pokemon['Energy_Cost']==1).mean()*100:.1f}%")
print(f"Attacks at 2 energy: {(pokemon['Energy_Cost']==2).mean()*100:.1f}%")
print(f"Attacks at 3 energy: {(pokemon['Energy_Cost']==3).mean()*100:.1f}%")
print(f"Meta OHKOs 230 HP (Basic ex): {(all_damages>=230).mean()*100:.1f}%")
print(f"Meta OHKOs 340 HP (Lucario): {(all_damages>=340).mean()*100:.1f}%")
print(f"Meta OHKOs 380 HP (Emboar): {(all_damages>=380).mean()*100:.1f}%")

emboar_dpe = pokemon[pokemon['Card ID']==932]['Clean_Damage'].iloc[0] / max(pokemon[pokemon['Card ID']==932]['Energy_Cost'].iloc[0],1)
lucario_dpe = pokemon[pokemon['Card ID']==678]['Clean_Damage'].iloc[0] / max(pokemon[pokemon['Card ID']==678]['Energy_Cost'].iloc[0],1)
print(f"Mega Emboar ex: {emboar_dpe:.0f} dmg/energy")
print(f"Mega Lucario ex: {lucario_dpe:.0f} dmg/energy")
print(f"Emboar advantage: {(emboar_dpe/lucario_dpe - 1)*100:.1f}% more efficient")
print(f"Fire weaknesses in meta: {pokemon['Weakness'].value_counts().get('{R}', 0)}")
print(f"Fighting weaknesses: {pokemon['Weakness'].value_counts().get('{F}', 0)}")
print("\nDone. All analysis complete.")
