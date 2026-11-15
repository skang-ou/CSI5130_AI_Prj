#!/usr/bin/env python3
"""Analyze frozen rubric ratings and export reproducible tables and static charts.

Ratings are existing single-reviewer AI judgments. This script neither changes
scores nor treats them as independent accuracy measurements.
"""
import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

if __package__:
    from . import evaluator
else:
    import evaluator

LABELS = {'zero_shot': 'Zero-Shot', 'structured': 'Structured', 'few_shot': 'Few-Shot'}
COLORS = {'zero_shot': '#3477a4', 'structured': '#d47b22', 'few_shot': '#39846a'}
CRITERIA_LABELS = ['Preconditions', 'Trigger', 'Expected\nbehavior', 'Conditions /\nboundaries', 'No unsupported\nbehavior']
CHARTS = ['strategy_means', 'criterion_means', 'difficulty_means', 'unsupported_additions', 'case_scores']


def paired_comparison(rows, strategy_a, strategy_b):
    """Join by requirement ID so aggregate differences retain the paired design."""
    a = {r['requirement_id']: r['total_score'] for r in rows if r['strategy'] == strategy_a}
    b = {r['requirement_id']: r['total_score'] for r in rows if r['strategy'] == strategy_b}
    if not a or a.keys() != b.keys():
        raise ValueError('Paired strategies must cover the same nonempty requirement set.')
    deltas = {rid: a[rid] - b[rid] for rid in sorted(a)}
    return dict(strategy_a=strategy_a, strategy_b=strategy_b, count=len(deltas),
                mean_delta=sum(deltas.values()) / len(deltas),
                higher=sum(d > 0 for d in deltas.values()),
                equal=sum(d == 0 for d in deltas.values()),
                lower=sum(d < 0 for d in deltas.values()), deltas=deltas)


def analyze(rows, summary, config):
    """Describe score differences without adding significance or causal claims."""
    pairs = [paired_comparison(rows, a, b) for a, b in [
        ('structured', 'zero_shot'), ('few_shot', 'zero_shot'), ('structured', 'few_shot')]]
    criteria = [c['id'] for c in config['criteria']]
    losses = []
    for row in rows:
        if row['total_score'] < 10:
            losses.append(dict(requirement_id=row['requirement_id'], strategy=row['strategy'],
                               difficulty=row['difficulty'], total_score=row['total_score'],
                               points_below_maximum=10 - row['total_score'],
                               **{key + '_loss': 2 - row[key] for key in criteria}))
    # Leave-one-requirement-out summaries measure sensitivity, not replacement scores.
    ids = sorted({r['requirement_id'] for r in rows})
    sensitivity = []
    for rid in ids:
        means = {strategy: sum(r['total_score'] for r in rows if r['strategy'] == strategy and r['requirement_id'] != rid) /
                 sum(r['strategy'] == strategy and r['requirement_id'] != rid for r in rows)
                 for strategy in config['strategies']}
        sensitivity.append(dict(excluded_requirement_id=rid, **means))
    return dict(rubric_version=config['version'], case_count=len(rows),
                interpretation='Descriptive analysis of unblinded single-reviewer AI ratings; no independent human validation.',
                strategies=summary['strategies'], paired_comparisons=pairs,
                cases_below_maximum=losses, leave_one_requirement_out=sensitivity)


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_tables(destination, analysis, config):
    strategies = analysis['strategies']
    write_csv(destination / 'strategy_comparison.csv', [dict(
        strategy=s, scored_count=g['scored_count'], mean_total=g['mean_total'],
        full_score_count=g['full_score_count'], **g['criterion_means']) for s, g in strategies.items()])
    write_csv(destination / 'difficulty_comparison.csv', [dict(
        strategy=s, difficulty=d, scored_count=v['scored_count'], mean_total=v['mean_total'])
        for s, g in strategies.items() for d, v in g['by_difficulty'].items()])
    write_csv(destination / 'criterion_distributions.csv', [dict(
        strategy=s, criterion=c['id'], score=score, count=g['criterion_counts'][c['id']][str(score)])
        for s, g in strategies.items() for c in config['criteria'] for score in [0, 1, 2]])
    write_csv(destination / 'unsupported_additions.csv', [dict(
        strategy=s, no_unsupported_count=g['criterion_counts']['unsupported_behavior']['2'],
        minor_count=g['minor_unsupported_count'], material_count=g['material_unsupported_count'],
        scored_count=g['scored_count']) for s, g in strategies.items()])
    write_csv(destination / 'paired_comparisons.csv', [{k: v for k, v in p.items() if k != 'deltas'}
                                                      for p in analysis['paired_comparisons']])
    write_csv(destination / 'paired_differences.csv', [dict(
        requirement_id=rid, strategy_a=p['strategy_a'], strategy_b=p['strategy_b'], delta=delta)
        for p in analysis['paired_comparisons'] for rid, delta in p['deltas'].items()])
    write_csv(destination / 'score_loss_cases.csv', analysis['cases_below_maximum'])
    write_csv(destination / 'leave_one_requirement_out.csv', analysis['leave_one_requirement_out'])


