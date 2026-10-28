"""Simulations of the shipped workbench engine; no model API calls."""
from __future__ import annotations

import argparse
import json
import math
import random
from statistics import mean
from pathlib import Path

from .dynamic import DynamicSession, choice_probability
from .research import default_blueprint
from .dynamic import compile_study


def simulate(strategy: str, population: str, seed: int, threshold: float = .45) -> dict:
    rng = random.Random(seed)
    study = compile_study(default_blueprint())
    truth = study.driver_ids[seed % 4]
    weights = {key: rng.uniform(.2, 1.2) for key in study.driver_ids}
    if population != 'mixed_no_dominant':
        weights[truth] += 1.5
    else:
        truth = max(weights, key=weights.get)
    temperature = rng.uniform(.65, 1.25)
    # Null cohort: highest rating agrees with the generating main factor.
    # For mixed_no_dominant this label is only a largest weight, not a true account.
    session = DynamicSession.create(study, truth, '', seed=seed)
    rounds = 6 if strategy == 'all_six' else 4
    # Four edges form a balanced cycle: every factor appears twice.
    fixed = ['e1', 'e4', 'e6', 'e3']

    def response(exp, flipped):
        if population == 'in_model':
            p = choice_probability(study, exp, truth)
        else:
            delta = sum(weights[k] * (exp.a['levels'][k] - exp.b['levels'][k]) for k in weights)
            p = 1 / (1 + math.exp(-delta / temperature))
        canonical = 'a' if rng.random() < p else 'b'
        if population != 'in_model' and rng.random() < .08:
            canonical = rng.choice(('a', 'b'))
        displayed = ('b' if canonical == 'a' else 'a') if flipped else canonical
        if population != 'in_model' and rng.random() < .06:
            displayed = 'a'
        return displayed

    for turn in range(rounds):
        if strategy == 'adaptive':
            public = session.next_experiment()
            exp = next(e for e in study.experiments if e.id == public['id'])
            flipped = public['flipped']
        else:
            available = [e for e in study.experiments if e.id not in session.used]
            exp = (rng.choice(available) if strategy == 'random' else
                   next(e for e in study.experiments if e.id == fixed[turn]) if strategy == 'fixed' else
                   study.experiments[turn])
            flipped = random.Random(f'{seed}:{exp.id}').random() < .5
        session.observe(exp.id, response(exp, flipped), flipped)
    holdout = session.holdout_experiment()
    repeated = next(e for e in study.experiments if e.id == holdout['id'])
    session.observe_holdout(response(repeated, holdout['flipped']), holdout['flipped'])
    report = session.report()
    passed = report['evidence_quality'] != 'low'
    mismatch = passed and report['leading_driver'] != truth and report['confidence'] >= threshold
    return {
        'correct': report['leading_driver'] == truth,
        'brier': mean((session.posterior[k] - (k == truth)) ** 2 for k in study.driver_ids),
        'passed': passed, 'flag': mismatch, 'probability': report['confidence'],
        'leader_differs': report['leading_driver'] != truth, 'questions': rounds + 1,
        'repeat_disagreed': report['holdout_consistent'] is False, 'true_factor': truth,
        'first_task': session.history[0]['experiment_id'],
    }


def summarize(rows: list[dict], threshold: float) -> dict:
    passing = [r for r in rows if r['passed']]
    flags = sum(r['passed'] and r['leader_differs'] and r['probability'] >= threshold for r in rows)
    return {
        'sessions': len(rows), 'total_questions_including_repeat': rows[0]['questions'],
        'top1_recovery': round(mean(r['correct'] for r in rows), 4),
        'mean_brier': round(mean(r['brier'] for r in rows), 4),
        'response_check_inconclusive_rate': round(1 - len(passing) / len(rows), 4),
        'repeat_disagreement_rate': round(mean(r.get('repeat_disagreed', False) for r in rows), 4),
        'repeat_disagreement_by_factor': {
            key: round(mean(r['repeat_disagreed'] for r in rows if r.get('true_factor') == key), 4)
            for key in sorted({r['true_factor'] for r in rows if 'true_factor' in r})
        },
        'first_task_counts': {key: sum(r.get('first_task') == key for r in rows) for key in sorted({r['first_task'] for r in rows if 'first_task' in r})},
        'weak_separation_among_passing': round(mean(r['probability'] < threshold for r in passing), 4) if passing else None,
        'null_mismatch_rate_all': round(flags / len(rows), 4),
        'null_mismatch_rate_passing': round(flags / len(passing), 4) if passing else None,
    }


def run_benchmark(participants: int = 2000, seed: int = 2026) -> dict:
    if participants < 1:
        raise ValueError('participants must be positive')
    result = {
        'engine': 'dynamic.DynamicSession with grocery workbench blueprint',
        'participants_per_condition': participants, 'seed': seed,
        'threshold': .45, 'threshold_policy': 'Uncalibrated descriptive heuristic; not tuned on evaluation data.',
        'design': 'Seeded random EIG tie-breaking. One uniformly sampled completed informative task is repeated with reversed sides; repeat agreement never filters sessions. Same participant seeds across policies; all-six uses two extra tasks.',
        'limitations': [
            'Synthetic diagnostics only; no human or Muse accuracy claim.',
            'All cohorts are null cohorts: stated highest rating matches the generating largest weight.',
            'A null mismatch is model/measurement disagreement, not a verified behavioural false positive.',
            'Mixed participants need not be represented by any single-factor model; top1 is largest-weight recovery only.',
            'No outside choices simulated. Repeat consistency is not a validation of the inferred account.',
        ],
        'populations': {},
    }
    for population in ('in_model', 'mixed_dominant', 'mixed_no_dominant'):
        result['populations'][population] = {}
        for strategy in ('adaptive', 'fixed', 'random', 'all_six'):
            rows = [simulate(strategy, population, seed + i) for i in range(participants)]
            summary = summarize(rows, .45)
            summary['threshold_sensitivity'] = {str(t): summarize(rows, t)['null_mismatch_rate_passing'] for t in (.45, .6, .75, .9)}
            result['populations'][population][strategy] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participants', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--output', default='outputs/workbench-benchmark.json')
    args = parser.parse_args()
    result = run_benchmark(args.participants, args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
