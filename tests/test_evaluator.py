"""Offline integrity and arithmetic checks; these do not validate semantic judgments."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from src import evaluator


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.inputs = evaluator.load_inputs(cls.root)

    def validate(self, bundle):
        # Reuse frozen inputs, but let each test mutate an independent review copy.
        config, plan, requirements, outputs, _ = self.inputs
        return evaluator.validate_reviews(config, plan, requirements, outputs, bundle)

    def test_all_planned_reviews_have_evidence_and_five_scores(self):
        config, plan, _, _, bundle = self.inputs
        rows = self.validate(bundle)
        self.assertEqual(len(rows), 90)
        self.assertEqual({c['name'] for c in config['criteria']}, {
            'Precondition Correctness', 'Trigger Correctness',
            'Expected Behavior Correctness', 'Condition / Boundary Coverage',
            'Unsupported Behavior / Hallucination',
        })
        self.assertEqual(len({(r['requirement_id'], r['strategy']) for r in rows}), 90)
        for row in rows:
            self.assertEqual(row['total_score'], sum(row[c['id']] for c in config['criteria']))

    def test_missing_and_duplicate_reviews_cannot_bias_denominators(self):
        bundle = copy.deepcopy(self.inputs[-1])
        bundle['records'].pop()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.validate(bundle)
        bundle = copy.deepcopy(self.inputs[-1])
        bundle['records'].append(copy.deepcopy(bundle['records'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.validate(bundle)

    def test_invalid_scores_and_missing_rationales_are_rejected(self):
        key = self.inputs[0]['criteria'][0]['id']
        # Unreviewed nulls must not become zeros; booleans must not become ones.
        for value in [None, True, -1, 3, '2']:
            with self.subTest(value=value):
                bundle = copy.deepcopy(self.inputs[-1])
                bundle['records'][0]['scores'][key] = value
                with self.assertRaisesRegex(ValueError, 'Invalid or unreviewed'):
                    self.validate(bundle)
        bundle = copy.deepcopy(self.inputs[-1])
        bundle['records'][0]['rationales'][key] = ' '
        with self.assertRaisesRegex(ValueError, 'Missing criterion rationale'):
            self.validate(bundle)

    def test_changed_evidence_and_version_are_rejected(self):
        bundle = copy.deepcopy(self.inputs[-1])
        bundle['records'][0]['generated']['then'] = 'Different output'
        with self.assertRaisesRegex(ValueError, 'Generated evidence mismatch'):
            self.validate(bundle)
        bundle = copy.deepcopy(self.inputs[-1])
        bundle['rubric_version'] = 'unrecognized'
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            self.validate(bundle)

    def test_source_file_change_is_detected_before_aggregation(self):
        # Work on temporary copies so the real source artifacts remain unchanged.
        config, plan, _, _, _ = self.inputs
        files = list(plan['source_sha256']) + [
            'evaluation/rubric.json', 'evaluation/rubric.md',
            'evaluation/review_plan.json', 'evaluation/reviews.json',
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in files:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.root / name, target)
            changed = root / 'results/zero_shot_results.csv'
            changed.write_bytes(changed.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Source fingerprint mismatch'):
                evaluator.load_inputs(root)

    def test_aggregation_preserves_direction_and_severity(self):
        config = self.inputs[0]
        keys = [c['id'] for c in config['criteria']]
        rows = [dict.fromkeys(keys, score) | dict(
            generation_status='success', total_score=5 * score,
            normalized_score=score / 2,
        ) for score in [0, 1, 2]]
        summary = evaluator.aggregate(rows, keys)
        self.assertEqual(summary['mean_total'], 5)
        self.assertEqual(summary['mean_normalized'], 0.5)
        self.assertEqual(summary['minor_unsupported_count'], 1)
        self.assertEqual(summary['material_unsupported_count'], 1)
        self.assertEqual(summary['full_score_count'], 1)
        self.assertEqual(summary['criterion_counts']['unsupported_behavior'], {'0': 1, '1': 1, '2': 1})


if __name__ == '__main__':
    unittest.main()