def render_charts(destination, analysis, rows, config):
    # Cache locally and use a headless backend; plotting requires no GUI or network.
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'csi5130-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none', 'savefig.dpi': 180})
    destination.mkdir(parents=True, exist_ok=True)
    strategies = config['strategies']
    groups = analysis['strategies']
    note = 'Rubric v1.0, single AI reviewer. Descriptive scores; no independent human validation.'

    def save(fig, name):
        fig.text(0.01, 0.015, note, fontsize=8, color='#4a4a4a')
        fig.tight_layout(rect=(0, 0.06, 1, 0.98))
        for extension in ['png', 'svg']:
            fig.savefig(destination / f'{name}.{extension}', facecolor='white')
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    values = [groups[s]['mean_total'] for s in strategies]
    bars = ax.bar([LABELS[s] for s in strategies], values, width=0.55, color=[COLORS[s] for s in strategies])
    ax.bar_label(bars, labels=[f'{v:.4f}' for v in values], padding=4)
    ax.set(ylim=(0, 10.8), yticks=range(0, 11, 2), ylabel='Mean total rubric score (0 to 10)',
           title='Mean quality scores across 30 requirements per strategy')
    ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    save(fig, 'strategy_means')

    fig, ax = plt.subplots(figsize=(11, 5.6))
    keys = [c['id'] for c in config['criteria']]
    for i, s in enumerate(strategies):
        bars = ax.bar([x + (i-1)*0.25 for x in range(5)],
                      [groups[s]['criterion_means'][k] for k in keys], width=0.24,
                      color=COLORS[s], label=LABELS[s])
        ax.bar_label(bars, labels=[f'{groups[s]["criterion_means"][k]:.2f}' for k in keys], padding=3, fontsize=8)
    ax.set(xticks=range(5), xticklabels=CRITERIA_LABELS, ylim=(0, 2.35), yticks=[0, .5, 1, 1.5, 2],
           ylabel='Mean criterion score (0 to 2)', title='Criterion means: higher is better in every column')
    ax.legend(ncol=3, loc='upper center', frameon=False)
    ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    save(fig, 'criterion_means')

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, s in enumerate(strategies):
        vals = [groups[s]['by_difficulty'][d]['mean_total'] for d in ['Easy', 'Medium', 'Hard']]
        bars = ax.bar([x + (i-1)*0.25 for x in range(3)], vals, width=0.24, color=COLORS[s], label=LABELS[s])
        ax.bar_label(bars, labels=[f'{v:.2f}' for v in vals], padding=3, fontsize=9)
    ax.set(xticks=range(3), xticklabels=['Easy', 'Medium', 'Hard'], ylim=(0, 12), yticks=range(0, 11, 2),
           ylabel='Mean total rubric score (0 to 10)', title='Difficulty breakdown: 10 requirements per strategy in each group')
    ax.legend(ncol=3, loc='upper center', frameon=False)
    ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    save(fig, 'difficulty_means')

    fig, ax = plt.subplots(figsize=(10, 5.2))
    left = [0, 0, 0]
    for score, label, color in [(2, 'None (score 2)', '#78aa95'), (1, 'Minor addition (score 1)', '#e7b45c'), (0, 'Material addition (score 0)', '#b8544d')]:
        counts = [groups[s]['criterion_counts']['unsupported_behavior'][str(score)] for s in strategies]
        bars = ax.barh([LABELS[s] for s in strategies], counts, left=left, color=color, label=label, height=0.55)
        ax.bar_label(bars, labels=[str(v) if v else '' for v in counts], label_type='center', fontsize=11)
        left = [a+b for a, b in zip(left, counts)]
    ax.invert_yaxis()
    ax.set(xlim=(0, 30), xticks=range(0, 31, 5), xlabel='Number of reviewed cases (30 per strategy)',
           title='Unsupported additions: minor assumptions versus material inventions')
    ax.legend(ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.32), frameon=False, fontsize=9)
    # Extra bottom space keeps the legend clear of the source note.
    fig.subplots_adjust(bottom=0.26)
    save(fig, 'unsupported_additions')

    fig, ax = plt.subplots(figsize=(8, 11))
    ids = sorted({r['requirement_id'] for r in rows})
    lookup = {(r['requirement_id'], r['strategy']): r['total_score'] for r in rows}
    values = [[lookup[(rid, s)] for s in strategies] for rid in ids]
    image = ax.imshow(values, cmap='YlGnBu', vmin=0, vmax=10, aspect='auto')
    for y, vals in enumerate(values):
        for x, value in enumerate(vals):
            ax.text(x, y, str(value), ha='center', va='center', color='white' if value >= 7 else '#111111', fontsize=9)
    ax.set(xticks=range(3), xticklabels=[LABELS[s] for s in strategies], yticks=range(30), yticklabels=ids,
           title='Per-requirement total scores: differences cluster in four IDs')
    ax.tick_params(axis='y', labelsize=9)
    for y in [9.5, 19.5]: ax.axhline(y, color='white', linewidth=2)
    colorbar = fig.colorbar(image, ax=ax, pad=0.04)
    colorbar.set_label('Total rubric score (0 to 10)')
    save(fig, 'case_scores')


