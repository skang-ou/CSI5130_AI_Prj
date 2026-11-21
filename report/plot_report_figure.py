#!/usr/bin/env python3
"""Create a compact report figure from the existing evaluation summary."""
import json
import os
import tempfile
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'csi5130-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
summary = json.loads((root / 'results/evaluation_summary.json').read_text())['strategies']
fig, ax = plt.subplots(figsize=(8, 2.8))
left = [0, 0, 0]
for score, label, color in [(2, 'None (2)', '#78aa95'), (1, 'Minor (1)', '#e7b45c'), (0, 'Material (0)', '#b8544d')]:
    counts = [group['criterion_counts']['unsupported_behavior'][str(score)] for group in summary.values()]
    bars = ax.barh(['Zero-Shot', 'Structured', 'Few-Shot'], counts, left=left, color=color, label=label, height=0.55)
    ax.bar_label(bars, labels=[str(value) if value else '' for value in counts], label_type='center', fontsize=10)
    left = [a+b for a,b in zip(left,counts)]
ax.invert_yaxis()
ax.set(xlim=(0,30), xticks=range(0,31,5), xlabel='Reviewed cases per strategy', title='Unsupported additions by severity')
for side in ['top','right']:ax.spines[side].set_visible(False)
ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(.5,-.3), frameon=False, fontsize=9)
fig.tight_layout()
for extension in ['png','svg']:
    fig.savefig(root / f'report/figures/unsupported_additions.{extension}', dpi=200, bbox_inches='tight', facecolor='white')
plt.close(fig)
