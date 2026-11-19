#!/usr/bin/env python3
"""Local browser demo using the existing generator and Python's HTTP server.

Run from the repository root: python demo/app.py
Saved mode replays recorded outputs; live mode requires OPENAI_API_KEY.
No demo request writes to the experiment or evaluation files.
"""
import argparse
import csv
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src import generator

ASSETS = Path(__file__).resolve().parent
STRATEGIES = tuple(generator.PROMPT_TEMPLATES)
MAX_BODY = 16384
MAX_REQUIREMENT = 5000


class DemoUnavailableError(RuntimeError):
    """Only deliberate, credential-free messages may be shown as service errors."""


class DemoService:
    """Share dataset lookup and request validation between the UI and tests."""
    def __init__(self, root=ROOT, client_factory=None):
        self.root = root
        self.client_factory = client_factory or generator.OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.requirements = generator.load_requirements(root / 'data/requirements.csv')
        self.by_id = {r['requirement_id']: r for r in self.requirements}
        self.saved = {}
        for strategy in STRATEGIES:
            with (root / f'results/{strategy}_results.csv').open(encoding='utf-8-sig', newline='') as stream:
                self.saved[strategy] = {r['requirement_id']: r for r in csv.DictReader(stream)}
        # Permit one paid live call at a time in this local demonstration.
        self.live_lock = threading.Lock()

    def catalog(self):
        # Reference answers and credentials never appear in browser responses.
        return dict(requirements=[{k: r[k] for k in ['requirement_id', 'requirement', 'category', 'difficulty']}
                                  for r in self.requirements],
                    strategies=list(STRATEGIES), default_model=generator.DEFAULT_MODEL,
                    live_available=bool(self.api_key))

    def generate(self, payload):
        if not isinstance(payload, dict):
            raise ValueError('Request must be a JSON object.')
        mode, strategy = payload.get('mode'), payload.get('strategy')
        if mode not in ('saved', 'live') or strategy not in STRATEGIES:
            raise ValueError('Select a supported mode and prompting strategy.')
        requirement = payload.get('requirement')
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError('Enter a requirement before generating a test.')
        requirement = requirement.strip()
        if len(requirement) > MAX_REQUIREMENT:
            raise ValueError(f'Requirement must not exceed {MAX_REQUIREMENT} characters.')
        rid = payload.get('requirement_id')
        if rid is not None and (not isinstance(rid, str) or rid not in self.by_id):
            raise ValueError('Select a valid sample or use a custom requirement.')
        if mode == 'saved':
            row = self.saved[strategy].get(rid)
            # Never misrepresent a recorded test as a new answer to edited input.
            if not row or row['requirement'].strip() != requirement:
                raise ValueError('Saved mode requires an unchanged dataset sample. Use Live API for custom text.')
            if row['status'] != 'success':
                raise ValueError('No successful saved output is available for this sample.')
            case = {k: row[f'generated_{k}'] for k in ['given', 'when', 'then']}
            model = row['model']
        else:
            if not self.api_key:
                raise DemoUnavailableError('Set OPENAI_API_KEY in the server environment and restart to enable live generation.')
            model = payload.get('model', generator.DEFAULT_MODEL)
            if not isinstance(model, str) or not model.strip() or len(model) > 100:
                raise ValueError('Enter a model identifier of 1 to 100 characters.')
            model = model.strip()
            # Check all dataset rows plus the custom target against the fixed examples.
            examples = generator.load_few_shot_examples(
                evaluated_requirements=[r['requirement'] for r in self.requirements] + [requirement]
            ) if strategy == 'few_shot' else None
            if not self.live_lock.acquire(blocking=False):
                raise BlockingIOError('A live request is already running. Wait for it to finish.')
            try:
                client = self.client_factory(api_key=self.api_key, timeout=60.0, max_retries=0)
                case = generator.generate_test_case(client, model, requirement, strategy, examples=examples)
            finally:
                self.live_lock.release()
        if any(not isinstance(case.get(k), str) or not case[k].strip() for k in ['given', 'when', 'then']):
            raise DemoUnavailableError('The output did not contain a complete Given-When-Then test. Try again.')
        # If live input was edited, do not retain an incorrect dataset identity.
        actual_id = rid if rid and self.by_id[rid]['requirement'].strip() == requirement else None
        return dict(mode=mode, strategy=strategy, model=model, requirement_id=actual_id,
                    requirement=requirement, test_case=case,
                    source='Saved experiment output' if mode == 'saved' else 'New API generation')


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        def trusted_request(self):
            # Keep the credential-backed service local and reject foreign browser origins.
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed:
                return False
            origin = self.headers.get('Origin')
            return not origin or origin in {f'http://{host}' for host in allowed}

        def send_body(self, status, body, content_type):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, value):
            self.send_body(status, json.dumps(value).encode(), 'application/json; charset=utf-8')

        def do_GET(self):
            if not self.trusted_request():
                self.send_json(403, {'error': 'Only local demo requests are accepted.'})
                return
            route = urlsplit(self.path).path
            if route == '/api/catalog':
                self.send_json(200, service.catalog())
                return
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if route not in assets:
                self.send_json(404, {'error': 'Not found.'})
                return
            name, mime = assets[route]
            self.send_body(200, (ASSETS / name).read_bytes(), mime + '; charset=utf-8')

        def do_POST(self):
            if not self.trusted_request():
                self.send_json(403, {'error': 'Only local demo requests are accepted.'})
                return
            if urlsplit(self.path).path != '/api/generate':
                self.send_json(404, {'error': 'Not found.'})
                return
            if self.headers.get_content_type() != 'application/json':
                self.send_json(415, {'error': 'Send application/json.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > MAX_BODY:
                    self.send_json(413, {'error': 'Request body is empty or too large.'})
                    return
                payload = json.loads(self.rfile.read(length))
                result = service.generate(payload)
            except (ValueError, UnicodeError):
                # Input-validation messages never include API credentials or raw responses.
                self.send_json(400, {'error': 'Check the input, sample, mode, and strategy. Saved mode needs an unchanged sample; Few-Shot cannot reuse a demonstration requirement.'})
            except BlockingIOError:
                self.send_json(429, {'error': 'A live request is already running. Try again when it finishes.'})
            except DemoUnavailableError as error:
                self.send_json(503, {'error': str(error)})
            except Exception:
                # SDK errors can contain request details: expose only a safe user-facing message.
                self.send_json(502, {'error': 'Live generation failed. Check server credentials, model access, and network availability, then try again.'})
            else:
                self.send_json(200, result)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('--port must be between 0 and 65535')
    service = DemoService()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(service))
    server.daemon_threads = True
    print(f'Demo available at http://127.0.0.1:{server.server_port}', flush=True)
    print('Saved mode ready. Live API mode ' + ('enabled.' if service.api_key else 'requires OPENAI_API_KEY.'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