def make_report(analysis, config):
    groups = analysis['strategies']
    lines = ['# Analysis and visualization', '',
             'Rubric v1.0. All 90 cases are scored: 30 per strategy, with 10 per difficulty.', '',
             '**Evidence scope:** Unblinded ratings from one AI reviewer, without independent',
             'human validation. The reviewer also assisted with the implementation and rubric.',
             'The rubric followed generation. This is descriptive analysis of these ratings,',
             'not a validated accuracy estimate, causal comparison, or significance claim.', '',
             '## Average quality and paired differences', '',
             '| Strategy | Mean total /10 | Full-score cases /30 |', '| --- | ---: | ---: |']
    for s, g in groups.items(): lines.append(f"| {LABELS[s]} | {g['mean_total']:.4f} | {g['full_score_count']} |")
    lines += ['', '![Mean quality scores](charts/strategy_means.png)', '',
              '| A minus B | Mean paired difference /10 | A higher | Equal | A lower |',
              '| --- | ---: | ---: | ---: | ---: |']
    for p in analysis['paired_comparisons']:
        lines.append(f"| {LABELS[p['strategy_a']]} minus {LABELS[p['strategy_b']]} | {p['mean_delta']:+.4f} | {p['higher']} | {p['equal']} | {p['lower']} |")
    lines += ['', 'Pairing uses the same requirement ID, not unrelated samples. Structured exceeds',
              'Zero-Shot on REQ-010, REQ-018, REQ-019 and REQ-023; the other 26 pairs tie.',
              'Few-Shot exceeds Zero-Shot only on the first three of those IDs, while both',
              'have the REQ-023 necessary/sufficient-condition error. Structured exceeds',
              'Few-Shot only on REQ-023. Small score differences depend on a few judgments.', '',
              '## Trigger and expected-behavior correctness', '',
              '| Strategy | Trigger mean /2 | Trigger counts 0 / 1 / 2 | Expected mean /2 | Expected counts 0 / 1 / 2 |',
              '| --- | ---: | --- | ---: | --- |']
    for s, g in groups.items():
        counts = lambda key: ' / '.join(str(g['criterion_counts'][key][str(v)]) for v in [0, 1, 2])
        lines.append(f"| {LABELS[s]} | {g['criterion_means']['trigger_correctness']:.4f} | {counts('trigger_correctness')} | {g['criterion_means']['expected_behavior_correctness']:.4f} | {counts('expected_behavior_correctness')} |")
    lines += ['', 'Zero-Shot REQ-018 receives trigger score 1: request receipt is already in Given,',
              'and When says only "The system processes the charging request". Structured',
              'uses request receipt with successful locking established; Few-Shot uses a',
              'joint request/locking event. Both alternatives are accepted by the rubric.', '',
              'Zero-Shot and Few-Shot REQ-023 each receive expected-behavior score 0.',
              'A valid checksum and age below 100 ms are necessary for acceptance, but the',
              'requirement does not guarantee acceptance whenever they hold. The reference',
              'makes the same unsupported inference. Structured instead rejects at exactly',
              '100 ms, which follows from the strict age limit.', '',
              '![Criterion mean scores](charts/criterion_means.png)', '',
              '## Condition/boundary fidelity and unsupported additions', '',
              '| Strategy | Conditions mean /2 | Full condition score /30 | No unsupported mean /2 | None | Minor | Material |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s, g in groups.items():
        lines.append(f"| {LABELS[s]} | {g['criterion_means']['condition_boundary_coverage']:.4f} | {g['criterion_counts']['condition_boundary_coverage']['2']} | {g['criterion_means']['unsupported_behavior']:.4f} | {g['criterion_counts']['unsupported_behavior']['2']} | {g['minor_unsupported_count']} | {g['material_unsupported_count']} |")
    lines += ['', 'Every case receives condition/boundary score 2. This criterion measures fidelity',
              'within the chosen single scenario, not coverage of every boundary or negative',
              'branch. It therefore has no discriminating power in this dataset. In REQ-023,',
              'correctly stated input constraints can receive condition credit even while the',
              'asserted acceptance fails expected behavior and unsupported-behavior criteria.', '',
              'The rubric defines unsupported behavior in the reverse direction to severity:',
              '2 means none, 1 a minor addition, and 0 a material invention. Zero-Shot has',
              'minor additions in REQ-010 (system operational), REQ-018 (incidental processing',
              'step), and REQ-019 (known current torque). Both material additions occur on',
              'REQ-023, one in Zero-Shot and one in Few-Shot. These are overlapping criterion',
              'penalties for the same logical error, not independent hallucination events.', '',
              'The three REQ-018 penalties likewise reflect different aspects of one scenario:',
              'misplaced receipt, vague When, and an unsupported processing assumption. Totals',
              'should be read alongside these criterion-level reasons.', '',
              '![Unsupported addition counts](charts/unsupported_additions.png)', '',
              '## Difficulty and concentration of score losses', '',
              '| Strategy | Easy /10 | Medium /10 | Hard /10 |', '| --- | ---: | ---: | ---: |']
    for s, g in groups.items():
        lines.append('| ' + LABELS[s] + ' | ' + ' | '.join(f"{g['by_difficulty'][d]['mean_total']:.4f}" for d in ['Easy', 'Medium', 'Hard']) + ' |')
    lines += ['', '![Mean scores by difficulty](charts/difficulty_means.png)', '',
              'Zero-Shot loses 9 of 300 possible points: REQ-010 loses 1, REQ-018 loses 3,',
              'REQ-019 loses 1, and REQ-023 loses 4. Few-Shot loses 4 points, all on REQ-023.',
              'Structured loses none. This does not establish a monotonic difficulty effect:',
              'there are only 10 synthetic cases per level and one output per case.', '',
              '![Total scores for all 30 requirements](charts/case_scores.png)', '',
              '## Sensitivity to one requirement', '',
              'A leave-one-requirement-out table is supplied for all 30 IDs. It does not',
              'replace the primary 30-case results. Excluding REQ-023 for illustration gives:', '',
              '| Strategy | Primary mean /10 (n=30) | Mean excluding REQ-023 (n=29) |', '| --- | ---: | ---: |']
    leave = next(r for r in analysis['leave_one_requirement_out'] if r['excluded_requirement_id'] == 'REQ-023')
    for s, g in groups.items(): lines.append(f"| {LABELS[s]} | {g['mean_total']:.4f} | {leave[s]:.4f} |")
    lines += ['', 'The Structured/Few-Shot difference disappears without REQ-023. That makes its',
              'logical interpretation and reference defect especially important for human',
              'review. No outlier is removed from the primary analysis, and no significance',
              'test or confidence interval is inferred from this deterministic sensitivity check.', '',
              '## Conclusions supported by this review', '',
              '- Structured has the highest recorded mean, but only four paired differences',
              '  separate it from Zero-Shot and only one separates it from Few-Shot.',
              '- Trigger structure improves in the REQ-018 examples; the main expected-behavior',
              '  failure is the REQ-023 logical implication, not a missing output field.',
              '- Condition/boundary scores show a ceiling for all strategies. Full credit for',
              '  one scenario says nothing about exhaustive test generation or hardware coverage.',
              '- Independent human review, especially of REQ-023 and the minor-assumption',
              '  ratings, is the strongest next check before claiming a performance advantage.',
              '- More independent requirements and repeated generations would be needed to',
              '  study generalization and output variation. Neither is measured here.', '',
              '## Artifacts and reproduction', '',
              '- `analysis_summary.json`: exact analysis, paired deltas and source fingerprints.',
              '- `strategy_comparison.csv`, `difficulty_comparison.csv`: mean-score tables.',
              '- `criterion_distributions.csv`: all 45 criterion/strategy/score counts.',
              '- `unsupported_additions.csv`: counts separated by severity.',
              '- `paired_comparisons.csv`, `paired_differences.csv`: joined ID comparisons.',
              '- `score_loss_cases.csv`: every case below the maximum.',
              '- `leave_one_requirement_out.csv`: all 30 exclusion summaries.',
              '- `charts/`: five figures, each in PNG and editable vector SVG formats.', '',
              'From the repository root, use an environment with Matplotlib installed:', '',
              '```bash', 'python -m pip install -r requirements-analysis.txt',
              'python src/analyze_results.py', '```', '',
              'No model calls or API credentials are needed. The script validates the frozen',
              'ratings and source hashes before plotting, checks the stored evaluation summary',
              'for consistency, and leaves requirements, generated outputs and reviews unchanged.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    config, plan, requirements, outputs, bundle = evaluator.load_inputs(args.root)
    rows = evaluator.validate_reviews(config, plan, requirements, outputs, bundle)
    summary = evaluator.make_summary(config, plan, bundle, rows)
    stored = evaluator.read_json(args.root / 'results/evaluation_summary.json')
    if summary['strategies'] != stored['strategies']:
        raise ValueError('Stored evaluation summary is stale; rerun src/evaluator.py first.')
    analysis = analyze(rows, summary, config)
    analysis['source_sha256'] = {name: evaluator.fingerprint(args.root / name) for name in [
        'evaluation/rubric.json', 'evaluation/reviews.json', 'evaluation/review_plan.json',
        'results/evaluation_summary.json', 'src/analyze_results.py']}
    destination = args.root / 'results/analysis'
    destination.mkdir(parents=True, exist_ok=True)
    render_charts(destination / 'charts', analysis, rows, config)
    write_tables(destination, analysis, config)
    (destination / 'analysis_summary.json').write_text(json.dumps(analysis, indent=2) + '\n', encoding='utf-8')
    (destination / 'analysis_report.md').write_text(make_report(analysis, config), encoding='utf-8')
    print('Analyzed 90 existing ratings; exported eight CSV tables and five PNG/SVG chart pairs.')
    for p in analysis['paired_comparisons']:
        print(f"{p['strategy_a']} minus {p['strategy_b']}: {p['mean_delta']:+.4f}; {p['higher']} higher, {p['equal']} equal, {p['lower']} lower")


if __name__ == '__main__':
    main()
