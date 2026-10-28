"""Known-probability simulations of mechanism contrasts; not model or human validation."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from .mechanisms import approve_study, manual_plan, report
from .research import draft_workspace, EXAMPLE_EVIDENCE


class Offline:
    enabled = False
    usage = []


def run_benchmark(per_arm=1000, seed=281026):
    if per_arm < 1:
        raise ValueError('Use a positive simulated sample size')
    workspace = draft_workspace('Which delivery mechanism should we investigate?', EXAMPLE_EVIDENCE, Offline())
    workspace['evidence_origin'] = 'fictional-example'
    scenarios = [
        ('default_effect', 'default', {'focal_default': .8, 'standard_default': .2, 'active': .5}),
        ('advance_information', 'planning', {'advance': .75, 'later': .4}),
        ('benefit_specific_credibility', 'credibility', {'benefit_verified': .85, 'benefit_retailer': .5, 'equal_verified': .4, 'equal_retailer': .35}),
        ('general_endorsement_rival', 'credibility', {'benefit_verified': .8, 'benefit_retailer': .6, 'equal_verified': .6, 'equal_retailer': .4}),
        ('no_default_effect', 'default', {'focal_default': .5, 'standard_default': .5, 'active': .5}),
        ('no_information_effect', 'planning', {'advance': .5, 'later': .5}),
        ('no_credibility_interaction', 'credibility', {key: .5 for key in ('benefit_verified', 'benefit_retailer', 'equal_verified', 'equal_retailer')}),
    ]
    output = {'seed': seed, 'simulated_per_arm': per_arm, 'scenarios': {},
              'scope': 'Tests fixed randomized-design contrast calculations against supplied arm probabilities. It does not recover hidden mechanisms, evaluate Muse, or validate a psychological mediator or human behaviour.'}
    for index, (name, mechanism, probabilities) in enumerate(scenarios):
        study = approve_study(workspace, manual_plan(workspace), mechanism, True)
        rng = random.Random(seed + index)
        rows = [{'study_id': study['id'], 'arm_id': arm, 'status': 'completed', 'choice': 'a' if rng.random() < p else 'b'}
                for arm, p in probabilities.items() for _ in range(per_arm)]
        result = report(study, rows)
        truth = sum(probabilities[key] * weight for key, weight in study['protocol']['contrast']['weights'].items())
        c = result['contrast']
        output['scenarios'][name] = {'known_arm_probabilities': probabilities, 'known_contrast': truth,
                                    'estimated_contrast': c['estimate'], 'lower': c['lower'], 'upper': c['upper'],
                                    'contains_generating_contrast': c['lower'] <= truth <= c['upper'], 'status': c['status'],
                                    'completed_sessions': len(rows), 'audit_passed': study['protocol']['audit']['passed']}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-arm', type=int, default=1000)
    parser.add_argument('--output', type=Path, default=Path('outputs/mechanism-benchmark.json'))
    args = parser.parse_args()
    result = run_benchmark(args.per_arm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
