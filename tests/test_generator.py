"""Offline checks for strategy selection, prompt isolation, and CSV metadata."""
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src import generator


class GeneratorTests(unittest.TestCase):
    def test_strategy_defaults_preserve_baseline_path(self):
        # Each strategy should choose its own output file when --output is omitted.
        for strategy, expected in (
            ('zero_shot', generator.DEFAULT_OUTPUT),
            ('structured', Path('results/structured_results.csv')),
            ('few_shot', Path('results/few_shot_results.csv')),
        ):
            # Simulate CLI arguments without launching a separate Python process.
            with self.subTest(strategy=strategy), patch('sys.argv', ['generator', '--strategy', strategy]):
                args = generator.parse_args()
                self.assertEqual(args.output, expected)

    def test_explicit_output_and_model_override(self):
        # User-supplied output and model values must take precedence over defaults.
        with patch('sys.argv', ['generator', '--strategy', 'structured', '--output', 'sample.csv', '--model', 'test-model']):
            args = generator.parse_args()
        self.assertEqual(args.output, Path('sample.csv'))
        self.assertEqual(args.model, 'test-model')

    def test_zero_shot_request_is_unchanged(self):
        # Return a small fake API response so this test runs without network access.
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(dict(given='Setup', when='Event', then='Result')))
        # Omitting strategy should still send exactly the original Zero-Shot request.
        generator.generate_test_case(client, 'test-model', 'Requirement')
        client.responses.create.assert_called_once_with(
            model='test-model', instructions=generator.SYSTEM_PROMPT,
            input=generator.ZERO_SHOT_PROMPT.format(requirement='Requirement'),
        )

    def test_structured_batch_sends_only_requirement_and_labels_results(self):
        # Reuse the batch checks to guard the existing Structured workflow.
        self._check_batch('structured')

    def test_few_shot_batch_excludes_references_and_labels_results(self):
        # Exercise Few-Shot through main(), including prompt construction and CSV saving.
        self._check_batch('few_shot')

    def _check_batch(self, strategy):
        # Shared helper keeps the same input and fake API response across both strategies.
        # Keep test CSV files separate from experiment data and clean them up afterward.
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / 'input.csv'
            output_path = Path(directory) / 'output.csv'
            with input_path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['requirement_id', 'requirement', 'reference_given', 'reference_when', 'reference_then'])
                writer.writeheader()
                # Distinctive reference markers let us detect accidental answer leakage.
                for i in range(3):
                    writer.writerow(dict(requirement_id=f'R{i}', requirement=f'Requirement {i}', reference_given='SECRET_REFERENCE_GIVEN', reference_when='SECRET_REFERENCE_WHEN', reference_then='SECRET_REFERENCE_THEN'))
            # Replace the client used by main(); no real API calls or credentials are needed.
            client = Mock()
            client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(dict(given='Setup', when='Event', then='Result')))
            # The dummy key satisfies the environment check; stdout capture hides progress logs.
            with patch('sys.argv', ['generator', '--input', str(input_path), '--output', str(output_path), '--strategy', strategy]), patch.dict('os.environ', {'OPENAI_API_KEY': 'offline-test'}), patch.object(generator, 'OpenAI', return_value=client), redirect_stdout(io.StringIO()):
                generator.main()
            # Inspect the actual CSV written by the batch workflow, not just the mock.
            with output_path.open(newline='') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r['status'] == 'success' and r['prompt_strategy'] == strategy for r in rows))
            self.assertEqual(client.responses.create.call_count, 3)
            # Verify prompt isolation and shared model/system settings for every request.
            for i, call in enumerate(client.responses.create.call_args_list):
                if strategy == 'structured':
                    self.assertEqual(call.kwargs['input'], generator.STRUCTURED_PROMPT.format(requirement=f'Requirement {i}'))
                else:
                    # Every request gets the same independent examples and baseline target format.
                    self.assertTrue(call.kwargs['input'].endswith(generator.ZERO_SHOT_PROMPT.format(requirement=f'Requirement {i}')))
                    for example in generator.load_few_shot_examples():
                        self.assertIn(example['requirement'], call.kwargs['input'])
                        self.assertIn(example['then'], call.kwargs['input'])
                self.assertNotIn('SECRET_REFERENCE', str(call))
                self.assertEqual(call.kwargs['instructions'], generator.SYSTEM_PROMPT)
                self.assertEqual(call.kwargs['model'], generator.DEFAULT_MODEL)

    def test_examples_are_separate_from_the_full_evaluation_dataset(self):
        # Validate all 30 rows, not just the small sample used for initial API checks.
        requirements = generator.load_requirements(generator.DEFAULT_INPUT)
        examples = generator.load_few_shot_examples(evaluated_requirements=[r['requirement'] for r in requirements])
        self.assertEqual(len(examples), 4)

    def test_target_overlap_is_rejected_before_an_api_call(self):
        # Explicitly supplied examples must not bypass the direct-call leakage check.
        client = Mock()
        example = generator.load_few_shot_examples()[0]
        # Case and whitespace differences must not hide an identical target answer.
        target = '  ' + example['requirement'].upper().replace(' ', '  ')
        with self.assertRaisesRegex(ValueError, 'overlap'):
            generator.generate_test_case(client, 'test-model', target, 'few_shot', examples=[example])
        client.responses.create.assert_not_called()  # Rejection must happen before a network request.

    def test_example_loader_rejects_overlap_duplicates_and_missing_fields(self):
        # Invalid demonstration data must fail before starting a paid experiment.
        example = generator.load_few_shot_examples()[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'examples.json'
            # First reject an example that also appears among the evaluation requirements.
            path.write_text(json.dumps([example]))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                generator.load_few_shot_examples(path, [example['requirement'].upper()])
            # Then reject repeated demonstrations even without evaluation overlap.
            path.write_text(json.dumps([example, example]))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                generator.load_few_shot_examples(path)
            # Finally reject an example with no Given/When/Then answer fields.
            path.write_text(json.dumps([{'requirement': 'A requirement'}]))
            with self.assertRaisesRegex(ValueError, 'nonempty text'):
                generator.load_few_shot_examples(path)

    def test_sample_limit_cannot_hide_evaluation_overlap(self):
        # An overlapping row outside --limit must still block the experiment.
        example = generator.load_few_shot_examples()[0]
        rows = [
            {'requirement_id': 'SAFE', 'requirement': 'An independent target.'},
            {'requirement_id': 'OVERLAP', 'requirement': example['requirement']},
        ]
        # --limit 1 selects only SAFE, but validation must also inspect OVERLAP.
        client = Mock()
        with patch('sys.argv', ['generator', '--strategy', 'few_shot', '--limit', '1']), patch.dict('os.environ', {'OPENAI_API_KEY': 'offline-test'}), patch.object(generator, 'OpenAI', return_value=client), patch.object(generator, 'load_requirements', return_value=rows):
            with self.assertRaisesRegex(ValueError, 'overlap'):
                generator.main()
        client.responses.create.assert_not_called()

    def test_bad_sample_limits_are_rejected(self):
        # argparse should stop invalid runs before any generation; suppress expected errors.
        for limit in ['0', '-1']:
            with patch('sys.argv', ['generator', '--limit', limit]), self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), patch('sys.stderr', new_callable=io.StringIO):
                generator.parse_args()


if __name__ == '__main__':
    # Support running this module directly as well as unittest discovery.
    unittest.main()
