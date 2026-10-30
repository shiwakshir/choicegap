"""Validated evidence packets and bounded Muse planning/reconsideration."""
from copy import deepcopy
import json


def packet(state):
    sources = [{'id': 'survey.statement', 'kind': 'text', 'text': state['survey']['statement']},
               {'id': 'survey.ratings', 'kind': 'record', 'text': json.dumps(state['survey'], ensure_ascii=False)}]
    for index, item in enumerate(state['base_report']['decision_trace']):
        sources.append({'id': f'choice.{index + 1}', 'kind': 'record', 'text': json.dumps({
            'stimulus': item['stimulus'], 'selected_displayed_option': item['displayed_choice'],
            'repeat': item.get('holdout', False)}, ensure_ascii=False)})
    for event in state['events']:
        sources.append({'id': event['id'], 'kind': 'text' if event['kind'] == 'text' else 'record',
                        'text': event['response'] if event['kind'] == 'text' else json.dumps(event['response'])})
    for c in state['contrasts']:
        if c['response'] is None:
            continue  # A planned task is not an observed response or an explicit skip.
        sources.append({'id': f"comparison.{c['factor']}", 'kind': 'record', 'text': json.dumps({
            'changed': c['changed'], 'baseline_choice': c['baseline_choice'], 'stimulus': c['stimulus'],
            'response': c['response']}, ensure_ascii=False)})
    correction = deepcopy(state.get('correction'))
    previous = state.get('interpretation') if not correction or correction['status'] == 'confirmed' else None
    plan = state.get('muse_plan')
    planning_reading = deepcopy(plan['tool_call']['arguments']) if plan and plan['status'] == 'accepted' else None
    return {'sources': sources, 'approved_factors': deepcopy(state['attributes']),
            'planning_reading': planning_reading,
            'participant_check': correction, 'previous_interpretation': deepcopy(previous),
            'previous_interpretation_rejected': bool(correction and correction['status'] != 'confirmed'),
            'earlier_reviews': deepcopy(state.get('muse_reviews', [])),
            'unanswered_comparisons': sum(c['response'] is None for c in state['contrasts']),
            'scope': 'Hypothetical within-session choices. Ratings and statements are not actual purchases. A correction takes precedence over the initial model interpretation; unresolved is not confirmation. Record references describe supplied observations, not causal proof.'}


def references_schema():
    return {'type': 'array', 'items': {'type': 'object', 'properties': {
        'source_id': {'type': 'string'}, 'quote': {'type': 'string'}},
        'required': ['source_id', 'quote'], 'additionalProperties': False}}


def validate_refs(refs, evidence):
    sources = {s['id']: s for s in evidence['sources']}
    if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
        raise ValueError('Supply one to twelve evidence references')
    for ref in refs:
        if not isinstance(ref, dict) or ref.get('source_id') not in sources or not isinstance(ref.get('quote'), str):
            raise ValueError('Unknown evidence reference')
        source = sources[ref['source_id']]
        quote = ref['quote']
        if (source['kind'] == 'text' and not quote) or (quote and quote not in source['text']):
            raise ValueError('Use an exact quote from the cited response')


def text_field(result, key, maximum=500):
    if not isinstance(result.get(key), str) or not 1 <= len(result[key].strip()) <= maximum:
        raise ValueError(f'Invalid {key}')


def tool_definition(candidates):
    return {'type': 'function', 'function': {'name': 'select_approved_comparison',
        'description': 'Select which of the supplied, code-audited single-detail comparisons to present first. Cannot create or alter an option. Both approved comparisons remain in the study.',
        'strict': True, 'parameters': {'type': 'object', 'properties': {
            'factor': {'type': 'string', 'enum': [c['factor'] for c in candidates]},
            'leading_explanation': {'type': 'string'}, 'alternative_explanation': {'type': 'string'},
            'reason': {'type': 'string'}, 'if_switch': {'type': 'string'}, 'if_same': {'type': 'string'},
            'evidence_refs': references_schema()},
            'required': ['factor', 'leading_explanation', 'alternative_explanation', 'reason', 'if_switch', 'if_same', 'evidence_refs'], 'additionalProperties': False}}}


