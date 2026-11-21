#!/usr/bin/env python3
"""Rehearse the final saved-output walkthrough without a server or API call."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from demo.app import DemoService


def rehearse():
    # Reject any accidental attempt to construct a live API client during rehearsal.
    def no_live_calls(**kwargs):
        raise AssertionError('Saved rehearsal must not make an API call.')
    service = DemoService(client_factory=no_live_calls)
    cases = []
    for requirement_id in ['REQ-002', 'REQ-018', 'REQ-023']:
        requirement = service.by_id[requirement_id]['requirement']
        for strategy in ['zero_shot', 'structured', 'few_shot']:
            result = service.generate(dict(mode='saved', strategy=strategy,
                                           requirement_id=requirement_id, requirement=requirement))
            if not all(result['test_case'].values()):
                raise ValueError('Incomplete saved demonstration case.')
            cases.append(result)
    return dict(mode='saved_only_rehearsal', case_count=len(cases), api_calls=0,
                presentation_delivered=False, recording_created=False, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional separate JSON rehearsal record.')
    args = parser.parse_args()
    result = rehearse()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Saved-only rehearsal passed for {result['case_count']} cases; no API calls.")
    for case in result['cases']:
        print(f"\n{case['requirement_id']} / {case['strategy']} / {case['source']}")
        for key, value in case['test_case'].items():
            print(f'{key.title()}: {value}')


if __name__ == '__main__':
    main()
