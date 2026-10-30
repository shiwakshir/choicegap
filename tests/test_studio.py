import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from choicegap import studio
from choicegap.research import ResearchStore


def q(kind='open', evidence='context'):
    return {'type': kind, 'prompt': 'What mattered in your most recent choice?',
            'options': [] if kind in ('open', 'number') else ['Accuracy', 'Familiarity', 'Neither'],
            'evidence_kind': 'hypothetical_choice' if kind == 'choice' else evidence,
            'purpose': 'Understand the context', 'show_stimulus': False}


def draft():
    return {'id': 'draft', 'status': 'draft', 'created_at': studio.now(), 'brief': 'AI adoption',
            'stimulus': {'text': '', 'image': ''}, 'design': studio.design({
                'title': 'AI assistant study', 'participant_intro': 'Tell us about your experience.',
                'objective': 'Understand AI assistant adoption', 'hypotheses': ['Familiarity may matter'],
                'followup_topics': ['Recent use', 'Switching effort'],
                'questions': [q(kind) for kind in studio.TYPES], 'interview_questions': [q(), q()]})}


class FakeMeta:
    enabled = True
    model = 'test-muse'
    usage = []

    def _structured(self, messages, name, schema):
        if name == 'studio_probe':
            return {'ask': True, 'question': 'Can you describe a recent example?', 'topic': 'Recent use',
                    'reason': 'Clarify the most recent account', 'source_ids': ['R1'],
                    'rival_explanation': 'Switching effort may matter instead'}
        if name == 'studio_member_check':
            return {'summary': 'You described using the familiar tool. Is that accurate?'}
        if name == 'studio_design':
            return draft()['design']
        raise AssertionError(name)


