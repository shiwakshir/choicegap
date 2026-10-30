"""Small prespecified input ablation: two answers versus the complete fictional session."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from .config import load_env_file
from .meta import MetaClient
from .muse_demo import fixture
from .muse_research import packet


CASES = [
    {'id': 'verification_words_budget_choices', 'weights': {'b': 3, 'd': 1, 'a': .8}, 'expected_factor': 'b',
     'responses': {'why': 'Fictional respondent: I value independent verification of environmental claims.', 'clarify': 'Fictional respondent: Independent evidence makes a delivery claim more credible.'}},
    {'id': 'fee_words_verified_choices', 'weights': {'b': 1, 'd': 3, 'a': .8}, 'expected_factor': 'd',
     'responses': {'why': 'Fictional respondent: I value free delivery because fees add up.', 'clarify': 'Fictional respondent: I like delivery options that help me save money.'}},
    {'id': 'vague_words_budget_choices', 'weights': {'b': 3, 'd': 1, 'a': .8}, 'expected_factor': 'b',
     'responses': {'why': 'Fictional respondent: I compared the options and chose what worked.', 'clarify': 'Fictional respondent: It depends on my weekly shop.'}},
]


def evaluate(case):
    def chooser(exp):
        return max(('a', 'b'), key=lambda side: sum(weight * exp[side]['levels'][key] for key, weight in case['weights'].items()))
    state = fixture(chooser)
    for phase in ('why', 'clarify'):
        state['events'].append({'id': f'interview.{phase}', 'phase': phase, 'kind': 'text', 'response': case['responses'][phase]})
    evidence = packet(state)
    outputs = {}
    for mode in ('narrow', 'full_context'):
        meta = MetaClient()
        try:
            value = meta.interpret_choice(case['responses'], state['attributes'], evidence if mode == 'full_context' else None)
            valid = (value.get('factor') in {'a', 'b', 'c', 'd', 'unresolved'} and value.get('rival') in {'a', 'b', 'c', 'd', 'unresolved'} and
                     isinstance(value.get('summary'), str) and 1 <= len(value['summary']) <= 600 and
                     isinstance(value.get('quote'), str) and bool(value['quote']) and any(value['quote'] in text for text in case['responses'].values()))
            outputs[mode] = {'status': 'ok' if valid else 'validation_error', 'result': value, 'matches_scripted_factor': valid and value['factor'] == case['expected_factor'], 'usage': meta.usage}
        except RuntimeError:
            outputs[mode] = {'status': 'request_error', 'matches_scripted_factor': False, 'usage': meta.usage}
    return {'case': case, 'full_context_input': evidence, 'outputs': outputs}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--live', action='store_true'); parser.add_argument('--output', default='outputs/muse-context-ablation.json')
    args = parser.parse_args()
    if not args.live: raise ValueError('This evaluation makes six real API calls; pass --live to run it')
    load_env_file(Path('.env'))
    if not MetaClient().enabled: raise RuntimeError('Configure MODEL_API_KEY locally')
    with ThreadPoolExecutor(max_workers=3) as pool: cases = list(pool.map(evaluate, CASES))
    summary = {mode: {'expected_factor_matches': sum(c['outputs'][mode]['matches_scripted_factor'] for c in cases),
                      'valid_outputs': sum(c['outputs'][mode]['status'] == 'ok' for c in cases), 'planned_calls': len(cases)} for mode in ('narrow', 'full_context')}
    result = {'scope': 'Six real Muse calls on three prespecified fictional scenarios, one call per input condition. Expected factors come from a scripted choice rule, not validated human motives. Same interpretation prompt/schema/model, with full-session evidence added in one condition. This is a tiny development ablation, not a reliable accuracy estimate, provider comparison or proof of causal inference. No output-based case selection or retries.',
              'summary': summary, 'cases': cases}
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
