"""Objective scripted checks of the shipped interview state machine, not human validation."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from . import explore
from .dynamic import DynamicSession, compile_study
from .meta import MetaClient
from .research import default_blueprint


def run(participants=200):
    if participants < 1:
        raise ValueError('Use at least one scripted session')
    study = compile_study(default_blueprint())
    metrics = dict(single_fact_audits=0, switch_labels_correct=0, corrections_preserved=0, unresolved_interpretations_not_adopted=0, skip_branches_correct=0)
    for seed in range(participants):
        session = DynamicSession.create(study, 'a', 'Scripted survey statement.', seed=seed)
        trace = []
        for _ in range(4):
            exp = session.next_experiment()
            session.observe(exp['id'], 'a', exp['flipped'])
            trace.append({'holdout': False, 'stimulus': exp, 'displayed_choice': 'a'})
        state = explore.begin(session, {**session.report(), 'decision_trace': trace})
        meta = MetaClient()
        def answer(**fields):
            explore.advance(state, {'answer_token': state['pending']['answer_token'], **fields}, meta)
        answer(text='Scripted reason about timing.')
        answer(text='A different window.')
        corrected = seed % 2 == 0
        answer(status='corrected' if corrected else 'unresolved', text='Access is the constraint.' if corrected else '', factor='unresolved')
        expected = []
        while state['phase'].startswith('condition'):
            c = state['contrasts'][int(state['phase'][-1])]
            differences = 0
            for side in ('a', 'b'):
                base = ('b' if side == 'a' else 'a') if c['reversed'] else side
                differences += sum(x != y for x, y in zip(c['baseline_stimulus'][base]['facts'], c['stimulus'][side]['facts']))
            metrics['single_fact_audits'] += int(differences == 1)
            switch = (seed + len(expected)) % 2 == 0
            identity = ('b' if c['baseline_choice'] == 'a' else 'a') if switch else c['baseline_choice']
            displayed = ('b' if identity == 'a' else 'a') if c['reversed'] else identity
            expected.append(switch)
            answer(choice=displayed)
        answer(text='Scripted reflection.')
        report = explore.synthesis(state)
        metrics['switch_labels_correct'] += sum(c['response']['switched'] == truth for c, truth in zip(report['condition_tests'], expected))
        metrics['corrections_preserved'] += int(corrected and report['participant_explanation']['effective'] == 'Access is the constraint.')
        metrics['unresolved_interpretations_not_adopted'] += int(not corrected and report['participant_explanation']['effective'] == 'Interpretation unresolved.')
        skipped = explore.begin(session, {**session.report(), 'decision_trace': [{**t, 'displayed_choice': 'outside'} for t in trace]})
        for fields in ({'text': ''}, {'text': ''}, {'status': 'unresolved'}, {'text': ''}):
            explore.advance(skipped, {'answer_token': skipped['pending']['answer_token'], **fields}, meta)
        metrics['skip_branches_correct'] += int(skipped['phase'] == 'complete' and not skipped['contrasts'])
    return {'scope': 'Scripted synthetic sessions verify state transitions, exact stimulus changes, identity normalization and correction handling. No human participants or model semantic accuracy are evaluated.',
            'sessions': participants, 'condition_tasks': participants * 2, 'checks_passed': metrics,
            'all_checks_passed': metrics == {'single_fact_audits': participants * 2, 'switch_labels_correct': participants * 2, 'corrections_preserved': (participants + 1) // 2, 'unresolved_interpretations_not_adopted': participants // 2, 'skip_branches_correct': participants}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--participants', type=int, default=200); parser.add_argument('--output', default='outputs/adaptive-interview-benchmark.json')
    args = parser.parse_args()
    with patch.dict('os.environ', {'MODEL_API_KEY': ''}): result = run(args.participants)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
