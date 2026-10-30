from copy import deepcopy
import json
import unittest
from unittest.mock import Mock, patch

from choicegap import explore, muse_research
from choicegap.meta import MetaClient
from choicegap.muse_demo import fixture, choose


class MuseResearchTests(unittest.TestCase):
    def setUp(self):
        self.state = fixture()
        self.local = MetaClient(); self.local.api_key = ''
        self.answer(text='Verification matters.')
        self.answer(text='At the same fee I would consider it.')

    def answer(self, meta=None, **fields):
        explore.advance(self.state, {'answer_token': self.state['pending']['answer_token'], **fields}, meta or self.local)

    def checked(self):
        self.answer(status='corrected', factor='unresolved', text='The fee is my budget constraint.')

    def call(self, factor='b'):
        return {'id': 'call_bounded', 'name': 'select_approved_comparison', 'arguments': {
            'factor': factor, 'leading_explanation': 'The fee may be the constraint.',
            'alternative_explanation': 'Verification may matter independently of cost.',
            'reason': 'Compare the fee change before the verification change.',
            'if_switch': 'A switch would be consistent with a fee constraint, not proof.',
            'if_same': 'No switch would leave other constraints open.',
            'evidence_refs': [{'source_id': 'interview.check', 'quote': 'fee is my budget constraint'}]}}

    def reviewer(self, update='strengthened'):
        return {'summary': 'The fee looks worth investigating.', 'what_changed': 'The fee changed and the option selection changed.',
            'next_step': 'Retest the fee change with more people.', 'remaining_uncertainty': 'Repeated exposure or other missing constraints could matter.',
            'factor': 'b', 'rival': 'd', 'update': update,
            'evidence_refs': [{'source_id': 'comparison.b', 'quote': ''}, {'source_id': 'interview.check', 'quote': 'fee is my budget constraint'}]}

    def test_full_packet_has_exact_choices_ratings_correction_and_no_nonce(self):
        self.checked()
        evidence = muse_research.packet(self.state)
        sources = {s['id']: s for s in evidence['sources']}
        self.assertIn('choice.4', sources)
        self.assertIn('survey.ratings', sources)
        self.assertEqual(sources['interview.check']['text'], 'The fee is my budget constraint.')
        self.assertIsNone(evidence['previous_interpretation'])
        self.assertNotIn('answer_token', json.dumps(evidence))
        self.assertNotIn('comparison.d', sources)
        self.assertEqual(evidence['unanswered_comparisons'], 2)

    def test_valid_tool_selects_existing_comparison_before_response(self):
        self.checked()
        original = {c['factor']: c['stimulus_sha256'] for c in self.state['contrasts']}
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        meta.select_research_comparison.return_value = self.call()
        muse_research.select(self.state, meta)
        self.assertEqual(self.state['contrasts'][0]['factor'], 'b')
        self.assertEqual({c['factor']: c['stimulus_sha256'] for c in self.state['contrasts']}, original)
        self.assertTrue(self.state['muse_plan']['planned_before_response'])
        self.assertTrue(all(c['response'] is None for c in self.state['contrasts']))
        self.assertIn('if_switch', self.state['contrasts'][0]['predicted_comparison'])

    def test_unknown_comparison_and_forged_quote_fall_back_without_editing_tasks(self):
        self.checked()
        original = deepcopy(self.state['contrasts'])
        for call in (self.call('c'), self.call()):
            if call['arguments']['factor'] == 'b': call['arguments']['evidence_refs'][0]['quote'] = 'invented'
            meta = Mock(enabled=True, model='Muse-test', usage=[])
            meta.select_research_comparison.return_value = call
            muse_research.select(self.state, meta)
            self.assertEqual(self.state['muse_plan']['status'], 'fallback')
            self.assertEqual(self.state['contrasts'], original)

    def test_participant_selected_factor_takes_precedence(self):
        self.answer(status='corrected', factor='d', text='The evidence is the constraint.')
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        meta.select_research_comparison.return_value = self.call('b')
        muse_research.select(self.state, meta, participant_factor='d')
        self.assertEqual(self.state['contrasts'][0]['factor'], 'd')
        self.assertEqual(self.state['muse_plan']['status'], 'fallback')

    def test_checked_review_references_result_and_retains_participant_correction(self):
        self.checked()
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        meta.select_research_comparison.return_value = self.call()
        muse_research.select(self.state, meta)
        c = self.state['contrasts'][0]
        c['response'] = {'displayed_choice': 'a', 'baseline_option_identity': 'b', 'switched': True}
        meta.reconsider_research.return_value = self.reviewer()
        muse_research.reconsider(self.state, meta, 'after_first_comparison')
        review = self.state['muse_reviews'][-1]
        self.assertEqual(review['status'], 'ok')
        self.assertEqual(review['previous_factor'], 'b')
        self.assertFalse(review['factor_changed'])
        self.assertEqual(len(review['evidence_sha256']), 64)
        evidence, tool_exchange = meta.reconsider_research.call_args.args
        self.assertEqual(tool_exchange['call']['id'], 'call_bounded')
        self.assertTrue(tool_exchange['result']['response']['switched'])
        self.assertEqual(evidence['participant_check']['text'], 'The fee is my budget constraint.')

    def test_review_rejects_omitted_correction_or_unobserved_comparison(self):
        self.checked()
        c = next(c for c in self.state['contrasts'] if c['factor'] == 'b')
        c['response'] = {'displayed_choice': 'a', 'baseline_option_identity': 'b', 'switched': True}
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        missing_correction = self.reviewer(); missing_correction['evidence_refs'] = [{'source_id': 'comparison.b', 'quote': ''}]
        unseen_result = self.reviewer(); unseen_result['evidence_refs'][0]['source_id'] = 'comparison.d'
        for result in (missing_correction, unseen_result):
            meta.reconsider_research.return_value = result
            muse_research.reconsider(self.state, meta, 'after_first_comparison')
            self.assertEqual(self.state['muse_reviews'][-1]['status'], 'fallback')

    def test_unchanged_is_valid_and_skipped_comparisons_do_not_request_review(self):
        self.checked()
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        muse_research.reconsider(self.state, meta, 'after_first_comparison')
        meta.reconsider_research.assert_not_called()
        next(c for c in self.state['contrasts'] if c['factor'] == 'b')['response'] = {'displayed_choice': 'a', 'baseline_option_identity': 'a', 'switched': False}
        meta.reconsider_research.return_value = self.reviewer('unchanged')
        muse_research.reconsider(self.state, meta, 'after_first_comparison')
        self.assertEqual(self.state['muse_reviews'][-1]['update'], 'unchanged')

    def test_native_tool_request_is_strict_and_reconsideration_uses_actual_tool_result(self):
        self.checked()
        evidence = muse_research.packet(self.state)
        meta = MetaClient(); meta.api_key = 'test-only-key'
        response = Mock()
        call = self.call()
        response.read.return_value = json.dumps({'choices': [{'message': {'tool_calls': [{'id': call['id'], 'function': {'name': call['name'], 'arguments': json.dumps(call['arguments'])}}]}}], 'usage': {'total_tokens': 50}}).encode()
        response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False)
        with patch('urllib.request.urlopen', return_value=response) as request:
            actual = meta.select_research_comparison(evidence, self.state['contrasts'])
        body = json.loads(request.call_args.args[0].data)
        self.assertTrue(body['tools'][0]['function']['strict'])
        self.assertFalse(body['parallel_tool_calls'])
        self.assertEqual(actual, {**call, 'assistant_content': ''})
        self.assertEqual(body['tool_choice'], 'auto')
        with patch.object(meta, '_structured', return_value=self.reviewer()) as structured:
            meta.reconsider_research(evidence, {'call': call, 'result': {'accepted': True, 'response': {'switched': True}}})
        messages = structured.call_args.args[0]
        self.assertEqual(messages[-2]['role'], 'assistant')
        self.assertEqual(messages[-1]['role'], 'tool')
        self.assertEqual(messages[-1]['tool_call_id'], call['id'])

    def test_initial_interpretation_receives_full_context(self):
        meta = MetaClient()
        evidence = muse_research.packet(self.state)
        with patch.object(meta, '_structured', return_value={}) as request:
            meta.interpret_choice({'why': 'Verification'}, self.state['attributes'], evidence)
        content = json.loads(request.call_args.args[0][-1]['content'])
        self.assertEqual(content['full_session_evidence'], evidence)

    def test_version_one_policy_is_preserved(self):
        self.assertEqual(explore.policy(1)['version'], 1)
        self.assertIn('One Muse interpretation call at most', explore.policy(1)['scope'])
        self.assertEqual(explore.policy(2)['version'], 2)
        self.assertIn('at most four calls', explore.policy(2)['scope'])

    def test_shipped_demo_completes_four_calls_without_double_counting_usage(self):
        from choicegap.muse_demo import run
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        def interpretation(responses, attrs, evidence):
            meta.usage.append({'task': 'interpret'})
            self.assertIn('choice.4', [s['id'] for s in evidence['sources']])
            return {'summary': 'Verification may matter.', 'quote': responses['why'], 'factor': 'd', 'rival': 'b'}
        def selection(evidence, candidates):
            meta.usage.append({'task': 'select'})
            call = self.call()
            call['arguments']['evidence_refs'] = [{'source_id': 'interview.check', 'quote': evidence['participant_check']['text']}]
            return call
        def review(evidence, exchange):
            meta.usage.append({'task': 'review'})
            value = self.reviewer()
            value['evidence_refs'][1]['quote'] = evidence['participant_check']['text']
            sources = {s['id']: s for s in evidence['sources']}
            for source_id in evidence['latest_observations']:
                if not any(r['source_id'] == source_id for r in value['evidence_refs']):
                    source = sources[source_id]
                    value['evidence_refs'].append({'source_id': source_id, 'quote': source['text'] if source['kind'] == 'text' else ''})
            return value
        meta.interpret_choice.side_effect = interpretation
        meta.select_research_comparison.side_effect = selection
        meta.reconsider_research.side_effect = review
        result = run(meta)
        self.assertEqual(result['checks']['calls'], 4)
        self.assertTrue(result['checks']['accepted_bounded_plan'])
        self.assertEqual(result['checks']['checked_reviews'], 2)
        self.assertTrue(result['checks']['correction_preserved'])

    def test_legacy_sessions_do_not_start_the_new_planning_loop(self):
        self.state['version'] = 1
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        self.answer(meta=meta, status='unresolved')
        while self.state['phase'].startswith('condition'):
            self.answer(meta=meta, choice='a')
        self.answer(meta=meta, text='A final comment.')
        meta.select_research_comparison.assert_not_called()
        meta.reconsider_research.assert_not_called()

    def test_skipping_all_text_makes_no_calls_even_with_answered_comparisons(self):
        self.state = fixture()
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        self.answer(meta=meta, text=''); self.answer(meta=meta, text='')
        self.answer(meta=meta, status='unresolved')
        while self.state['phase'].startswith('condition'):
            self.answer(meta=meta, choice='a')
        self.answer(meta=meta, text='')
        meta.interpret_choice.assert_not_called()
        meta.select_research_comparison.assert_not_called()
        meta.reconsider_research.assert_not_called()

    def test_final_review_cannot_ignore_the_latest_response(self):
        self.checked()
        next(c for c in self.state['contrasts'] if c['factor'] == 'b')['response'] = {'displayed_choice': 'a', 'baseline_option_identity': 'a', 'switched': False}
        self.state['events'].append({'id': 'interview.reflection', 'phase': 'reflection', 'kind': 'text', 'response': 'This latest explanation matters.'})
        meta = Mock(enabled=True, model='Muse-test', usage=[])
        meta.reconsider_research.return_value = self.reviewer()
        muse_research.reconsider(self.state, meta, 'after_final_response')
        self.assertEqual(self.state['muse_reviews'][-1]['status'], 'fallback')


if __name__ == '__main__': unittest.main()
