#!/usr/bin/env python3
"""Validate authored semantic reviews and compute rubric-based results offline.

This script checks provenance, completeness, and arithmetic. It does not invent
semantic ratings or grade by text similarity; ratings live in evaluation/reviews.json.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(root):
    """Reject changed source artifacts before using their associated reviews."""
    config = read_json(root / 'evaluation/rubric.json')
    plan = read_json(root / 'evaluation/review_plan.json')
    bundle = read_json(root / 'evaluation/reviews.json')
    for name, expected in plan['source_sha256'].items():
        if fingerprint(root / name) != expected:
            raise ValueError(f'Source fingerprint mismatch: {name}')
    for name, expected in (
        (plan['rubric_file'], plan['rubric_sha256']),
        ('evaluation/rubric.md', plan['rubric_document_sha256']),
    ):
        if fingerprint(root / name) != expected:
            raise ValueError(f'Rubric fingerprint mismatch: {name}')
    with (root / 'data/requirements.csv').open(encoding='utf-8-sig', newline='') as stream:
        requirements = {r['requirement_id']: r for r in csv.DictReader(stream)}
    outputs = {}
    for strategy in config['strategies']:
        with (root / f'results/{strategy}_results.csv').open(encoding='utf-8-sig', newline='') as stream:
            outputs[strategy] = {r['requirement_id']: r for r in csv.DictReader(stream)}
    return config, plan, requirements, outputs, bundle


def validate_reviews(config, plan, requirements, outputs, bundle):
    """Require one complete, evidenced review for every planned strategy/ID pair."""
    criteria = [c['id'] for c in config['criteria']]
    expected = {(c['requirement_id'], c['strategy']): c for c in plan['cases']}
    if len(expected) != plan['expected_case_count']:
        raise ValueError('The review plan contains duplicate or missing cases.')
    if bundle['rubric_version'] != config['version'] or plan['rubric_version'] != config['version']:
        raise ValueError('Rubric version mismatch.')
    rows, seen = [], set()
    for record in bundle['records']:
        pair = (record['requirement_id'], record['strategy'])
        if pair not in expected or pair in seen:
            raise ValueError(f'Unknown or duplicate review: {pair}')
        seen.add(pair)
        if record['review_id'] != expected[pair]['review_id'] or record['rubric_version'] != config['version']:
            raise ValueError(f'Review identifier/version mismatch: {pair}')
        scores, reasons = record['scores'], record['rationales']
        if set(scores) != set(criteria) or set(reasons) != set(criteria):
            raise ValueError(f'Criterion keys mismatch: {pair}')
        # bool is a Python int subclass; explicitly exclude it as a quality score.
        if any(type(scores[k]) is not int or scores[k] not in config['allowed_scores'] for k in criteria):
            raise ValueError(f'Invalid or unreviewed score: {pair}')
        if any(not isinstance(reasons[k], str) or not reasons[k].strip() for k in criteria):
            raise ValueError(f'Missing criterion rationale: {pair}')
        if any(not isinstance(record.get(k), str) or not record[k].strip()
               for k in ['reviewer', 'reviewer_type', 'review_date', 'reference_notes']):
            raise ValueError(f'Missing reviewer metadata or reference notes: {pair}')
        requirement = requirements[pair[0]]
        output = outputs[pair[1]][pair[0]]
        # Evidence snapshots bind each judgment to the exact text actually generated.
        if record['requirement'] != requirement['requirement']:
            raise ValueError(f'Requirement evidence mismatch: {pair}')
        for field in ['given', 'when', 'then']:
            if record['reference'][field] != requirement[f'reference_{field}']:
                raise ValueError(f'Reference evidence mismatch: {pair}')
            if record['generated'][field] != output[f'generated_{field}']:
                raise ValueError(f'Generated evidence mismatch: {pair}')
        if output['status'] != 'success' and any(scores.values()):
            raise ValueError(f'Failed generation must receive five zeros: {pair}')
        total = sum(scores[c['id']] * c['weight'] for c in config['criteria'])
        rows.append(dict(review_id=record['review_id'], requirement_id=pair[0],
                         strategy=pair[1], difficulty=requirement['difficulty'],
                         generation_status=output['status'], rubric_version=config['version'],
                         **scores, total_score=total,
                         normalized_score=total / config['aggregation']['total_max'],
                         reviewer=record['reviewer'], reviewer_type=record['reviewer_type'],
                         review_date=record['review_date']))
    if seen != set(expected):
        raise ValueError('Incomplete review set; final summaries require every planned review.')
    return rows


def aggregate(rows, criteria):
    """Keep criterion distributions and unsupported-addition severity visible."""
    count = len(rows)
    return dict(
        scored_count=count,
        generation_success_count=sum(r['generation_status'] == 'success' for r in rows),
        mean_total=sum(r['total_score'] for r in rows) / count,
        mean_normalized=sum(r['normalized_score'] for r in rows) / count,
        total_distribution={str(k): v for k, v in sorted(Counter(r['total_score'] for r in rows).items())},
        full_score_count=sum(r['total_score'] == 10 for r in rows),
        criterion_means={k: sum(r[k] for r in rows) / count for k in criteria},
        criterion_counts={k: {str(v): sum(r[k] == v for r in rows) for v in [0, 1, 2]} for k in criteria},
        minor_unsupported_count=sum(r['unsupported_behavior'] == 1 for r in rows),
        material_unsupported_count=sum(r['unsupported_behavior'] == 0 for r in rows),
    )


def make_summary(config, plan, bundle, rows):
    criteria = [c['id'] for c in config['criteria']]
    strategies = {}
    for strategy in config['strategies']:
        selected = [r for r in rows if r['strategy'] == strategy]
        strategies[strategy] = aggregate(selected, criteria)
        strategies[strategy]['by_difficulty'] = {
            level: aggregate([r for r in selected if r['difficulty'] == level], criteria)
            for level in ['Easy', 'Medium', 'Hard']
        }
    return dict(rubric_version=config['version'], review_count=len(rows),
                method=bundle['method'], blinded=bundle['blinded'],
                independent_human_validation=bundle['independent_human_validation'],
                source_sha256=plan['source_sha256'], strategies=strategies)


def make_report(config, bundle, summary):
    lines = [
        '# Evaluation results', '',
        'Rubric: v1.0. Review date: November 18, 2026.', '',
        '**Method:** ' + bundle['method'], '',
        'All 90 saved outputs received five authored semantic scores and criterion-specific',
        'rationales. The evaluator validates those judgments and computes arithmetic; it',
        'does not independently establish their correctness. No new API calls were made.', '',
        '## Quantitative results', '',
        'All strategies have 30/30 successful generation records and 30/30 scored cases.',
        'Generation success is separate from the rubric scores below.', '',
        '| Strategy | Mean total /10 | Full scores /30 | Minor unsupported additions | Material unsupported additions |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for strategy, group in summary['strategies'].items():
        lines.append(f"| {strategy} | {group['mean_total']:.4f} | {group['full_score_count']} | {group['minor_unsupported_count']} | {group['material_unsupported_count']} |")
    lines += ['', 'Full-score counts are descriptive rubric outcomes, not validated accuracy or pass rates.', '',
              '### Mean criterion scores (0 to 2)', '',
              '| Strategy | Preconditions | Trigger | Expected behavior | Conditions / boundaries | No unsupported behavior |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for strategy, group in summary['strategies'].items():
        values = ' | '.join(f"{group['criterion_means'][c['id']]:.4f}" for c in config['criteria'])
        lines.append(f'| {strategy} | {values} |')
    lines += ['', '### Difficulty breakdown (10 cases per cell)', '',
              '| Strategy | Easy mean /10 | Medium mean /10 | Hard mean /10 |',
              '| --- | ---: | ---: | ---: |']
    for strategy, group in summary['strategies'].items():
        means = ' | '.join(f"{group['by_difficulty'][d]['mean_total']:.4f}" for d in ['Easy', 'Medium', 'Hard'])
        lines.append(f'| {strategy} | {means} |')
    lines += ['', 'Exact means, per-criterion 0/1/2 counts and total distributions are in',
              '`evaluation_summary.json`. Every case score is in `evaluation_scores.csv`;',
              'evidence snapshots and all 450 rationales are in `../evaluation/reviews.json`.', '',
              '## Representative examples', '']
    examples = [
        ('REQ-002', 'zero_shot', 'Successful guarded threshold test'),
        ('REQ-013', 'few_shot', 'Successful response-deadline test'),
        ('REQ-018', 'zero_shot', 'Structural weakness requiring clarification'),
        ('REQ-023', 'zero_shot', 'Unsupported acceptance assertion'),
        ('REQ-023', 'few_shot', 'Same logical error despite reference agreement'),
        ('REQ-023', 'structured', 'Valid negative boundary despite reference disagreement'),
        ('REQ-010', 'zero_shot', 'Minor unnecessary setup restriction'),
    ]
    index = {(r['requirement_id'], r['strategy']): r for r in bundle['records']}
    for rid, strategy, label in examples:
        record = index[(rid, strategy)]
        lines += [f'### {rid} ({strategy}): {label}', '',
                  'Requirement: ' + record['requirement'], '',
                  '- Given: ' + record['generated']['given'],
                  '- When: ' + record['generated']['when'],
                  '- Then: ' + record['generated']['then'], '',
                  'Scores in rubric order (Given, When, Then, coverage, unsupported): ' +
                  ', '.join(str(record['scores'][c['id']]) for c in config['criteria']) +
                  f". Total: {sum(record['scores'].values())}/10.", '']
        for c in config['criteria']:
            if record['scores'][c['id']] < 2:
                lines += ['- ' + c['name'] + ': ' + record['rationales'][c['id']]]
        if all(v == 2 for v in record['scores'].values()):
            lines += [record['rationales']['expected_behavior_correctness']]
        lines += ['', 'Reference comparison: ' + record['reference_notes'], '']
    lines += [
        '## Interpretation and limitations', '',
        '- Structured receives full credit throughout this particular review. This is a ceiling',
        '  effect under the stated single-scenario rubric, not evidence of exhaustive coverage.',
        '- Most outputs share similar wording and valid scenarios. A small number of judgments',
        '  drive the score differences; do not infer broad superiority from these means.',
        '- REQ-023 explains both material unsupported additions. The issue is a necessary versus',
        '  sufficient condition, not a malformed response or API failure.',
        '- The minor setup ratings in Zero-Shot REQ-010 and REQ-019 follow the rubric\'s',
        '  unnecessary-restriction anchor. Compatible observable-output setup is allowed:',
        '  for example, an initially clear fault or available freeze-frame signals.',
        '- The three low scores for Zero-Shot REQ-018 have separate rationales: misplaced',
        '  request receipt, vague When, and an unsupported incidental processing step.',
        '- Ratings come from one unblinded AI reviewer that also assisted with the project.',
        '  There is no independent human validation or inter-rater reliability estimate.',
        '- The rubric followed generation and preliminary inspection. It is not preregistered,',
        '  and 30 synthetic requirements with one output per pair limit generalization.',
        '- A full score does not require a test suite, executable hardware tests, or every',
        '  positive/negative branch. It means this one scenario satisfies rubric v1.0.',
        '- Charts and deeper paired strategy analysis remain task #5.', '',
        '## Reproduction', '', 'From the repository root:', '', '```bash',
        'python src/evaluator.py', 'python -m unittest discover -s tests -v', '```', '',
        'These commands need no API key or network for evaluation. The full test suite',
        'also imports the generator and therefore requires its installed OpenAI package.', '',
        'The review plan preserves source fingerprints. A display-label repair to',
        '`rubric.json` is recorded in its metadata; scoring anchors, IDs, weights and',
        'the rubric document were unchanged. Evaluation artifacts contain the same',
        'five criterion IDs and rubric version for all three strategies.', '',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    config, plan, requirements, outputs, bundle = load_inputs(args.root)
    rows = validate_reviews(config, plan, requirements, outputs, bundle)
    summary = make_summary(config, plan, bundle, rows)
    # Bind generated summaries to their source reviews and rubric as well as raw inputs.
    summary['evaluation_sha256'] = {name: fingerprint(args.root / name) for name in
                                    ['evaluation/rubric.json', 'evaluation/reviews.json']}
    destination = args.root / 'results'
    with (destination / 'evaluation_scores.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (destination / 'evaluation_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (destination / 'evaluation_report.md').write_text(make_report(config, bundle, summary), encoding='utf-8')
    print(f'Validated and summarized {len(rows)} semantic reviews.')
    for strategy, group in summary['strategies'].items():
        print(f"{strategy}: {group['mean_total']:.4f}/10 ({group['scored_count']}/30 scored)")


if __name__ == '__main__':
    main()