class NoMeta(FakeMeta):
    enabled = False


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.study = studio.approve(draft(), {'confirmed': True, 'design': draft()['design'],
                                             'method': 'combined', 'recording': True})

    def answer(self, state, value=None, skip=False, meta=None):
        return studio.answer(self.study, state, {'nonce': state['nonce'], 'answer': value, 'skip': skip}, meta or NoMeta())

    def test_each_answer_type_and_rejections(self):
        good = {'open': 'Yesterday I used it to draft a message.', 'single': 'Accuracy',
                'multi': ['Familiarity', 'Neither'], 'ranking': ['Neither', 'Accuracy', 'Familiarity'],
                'scale': 3, 'number': 0, 'choice': 'Neither'}
        for kind, value in good.items():
            with self.subTest(kind=kind):
                self.assertEqual(studio.validate_answer(q(kind), value, False), value)
                self.assertIsNone(studio.validate_answer(q(kind), None, True))
        for kind, value in [('single', 'invented'), ('multi', ['Neither', 'Neither']),
                            ('ranking', ['Accuracy']), ('scale', True), ('scale', 6),
                            ('number', float('nan')), ('number', True), ('open', '')]:
            with self.subTest(kind=kind, invalid=value), self.assertRaises(ValueError):
                studio.validate_answer(q(kind), value, False)

    def test_publish_and_consent_are_explicit(self):
        with self.assertRaises(ValueError):
            studio.approve(draft(), {'confirmed': False})
        with self.assertRaises(ValueError):
            studio.start(self.study, False)
        edited = copy.deepcopy(draft()['design'])
        edited['questions'][0]['prompt'] = 'Your edited question?'
        approved = studio.approve(draft(), {'confirmed': True, 'method': 'survey', 'design': edited})
        self.assertEqual(approved['design']['questions'][0]['prompt'], 'Your edited question?')
        edited['questions'][0]['prompt'] = 'Subsequent edit'
        self.assertEqual(approved['design']['questions'][0]['prompt'], 'Your edited question?')

    def test_adaptive_probe_inserted_once_then_base_continues(self):
        state = studio.start(self.study, True)
        next_state = self.answer(state, 'I used a familiar tool yesterday.', meta=FakeMeta())
        self.assertEqual(state['responses'], [])
        self.assertTrue(next_state['queue'][next_state['index']]['adaptive'])
        self.assertEqual(next_state['probes']['survey'], 1)
        after = self.answer(next_state, 'Switching was too much effort.', meta=FakeMeta())
        self.assertEqual(after['queue'][after['index']]['id'], 'Q2')
        self.assertEqual(len(after['decisions']), 1)
        with self.assertRaises(ValueError):
            studio.answer(self.study, after, {'nonce': state['nonce'], 'answer': 'Accuracy'}, FakeMeta())

    def test_skips_do_not_trigger_model_and_completion_preserves_correction(self):
        state = studio.start(self.study, True)
        while state['status'] == 'active' and state['queue'][state['index']]['phase'] != 'correction':
            state = self.answer(state, skip=True, meta=FakeMeta())
        self.assertEqual(state['decisions'], [])
        state = self.answer(state, 'The premise did not apply to me.', meta=FakeMeta())
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(state['responses'][-1]['answer'], 'The premise did not apply to me.')
        self.assertEqual(state['responses'][-1]['question']['phase'], 'correction')
        self.assertTrue(all(r['skipped'] for r in state['responses'][:-1]))

    def test_out_of_scope_model_question_falls_back_to_approved_guide(self):
        class Bad(FakeMeta):
            def _structured(self, *args):
                return {**super()._structured(*args), 'topic': 'Political views'}
        state = self.answer(studio.start(self.study, True), 'I tried it once.', meta=Bad())
        self.assertEqual(state['queue'][state['index']]['id'], 'Q2')
        self.assertEqual(state['decisions'][0]['status'], 'unavailable')

    def test_probe_caps_and_interview_guide(self):
        self.study['method'] = 'interview'
        self.study['design']['interview_questions'] = [studio.question(q(), f'I{i}') for i in range(10)]
        state = studio.start(self.study, True)
        while state['status'] == 'active':
            state = self.answer(state, 'A concrete example from yesterday.', meta=FakeMeta())
        self.assertEqual(state['probes']['interview'], 3)
        self.assertEqual(len(state['responses']), 14)  # 10 base, 3 probes, correction
        self.assertEqual(state['probes']['survey'], 0)

    def test_store_rejects_duplicate_answer_and_published_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ResearchStore(Path(temp) / 'test.sqlite3')
            state = studio.start(self.study, True)
            store.put('studio_study', self.study['id'], self.study)
            with self.assertRaises(ValueError):
                store.put('studio_study', self.study['id'], self.study)
            store.put('studio_session', state['id'], state)
            updated = self.answer(state, 'A recent example')
            store.save_studio_session(updated, state['nonce'])
            with self.assertRaises(ValueError):
                store.save_studio_session(updated, state['nonce'])
            self.assertEqual(len(store.get('studio_session', state['id'])['responses']), 1)

    def test_report_requires_valid_sources_and_corrections(self):
        class Synthesis(FakeMeta):
            refs = ['S1:R1', 'S1:R10']
            def _structured(self, messages, name, schema):
                return {'overview': 'Exploratory account', 'next_research': ['Test switching effort'],
                        'findings': [{'finding': 'Familiarity may matter', 'evidence_ids': self.refs,
                          'alternative_explanation': 'Task requirements', 'behavioural_interpretation': 'Possible habit',
                          'recommendation': 'Test onboarding', 'limitation': 'One self-report'}]}
        state = studio.start(self.study, True)
        state = self.answer(state, 'A recent example')
        while state['status'] == 'active':
            correction = state['queue'][state['index']]['phase'] == 'correction'
            state = self.answer(state, 'Actually it was a one-off task.' if correction else None, skip=not correction)
        meta = Synthesis()
        result = studio.report(self.study, [state], meta)
        self.assertEqual(result['included'], 1)
        for refs in (['S1:R1'], ['S1:R2'], ['invented']):
            meta.refs = refs
            with self.assertRaises(ValueError):
                studio.report(self.study, [state], meta)

    def test_invalid_stimulus_and_hypothetical_label(self):
        with self.assertRaises(ValueError):
            studio.stimulus({'image': 'https://private/internal'})
        with self.assertRaises(ValueError):
            studio.question({**q('choice'), 'evidence_kind': 'reported_behaviour'}, 'Q1')

    def test_evidence_keeps_answer_options_and_stimulus_context(self):
        state = studio.start(self.study, True)
        state = self.answer(state, 'Yesterday I used it.')
        state = self.answer(state, 'Accuracy')
        packet = studio.evidence(state)
        self.assertEqual(packet[1]['options'], ['Accuracy', 'Familiarity', 'Neither'])
        self.assertEqual(packet[1]['question_type'], 'single')
        self.assertIn('stimulus_shown', packet[1])

    def test_empty_sessions_cannot_be_turned_into_findings(self):
        state = studio.start(self.study, True)
        while state['status'] == 'active':
            state = self.answer(state, skip=True)
        with self.assertRaisesRegex(ValueError, 'no answered questions'):
            studio.report(self.study, [state], FakeMeta())

    def test_model_receives_approved_stimulus_alongside_response_context(self):
        class Inspect(FakeMeta):
            def _structured(inner, messages, name, schema):
                self.assertEqual(messages[-1]['content'][1]['type'], 'image_url')
                self.assertIn('approved_stimulus_text', messages[-1]['content'][0]['text'])
                self.assertIn('Recent use', messages[-1]['content'][0]['text'])
                return super()._structured(messages, name, schema)
        self.study['stimulus'] = {'text': 'Fictional concept', 'image': 'data:image/png;base64,test-fixture'}
        state = self.answer(studio.start(self.study, True), 'An example', meta=Inspect())
        self.assertEqual(state['probes']['survey'], 1)

    def test_server_routes_preserve_drafts_publish_resume_and_reject_replays(self):
        from choicegap import server
        with tempfile.TemporaryDirectory() as temp:
            store = ResearchStore(Path(temp) / 'test.sqlite3')
            store.put('studio_study', 'draft', draft())
            handler = object.__new__(server.Handler)
            replies = []
            handler._json = lambda status, value: replies.append(value)
            with patch.object(server, 'STORE', store), patch.object(server, 'MetaClient', NoMeta):
                handler._studio_post('/api/studio/save', {'id': 'draft', 'design': draft()['design'],
                                                         'method': 'interview', 'recording': True})
                self.assertEqual(replies[-1]['method'], 'interview')
                self.assertTrue(replies[-1]['recording'])
                handler._studio_post('/api/studio/approve', {'id': 'draft', 'design': draft()['design'],
                    'confirmed': True, 'method': 'interview', 'recording': True})
                published = replies[-1]
                handler._studio_get('/api/studio/participant', {'id': [published['id']]})
                self.assertNotIn('hypotheses', replies[-1])
                self.assertNotIn('brief', replies[-1])
                handler._studio_post('/api/studio/start', {'study_id': published['id'], 'consent': True})
                pending = replies[-1]
                handler._studio_post('/api/studio/answer', {'id': pending['id'], 'nonce': pending['nonce'], 'skip': True})
                self.assertEqual(replies[-1]['answered'], 1)
                handler._studio_post('/api/studio/resume', {'id': pending['id']})
                self.assertEqual(replies[-1]['question']['id'], 'I2')
                with self.assertRaises(ValueError):
                    handler._studio_post('/api/studio/answer', {'id': pending['id'], 'nonce': pending['nonce'], 'skip': True})
                handler._studio_get('/api/studio/results', {'id': [published['id']]})
                self.assertEqual(replies[-1]['started'], 1)
                self.assertEqual(replies[-1]['completed'], 0)


if __name__ == '__main__':
    unittest.main()
