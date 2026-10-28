"""Bounded, evidence-linked interviews and within-session condition comparisons."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import secrets
import threading
from typing import Any

VERSION = 1
LOCKS = [threading.Lock() for _ in range(64)]
QUESTIONS = {
    'why': 'What mattered when you made this choice? You can also describe anything the options missed.',
    'clarify': 'What circumstances, if any, could lead you to choose differently? It is fine if none would.',
    'check': 'Does this description reflect your reasoning? You can correct it or leave it unresolved.',
    'reflection': 'What, if anything, explains your choices across these versions? You can also describe something we missed.',
}


def policy() -> dict[str, Any]:
    return {'version': VERSION, 'questions': QUESTIONS, 'max_condition_tasks': 2,
            'scope': 'Four adaptive choices, an optional reversed repeat, four optional text responses including an interpretation check, and up to two single-detail variations of one answered task. Only approved factor levels are used. Variations do not update the choice model. One Muse interpretation call at most; no model call when text is skipped.',
            'limits': 'Within-session hypothetical comparisons are descriptive. Order, learning, repeated exposure and unmeasured factors prevent a causal or real-purchase claim.'}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def lock_for(token: str):
    return LOCKS[int(hashlib.sha256(token.encode()).hexdigest(), 16) % len(LOCKS)]


def attributes(session) -> list[dict]:
    if hasattr(session, 'study'):
        return [dict(a) for a in session.study.attributes]
    return [
        dict(id='price', label='Delivery fee', low_label='£3 delivery fee', high_label='Free delivery', fact_index=0),
        dict(id='impact', label='Environmental impact', low_label='Standard delivery emissions', high_label='Estimated delivery emissions: 60% lower', fact_index=1),
        dict(id='convenience', label='Delivery timing', low_label='Flexible delivery day', high_label='Two-hour delivery window', fact_index=2),
        dict(id='trust', label='Claim evidence', low_label='Retailer calculation', high_label='Method independently verified', fact_index=3),
    ]


def levels(option: dict, attrs: list[dict]) -> dict:
    if 'levels' in option:
        return option['levels']
    return {a['id']: (int(option['price'] == 0) if a['id'] == 'price' else option[a['id']]) for a in attrs}


def begin(session, base_report: dict) -> dict:
    attrs = attributes(session)
    trace = [t for t in base_report['decision_trace'] if not t['holdout']]
    answered = [t for t in trace if t['displayed_choice'] in ('a', 'b')]
    ratings = session.stated_ratings
    tops = {k for k, v in ratings.items() if v == max(ratings.values())}
    def discrepancy(t):
        c = t['displayed_choice']; other = 'b' if c == 'a' else 'a'
        return sum(levels(t['stimulus'][c], attrs)[k] < levels(t['stimulus'][other], attrs)[k] for k in tops)
    anchor = max(answered, key=discrepancy) if answered else (trace[-1] if trace else None)
    state = {'version': VERSION, 'phase': 'why', 'attributes': attrs,
             'survey': {'ratings': ratings, 'intention': session.intention_score, 'statement': session.statement},
             'base_report': deepcopy(base_report), 'anchor': deepcopy(anchor), 'events': [], 'contrasts': [],
             'interpretation': None, 'api_usage': [], 'analysis_source': 'literal-local',
             'anchor_reason': ('A task where a top-rated factor traded against the selected option; this is a clarification trigger, not a diagnosed gap.' if anchor and answered and discrepancy(anchor) else 'An answered task for neutral clarification; no rating-choice discrepancy is assumed.'),
             'policy': policy(), 'policy_sha256': digest(policy())}
    issue(state)
    return state


def issue(state):
    phase = state['phase']
    step = {'kind': 'choice' if phase.startswith('condition') else 'text', 'phase': phase, 'issued_at': datetime.now(timezone.utc).isoformat(),
            'question': QUESTIONS.get(phase, 'Which option would you choose now?'),
            'reason': state.get('anchor_reason') if phase == 'why' else 'Approved bounded follow-up; no diagnosis of a participant.'}
    if phase == 'why' and state['anchor']:
        step['context'] = {'stimulus': state['anchor']['stimulus'], 'choice': state['anchor']['displayed_choice']}
    if phase == 'clarify':
        why = next(e['response'] for e in state['events'] if e['phase'] == 'why')
        if why:
            step['response_context'] = why
    if phase == 'check':
        step['interpretation'] = state['interpretation']
        step['factors'] = [{'id': a['id'], 'label': a['label']} for a in state['attributes']]
    if phase.startswith('condition'):
        contrast = state['contrasts'][int(phase[-1])]
        step.update(stimulus=contrast['stimulus'], reason=contrast['selection_reason'])
    state['pending'] = {**step, 'answer_token': secrets.token_urlsafe(18)}


def public_step(state):
    # Selection rationales and hypotheses belong to the researcher, not the participant.
    return {k: deepcopy(v) for k, v in state['pending'].items() if k != 'reason'}


def plan_contrasts(state, factor=None):
    anchor = state['anchor']
    if not anchor or anchor['displayed_choice'] not in ('a', 'b'):
        state['contrasts'] = []
        return
    stimulus = anchor['stimulus']
    attrs = state['attributes']
    varying = [a for a in attrs if levels(stimulus['a'], attrs)[a['id']] != levels(stimulus['b'], attrs)[a['id']]]
    leader_order = sorted(state['base_report']['posterior'], key=state['base_report']['posterior'].get, reverse=True)
    varying.sort(key=lambda a: (a['id'] != factor, leader_order.index(a['id'])))
    unchosen = 'b' if anchor['displayed_choice'] == 'a' else 'a'
    contrasts = []
    for a in varying[:2]:
        changed = deepcopy(stimulus)
        option = changed[unchosen]
        old = levels(option, attrs)[a['id']]
        new = 1 - old
        if 'levels' in option:
            option['levels'][a['id']] = new
            index = next(i for i, item in enumerate(attrs) if item['id'] == a['id'])
            option['facts'][index] = f"{a['label']}: {a['high_label'] if new else a['low_label']}"
        else:
            option[a['id']] = (0 if new else 3) if a['id'] == 'price' else new
            option['facts'][a['fact_index']] = a['high_label'] if new else a['low_label']
        changed['id'] = f"condition-{a['id']}"
        changed['rationale'] = 'One approved detail changes relative to the recorded anchor task.'
        # Stable identities are anchored to the displayed baseline A/B, independent of new display order.
        flipped = secrets.choice([False, True])
        if flipped:
            changed['a'], changed['b'] = changed['b'], changed['a']
        for side in ('a', 'b'):
            changed[side]['name'] = f'Option {side.upper()}'
        changed['flipped'] = flipped
        comparisons = []
        for side in ('a', 'b'):
            baseline_side = ('b' if side == 'a' else 'a') if flipped else side
            for index, (before, after) in enumerate(zip(stimulus[baseline_side]['facts'], changed[side]['facts'])):
                if before != after:
                    comparisons.append({'baseline_option': baseline_side, 'fact_index': index, 'before': before, 'after': after})
        if len(comparisons) != 1:
            raise ValueError('A condition task must change exactly one displayed fact')
        contrasts.append({'factor': a['id'], 'factor_label': a['label'], 'changed': comparisons[0],
                          'baseline_stimulus': deepcopy(stimulus), 'baseline_choice': anchor['displayed_choice'],
                          'stimulus': changed, 'stimulus_sha256': digest(changed), 'reversed': flipped,
                          'selection_reason': ('Participant-selected factor tested first; a competing factor is also tested.' if factor else 'Two differing approved factors tested separately; ranked by current choice-model accounts.'),
                          'response': None, 'predicted_comparison': 'Does changing this detail coincide with switching the selected option relative to the baseline? A switch is descriptive, not a unique mechanism.'})
    state['contrasts'] = contrasts


def advance(state: dict, payload: dict, meta) -> None:
    pending = state['pending']; phase = state['phase']
    token = payload.get('answer_token')
    if not isinstance(token, str) or not secrets.compare_digest(token.encode(), pending['answer_token'].encode()):
        raise ValueError('This follow-up has already been answered or is out of date')
    text = payload.get('text', '')
    if not isinstance(text, str) or len(text) > 2000:
        raise ValueError('Use at most 2000 characters')
    text = text.strip()
    event = {k: deepcopy(v) for k, v in pending.items() if k != 'answer_token'}
    event['id'] = f'interview.{phase}'
    event['answered_at'] = datetime.now(timezone.utc).isoformat()
    if phase.startswith('condition'):
        choice = payload.get('choice')
        if choice not in ('a', 'b', 'outside', 'skip'):
            raise ValueError('Choose an option, neither, or skip')
        item = state['contrasts'][int(phase[-1])]
        canonical = ('b' if choice == 'a' else 'a') if choice in ('a', 'b') and item['reversed'] else choice
        item['response'] = {'displayed_choice': choice, 'baseline_option_identity': canonical,
                            'switched': canonical != item['baseline_choice'] if canonical in ('a', 'b') else None}
        event['response'] = choice
        state['phase'] = 'condition1' if phase == 'condition0' and len(state['contrasts']) > 1 else 'reflection'
    else:
        event['response'] = text
        if phase == 'why':
            state['phase'] = 'clarify'
        elif phase == 'clarify':
            why = next(e['response'] for e in state['events'] if e['phase'] == 'why')
            interp = {'summary': f'Your earlier answer: “{why}”' if why else 'No explanation supplied; the reasons remain unresolved.', 'quote': why, 'factor': 'unresolved', 'rival': 'unresolved'}
            if meta.enabled and (why or text):
                try:
                    result = meta.interpret_choice({'why': why, 'clarify': text}, state['attributes'])
                    allowed = {a['id'] for a in state['attributes']} | {'unresolved'}
                    if (not isinstance(result.get('quote'), str) or not result['quote'] or
                            not any(result['quote'] in source for source in (why, text)) or
                            result.get('factor') not in allowed or result.get('rival') not in allowed or
                            not isinstance(result.get('summary'), str) or not 1 <= len(result['summary']) <= 600):
                        raise ValueError('Invalid source-linked interpretation')
                    interp = result
                    state['analysis_source'] = meta.model
                except (RuntimeError, ValueError, KeyError, TypeError):
                    state['analysis_source'] = 'literal-local-after-model-error'
            state['api_usage'] = list(meta.usage)
            state['interpretation'] = interp
            state['phase'] = 'check'
        elif phase == 'check':
            status = payload.get('status')
            factor = payload.get('factor', 'unresolved')
            if status not in ('confirmed', 'corrected', 'unresolved') or factor not in {a['id'] for a in state['attributes']} | {'unresolved'}:
                raise ValueError('Check the interpretation and select a valid factor')
            if status == 'corrected' and not text:
                raise ValueError('Please supply the correction, or mark the interpretation unresolved')
            event.update(status=status, factor=factor)
            state['correction'] = {'status': status, 'text': text, 'factor': factor,
                                   'supersedes_model_summary': status != 'confirmed'}
            # A rejected model interpretation cannot silently steer subsequent tasks.
            selected = factor if factor != 'unresolved' else (state['interpretation']['factor'] if status == 'confirmed' else None)
            plan_contrasts(state, selected)
            state['phase'] = 'condition0' if state['contrasts'] else 'reflection'
        elif phase == 'reflection':
            state['phase'] = 'complete'
    state['events'].append(event)
    state['pending'] = None
    if state['phase'] != 'complete':
        issue(state)


def synthesis(state) -> dict:
    correction = state.get('correction', {'status': 'unresolved'})
    refs = [{'id': 'survey.statement', 'kind': 'stated', 'text': state['survey']['statement']}]
    refs.extend({'id': e['id'], 'kind': 'participant-response', 'text': e['response']} for e in state['events'] if e['kind'] == 'text')
    effective = (correction.get('text', '') if correction['status'] == 'corrected' else
                 state['interpretation']['summary'] if correction['status'] == 'confirmed' else 'Interpretation unresolved.')
    tests = []
    for index, c in enumerate(state['contrasts']):
        tests.append({**deepcopy(c), 'id': f'condition.{index}',
                      'recommendation': (f"Evaluate the tested {c['factor_label'].lower()} change in a randomized or field study before implementation." if c['response'] and c['response']['switched'] is True else
                                         f"No switch observed here; this does not establish that {c['factor_label'].lower()} is irrelevant. Examine the explanation and rival constraints." if c['response'] and c['response']['switched'] is False else
                                         'No comparable A/B response; no product recommendation is inferred from this comparison.'),
                      'evidence_refs': ['interview.check', f'interview.condition{index}', 'interview.reflection']})
    top = max(state['survey']['ratings'].values())
    priorities = [a['label'].lower() for a in state['attributes'] if state['survey']['ratings'][a['id']] == top]
    anchor = state['anchor']
    choice_description = (f"They rated {', '.join(priorities)} highest ({top}/5). In the task we asked about, they selected " +
                          ('neither option.' if anchor['displayed_choice'] == 'outside' else f"Option {anchor['displayed_choice'].upper()}.")) if anchor else 'No earlier choice was available to discuss.'
    return {'version': VERSION, 'survey': state['survey'], 'evidence': refs,
            'factor_labels': {a['id']: a['label'] for a in state['attributes']},
            'stated_priorities': [k for k, v in state['survey']['ratings'].items() if v == top],
            'alignment': {'trigger': state['anchor_reason'], 'anchor': anchor, 'interpretation': choice_description},
            'participant_explanation': {'effective': effective, 'status': correction['status'], 'original_model_interpretation': state['interpretation'], 'correction': correction, 'source': state['analysis_source'], 'evidence_refs': ['interview.why', 'interview.clarify', 'interview.check']},
            'untested_participant_factor': correction.get('factor') if correction.get('factor') not in {'unresolved', None} | {c['factor'] for c in state['contrasts']} else None,
            'condition_tests': tests,
            'behavioural_interpretation': {'scope': 'Candidate lenses for researcher review, not diagnoses or established mediators.',
                'model_candidate': state['interpretation']['factor'], 'model_rival': state['interpretation']['rival'],
                'candidate_status': 'Retained for researcher review after participant confirmation' if correction['status'] == 'confirmed' else 'Not adopted: participant corrected or left the interpretation unresolved',
                'lenses': ['Practical opportunity and capability constraints', 'Costs and benefits of the presented options', 'Credibility and uncertainty where supported by participant explanations'],
                'rivals': ['Mixed priorities', 'Unrepresented constraints', 'Task wording or order', 'Indifference or changed interpretation'],
                'evidence_refs': ['interview.why', 'interview.clarify', 'interview.check', 'interview.reflection']},
            'exposure_ledger': deepcopy(state['events']), 'policy': state['policy'], 'policy_sha256': state['policy_sha256'],
            'limitations': [state['policy']['limits'], 'Adaptive branches have different exposure denominators; do not interpret branch counts as prevalence.', 'Participant confirmation is a clarification, not independent validation of an explanation.', 'Only the approved four factors and binary levels were tested; no threshold or stable trait is estimated.', 'No prototype interactions, purchases or real-world outcomes were observed in this flow.']}


def aggregate(records: list[dict]) -> dict:
    cases = [{'case': r.get('id', i + 1), 'analysis': r['report']['ux_analysis']} for i, r in enumerate(records) if r.get('report', {}).get('ux_analysis')]
    phases = list(QUESTIONS) + ['condition0', 'condition1']
    by_condition = {}
    for case in cases:
        for test in case['analysis']['condition_tests']:
            # Compare only identical anchor and changed facts; orientation is not a condition.
            key = digest({'baseline': {s: test['baseline_stimulus'][s]['facts'] for s in ('a', 'b')}, 'changed': test['changed']})
            group = by_condition.setdefault(key, {'factor': test['factor_label'], 'changed': test['changed'], 'shown': 0, 'ab_responses': 0, 'switches': 0, 'outside': 0, 'skipped': 0, 'cases': []})
            group['shown'] += 1
            response = test['response']
            if response and response['switched'] is not None:
                group['ab_responses'] += 1
                group['switches'] += int(response['switched'])
            elif response and response['displayed_choice'] == 'outside': group['outside'] += 1
            else: group['skipped'] += 1
            group['cases'].append(case['case'])
    return {'completed_interviews': len(cases), 'cases': cases, 'condition_groups': list(by_condition.values()),
            'exposures': [{'phase': phase, 'shown': sum(any(e['phase'] == phase for e in c['analysis']['exposure_ledger']) for c in cases),
                           'answered': sum(any(e['phase'] == phase and (e['response'] not in ('', 'skip') or e.get('status') in ('confirmed', 'corrected')) for e in c['analysis']['exposure_ledger']) for c in cases)} for phase in phases],
            'scope': 'Completed-session exposure counts only. Blank text and explicit skips remain missing; neither is a recorded choice. These are sessions, not verified unique participants.'}


def collection_progress(states: list[dict], study_id: str) -> dict:
    ongoing = [s for s in states if s['record'].get('study_id') == study_id and s['phase'] != 'complete']
    counts = {}
    for state in ongoing:
        for event in state['events'] + ([state['pending']] if state.get('pending') else []):
            item = counts.setdefault(event['phase'], {'phase': event['phase'], 'issued': 0, 'responded': 0})
            item['issued'] += 1
            item['responded'] += int('response' in event)
    return {'unfinished_interviews': len(ongoing), 'exposures': list(counts.values()),
            'scope': 'Issued by the server, not confirmed as viewed. Unfinished interviews are not silently counted as completed or as negative responses. Baseline choice sessions before the interview remain memory-only.'}
