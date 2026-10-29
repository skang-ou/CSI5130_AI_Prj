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
            with patch('sys.argv', ['generator', '--input', str(input_path), '--output', str(output_path), '--strategy', 'structured']), patch.dict('os.environ', {'OPENAI_API_KEY': 'offline-test'}), patch.object(generator, 'OpenAI', return_value=client), redirect_stdout(io.StringIO()):
                generator.main()
            # Inspect the actual CSV written by the batch workflow, not just the mock.
            with output_path.open(newline='') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r['status'] == 'success' and r['prompt_strategy'] == 'structured' for r in rows))
            # Verify prompt isolation and shared model/system settings for every request.
            for i, call in enumerate(client.responses.create.call_args_list):
                self.assertEqual(call.kwargs['input'], generator.STRUCTURED_PROMPT.format(requirement=f'Requirement {i}'))
                self.assertNotIn('SECRET_REFERENCE', str(call))
                self.assertEqual(call.kwargs['instructions'], generator.SYSTEM_PROMPT)
                self.assertEqual(call.kwargs['model'], generator.DEFAULT_MODEL)

    def test_bad_sample_limits_are_rejected(self):
        # argparse should stop invalid runs before any generation; suppress expected errors.
        for limit in ['0', '-1']:
            with patch('sys.argv', ['generator', '--limit', limit]), self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), patch('sys.stderr', new_callable=io.StringIO):
                generator.parse_args()


if __name__ == '__main__':
    # Support running this module directly as well as unittest discovery.
    unittest.main()
