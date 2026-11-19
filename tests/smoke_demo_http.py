"""Check a running local demo over HTTP without API calls or credentials.

Start demo/app.py first, then run: python tests/smoke_demo_http.py
"""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    base = f'http://127.0.0.1:{args.port}'
    for asset in ['/', '/style.css', '/app.js']:
        with urlopen(base + asset, timeout=10) as response:
            assert response.status == 200 and response.read()
    with urlopen(base + '/api/catalog', timeout=10) as response:
        catalog = json.load(response)
    assert len(catalog['requirements']) == 30
    assert 'api_key' not in catalog
    sample = next(r for r in catalog['requirements'] if r['requirement_id'] == 'REQ-002')
    for strategy in catalog['strategies']:
        request = Request(base + '/api/generate', data=json.dumps(dict(
            mode='saved', strategy=strategy, requirement_id=sample['requirement_id'],
            requirement=sample['requirement'])).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        assert result['mode'] == 'saved' and result['strategy'] == strategy
        assert all(result['test_case'][key] for key in ['given', 'when', 'then'])
    # Check that a non-asset path cannot expose repository files through the web server.
    try:
        urlopen(base + '/README.md', timeout=10)
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError('Unexpected access to a repository document')
    print('HTTP smoke checks passed: three assets, 30 samples, three saved strategies and restricted routes.')


if __name__ == '__main__':
    main()
