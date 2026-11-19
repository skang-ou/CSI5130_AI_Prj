"""Test saved replay, shared live generation and local HTTP behavior without API calls."""
import io
import json
import unittest
from email.message import Message
from types import SimpleNamespace
from unittest.mock import Mock, patch

from demo.app import DemoService, DemoUnavailableError, handler_for


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.factory = Mock()
        self.client = Mock()
        self.factory.return_value = self.client
        self.client.responses.create.return_value = SimpleNamespace(
            output_text=json.dumps(dict(given='Setup', when='Input', then='Response')))
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'dummy-test-key'}):
            self.service = DemoService(client_factory=self.factory)

    def payload(self, mode='saved', strategy='zero_shot'):
        row = self.service.by_id['REQ-002']
        return dict(mode=mode, strategy=strategy, requirement_id='REQ-002', requirement=row['requirement'])

    def test_all_90_saved_cases_match_original_outputs_without_api_calls(self):
        for strategy, cases in self.service.saved.items():
            for rid, row in cases.items():
                with self.subTest(strategy=strategy, rid=rid):
                    result = self.service.generate(dict(mode='saved', strategy=strategy,
                                                       requirement_id=rid, requirement=row['requirement']))
                    self.assertEqual(result['source'], 'Saved experiment output')
                    self.assertEqual(result['model'], row['model'])
                    for key in ['given', 'when', 'then']:
                        self.assertEqual(result['test_case'][key], row['generated_' + key])
        self.factory.assert_not_called()

    def test_catalog_omits_credentials_and_reference_answers(self):
        catalog = self.service.catalog()
        encoded = json.dumps(catalog)
        self.assertEqual(len(catalog['requirements']), 30)
        self.assertNotIn('dummy-test-key', encoded)
        self.assertNotIn('reference_given', encoded)
        self.assertNotIn('reference_then', encoded)

    def test_saved_mode_rejects_edited_text_and_invalid_payloads(self):
        payload = self.payload()
        payload['requirement'] += ' A changed condition.'
        with self.assertRaisesRegex(ValueError, 'unchanged'):
            self.service.generate(payload)
        for change in [dict(strategy='unknown'), dict(requirement=''), dict(requirement_id=[]),
                       dict(requirement='X' * 5001), dict(mode='unknown')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.service.generate(self.payload() | change)
        self.factory.assert_not_called()

    def test_live_mode_reuses_each_strategy_and_excludes_references(self):
        for strategy in self.service.saved:
            result = self.service.generate(self.payload('live', strategy))
            self.assertEqual(result['source'], 'New API generation')
            self.assertEqual(result['strategy'], strategy)
            request = self.client.responses.create.call_args.kwargs
            self.assertNotIn('reference_given', request['input'])
            self.assertNotIn('dummy-test-key', request['input'])
        self.assertEqual(self.client.responses.create.call_count, 3)

    def test_custom_live_input_does_not_keep_the_old_sample_identity(self):
        payload = self.payload('live')
        payload['requirement'] = 'When a switch is asserted, the controller shall illuminate an indicator.'
        result = self.service.generate(payload)
        self.assertIsNone(result['requirement_id'])
        self.assertEqual(result['requirement'], payload['requirement'])

    def test_live_key_overlap_and_busy_checks_prevent_api_calls(self):
        self.service.api_key = ''
        with self.assertRaises(DemoUnavailableError):
            self.service.generate(self.payload('live'))
        self.service.api_key = 'dummy-test-key'
        payload = self.payload('live', 'few_shot')
        from src import generator
        payload['requirement'] = generator.load_few_shot_examples()[0]['requirement']
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.service.generate(payload)
        self.service.live_lock.acquire()
        try:
            with self.assertRaises(BlockingIOError):
                self.service.generate(self.payload('live'))
        finally:
            self.service.live_lock.release()
        self.factory.assert_not_called()

    def test_live_lock_is_released_after_an_sdk_error(self):
        self.client.responses.create.side_effect = Exception('API failure')
        with self.assertRaises(Exception):
            self.service.generate(self.payload('live'))
        self.assertFalse(self.service.live_lock.locked())

    def handler(self, path, payload=None, origin=None, host='127.0.0.1:8765'):
        # Construct a handler without a network socket; real HTTP smoke checks run separately.
        handler = object.__new__(handler_for(self.service))
        handler.server = SimpleNamespace(server_port=8765)
        handler.path = path
        handler.headers = Message()
        handler.headers['Host'] = host
        if origin: handler.headers['Origin'] = origin
        if payload is not None:
            raw = json.dumps(payload).encode()
            handler.headers['Content-Type'] = 'application/json'
            handler.headers['Content-Length'] = str(len(raw))
            handler.rfile = io.BytesIO(raw)
        handler.send_json = Mock()
        handler.send_body = Mock()
        return handler

    def test_http_routes_reject_foreign_origins_and_private_files(self):
        foreign = self.handler('/api/generate', self.payload('live'), origin='https://unrelated.example')
        foreign.do_POST()
        self.assertEqual(foreign.send_json.call_args.args[0], 403)
        for path in ['/.OpenaiApikey', '/../README.md', '/src/generator.py']:
            handler = self.handler(path)
            handler.do_GET()
            self.assertEqual(handler.send_json.call_args.args[0], 404)
        host = self.handler('/api/catalog', host='unrelated.example')
        host.do_GET()
        self.assertEqual(host.send_json.call_args.args[0], 403)
        self.factory.assert_not_called()

    def test_http_hides_sdk_error_details_and_limits_request_size(self):
        self.client.responses.create.side_effect = RuntimeError('dummy-test-key must never reach the browser')
        handler = self.handler('/api/generate', self.payload('live'))
        handler.do_POST()
        status, body = handler.send_json.call_args.args
        self.assertEqual(status, 502)
        self.assertNotIn('dummy-test-key', json.dumps(body))
        large = self.handler('/api/generate', self.payload())
        large.headers.replace_header('Content-Length', '20000')
        large.do_POST()
        self.assertEqual(large.send_json.call_args.args[0], 413)


if __name__ == '__main__':
    unittest.main()