def select(state, meta, participant_factor=None):
    if not meta.enabled or not state['contrasts'] or not any(e['kind'] == 'text' and e['response'] for e in state['events']):
        return
    evidence = packet(state)
    candidates = [{k: deepcopy(c[k]) for k in ('factor', 'factor_label', 'changed', 'stimulus', 'stimulus_sha256')} for c in state['contrasts']]
    try:
        call = meta.select_research_comparison(evidence, candidates)
        if not isinstance(call, dict):
            raise ValueError('Invalid tool call')
        if call.get('name') != 'select_approved_comparison' or not isinstance(call.get('id'), str) or not 1 <= len(call['id']) <= 64:
            raise ValueError('Invalid tool call')
        args = call['arguments']
        if not isinstance(args, dict):
            raise ValueError('Invalid tool arguments')
        for key in ('leading_explanation', 'alternative_explanation', 'reason', 'if_switch', 'if_same'):
            text_field(args, key)
        validate_refs(args['evidence_refs'], evidence)
        ids = [c['factor'] for c in state['contrasts']]
        if args['factor'] not in ids:
            raise ValueError('Comparison is not approved')
        if participant_factor in ids and args['factor'] != participant_factor:
            raise ValueError('Participant-selected detail takes precedence')
        state['contrasts'].sort(key=lambda c: c['factor'] != args['factor'])
        selected = state['contrasts'][0]
        selected['selection_reason'] = args['reason']
        selected['predicted_comparison'] = {'if_switch': args['if_switch'], 'if_same': args['if_same']}
        state['muse_plan'] = {'status': 'accepted', 'source': meta.model, 'tool_call': call,
                              'planned_before_response': True, 'evidence': evidence,
                              'tool_result': {'accepted': True, 'factor': selected['factor'], 'stimulus_sha256': selected['stimulus_sha256'],
                                              'scope': 'Code validated and selected an existing comparison. No participant response has been observed yet.'}}
    except (RuntimeError, ValueError, KeyError, TypeError):
        state['muse_plan'] = {'status': 'fallback', 'source': 'computed', 'reason': 'Muse planning failed validation or was unavailable. The approved local ordering was retained.'}


def reconsider(state, meta, stage):
    if not meta.enabled or not any(e['kind'] == 'text' and e['response'] for e in state['events']) or not any(c['response'] and c['response']['switched'] is not None for c in state['contrasts']):
        return
    evidence = packet(state)
    evidence['review_stage'] = stage
    latest = [f"comparison.{state['contrasts'][0]['factor']}"] if stage == 'after_first_comparison' else [f"comparison.{state['contrasts'][-1]['factor']}"]
    if stage == 'after_final_response' and any(e['phase'] == 'reflection' and e['response'] for e in state['events']):
        latest.append('interview.reflection')
    evidence['latest_observations'] = latest
    from .explore import digest
    try:
        plan = state.get('muse_plan')
        tool_exchange = None
        if plan and plan['status'] == 'accepted':
            selected = next(c for c in state['contrasts'] if c['factor'] == plan['tool_result']['factor'])
            tool_exchange = {'call': plan['tool_call'], 'result': {**plan['tool_result'], 'response': selected['response'],
                'scope': 'The selected comparison was presented; this is its recorded response, not a causal effect.'}}
        result = meta.reconsider_research(evidence, tool_exchange)
        for key in ('summary', 'what_changed', 'next_step', 'remaining_uncertainty'):
            text_field(result, key)
        allowed = {a['id'] for a in state['attributes']} | {'unresolved'}
        if result.get('factor') not in allowed or result.get('rival') not in allowed or result.get('update') not in ('strengthened', 'weakened', 'unchanged', 'unresolved'):
            raise ValueError('Invalid reconsideration')
        validate_refs(result['evidence_refs'], evidence)
        observed = {f"comparison.{c['factor']}" for c in state['contrasts'] if c['response'] and c['response']['switched'] is not None}
        if not observed.intersection(r['source_id'] for r in result['evidence_refs']):
            raise ValueError('Review must reference an answered comparison')
        if not set(latest).issubset(r['source_id'] for r in result['evidence_refs']):
            raise ValueError('Review must account for the latest comparison and final explanation')
        if state.get('correction', {}).get('status') == 'corrected' and not any(r['source_id'] == 'interview.check' for r in result['evidence_refs']):
            raise ValueError('Review must retain the participant correction')
        previous_reviews = [r for r in state.get('muse_reviews', []) if r['status'] == 'ok']
        previous_factor = previous_reviews[-1]['factor'] if previous_reviews else (evidence['planning_reading']['factor'] if evidence['planning_reading'] else None)
        state.setdefault('muse_reviews', []).append({'stage': stage, 'source': meta.model, 'status': 'ok', **result,
                                                     'previous_factor': previous_factor, 'factor_changed': result['factor'] != previous_factor if previous_factor else None,
                                                     'based_on_sources': [s['id'] for s in evidence['sources']], 'evidence_sha256': digest(evidence)})
    except (RuntimeError, ValueError, KeyError, TypeError):
        state.setdefault('muse_reviews', []).append({'stage': stage, 'source': 'computed', 'status': 'fallback',
            'summary': 'An updated model interpretation is unavailable. Use the recorded choices and participant explanation.'})
