"""Reproducible fictional scenario for observing Muse plan, act and reconsider."""
import argparse
import json
from pathlib import Path

from . import explore
from .config import load_env_file
from .dynamic import DynamicSession, compile_study
from .meta import MetaClient
from .research import default_blueprint


def fixture(chooser=None):
    study = compile_study(default_blueprint())
    # Select a declared seed with price-versus-verification first; no model output is screened.
    seed = next(seed for seed in range(1000) if DynamicSession.create(study, 'd', '', seed=seed).next_experiment()['id'] == 'e5')
    session = DynamicSession.create(study, 'd', 'Fictional respondent: I value verified environmental claims.', seed=seed,
                                    stated_ratings={'a': 4, 'b': 4, 'c': 3, 'd': 5})
    trace = []
    for _ in range(4):
        exp = session.next_experiment()
        choice = (chooser or choose)(exp)
        before = dict(session.posterior)
        session.observe(exp['id'], choice, exp['flipped'])
        trace.append({'holdout': False, 'stimulus': exp, 'displayed_choice': choice,
                      'posterior_before': before, 'posterior_after': dict(session.posterior)})
    return explore.begin(session, {**session.report(), 'decision_trace': trace})


def choose(exp):
    return max(('a', 'b'), key=lambda side: 3 * exp[side]['levels']['b'] + exp[side]['levels']['d'] + .8 * exp[side]['levels']['a'])


def run(meta):
    state = fixture()
    def answer(**fields):
        explore.advance(state, {'answer_token': state['pending']['answer_token'], **fields}, meta)
    answer(text='Fictional respondent: Independent verification matters because I hesitate over unsupported green claims.')
    answer(text='Fictional respondent: I would consider the verified option if the delivery fee were the same.')
    answer(status='corrected', factor='unresolved', text='Fictional correction: The extra fee rules it out for my budget. I am not rejecting verification itself.')
    while state['phase'].startswith('condition'):
        c = state['contrasts'][int(state['phase'][-1])]
        answer(choice=choose(c['stimulus']))
    answer(text='Fictional reflection: When both options were free I chose verification. The extra fee was the constraint.')
    analysis = explore.synthesis(state)
    return {'scope': 'Fictional scripted participant using four computed adaptive baseline tasks and two approved single-detail comparisons. Live outputs are not prewritten. This demonstrates software/model behaviour, not human research validity or causal proof. The simulated rule values free delivery most, then verification and impact; this rule is not disclosed to Muse.',
            'expected_comparison': 'Delivery cost (b) first when Muse finds the budget correction useful; verification (d) is the rival. Final reading may remain cautious or unresolved.',
            'analysis': analysis, 'api_usage': state['api_usage'],
            'checks': {'accepted_bounded_plan': state.get('muse_plan', {}).get('status') == 'accepted',
                       'first_comparison': state['contrasts'][0]['factor'],
                       'checked_reviews': sum(r['status'] == 'ok' for r in state.get('muse_reviews', [])),
                       'calls': len(state['api_usage']),
                       'correction_preserved': analysis['participant_explanation']['effective'].startswith('Fictional correction:')}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Use the configured Meta API, up to four calls on fictional data.')
    parser.add_argument('--output', default='outputs/muse-reasoning-demo.json')
    args = parser.parse_args()
    if args.live:
        load_env_file(Path('.env'))
    meta = MetaClient()
    if not args.live: meta.api_key = ''
    if args.live and not meta.enabled: raise RuntimeError('Configure MODEL_API_KEY locally before running the live demo')
    result = run(meta)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'scope': result['scope'], 'checks': result['checks']}, indent=2))


if __name__ == '__main__': main()
