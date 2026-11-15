"""Check paired joins and sensitivity arithmetic without requiring plotting packages."""
import copy
import unittest

from src import analyze_results


class AnalysisTests(unittest.TestCase):
    def test_pairing_joins_ids_instead_of_row_positions(self):
        rows = [
            {'requirement_id': 'B', 'strategy': 'a', 'total_score': 7},
            {'requirement_id': 'A', 'strategy': 'a', 'total_score': 10},
            {'requirement_id': 'A', 'strategy': 'b', 'total_score': 8},
            {'requirement_id': 'B', 'strategy': 'b', 'total_score': 9},
        ]
        result = analyze_results.paired_comparison(rows, 'a', 'b')
        self.assertEqual(result['deltas'], {'A': 2, 'B': -2})
        self.assertEqual((result['higher'], result['equal'], result['lower']), (1, 0, 1))
        self.assertEqual(result['mean_delta'], 0)

    def test_incomplete_pairs_cannot_silently_drop_cases(self):
        with self.assertRaisesRegex(ValueError, 'same nonempty'):
            analyze_results.paired_comparison([
                {'requirement_id': 'A', 'strategy': 'a', 'total_score': 10},
                {'requirement_id': 'B', 'strategy': 'b', 'total_score': 10},
            ], 'a', 'b')

    def test_losses_and_leave_one_out_preserve_original_scores(self):
        # Two artificial cases isolate both the denominator and the exclusion ID.
        keys = ['precondition_correctness', 'trigger_correctness',
                'expected_behavior_correctness', 'condition_boundary_coverage', 'unsupported_behavior']
        strategies = ['zero_shot', 'structured', 'few_shot']
        rows = []
        for s in strategies:
            for rid in ['A', 'B']:
                score = 0 if s == 'zero_shot' and rid == 'A' else 2
                rows.append(dict(requirement_id=rid, strategy=s, difficulty='Easy',
                                 total_score=score * 5, **dict.fromkeys(keys, score)))
        original = copy.deepcopy(rows)
        result = analyze_results.analyze(rows, {'strategies': {}},
                                         {'version': '1.0', 'criteria': [{'id': k} for k in keys], 'strategies': strategies})
        self.assertEqual(rows, original)
        self.assertEqual(len(result['cases_below_maximum']), 1)
        self.assertEqual(result['cases_below_maximum'][0]['points_below_maximum'], 10)
        means = {r['excluded_requirement_id']: r for r in result['leave_one_requirement_out']}
        self.assertEqual(means['A']['zero_shot'], 10)
        self.assertEqual(means['B']['zero_shot'], 0)
        self.assertEqual(means['A']['structured'], 10)


if __name__ == '__main__':
    unittest.main()
