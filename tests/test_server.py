"""Exercise complete sessions through the request handlers without a network dependency."""

import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

from choicegap import server
from choicegap.engine import Session
from test_dynamic import DESIGN
from choicegap.dynamic import compile_study
from choicegap.research import EXAMPLE_EVIDENCE


class ServerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store_patch = patch.object(server, 'STORE', server.ResearchStore(Path(self.temp.name) / 'research.sqlite3'))
        self.store_patch.start()
        self.environment = patch.dict('os.environ', {'MODEL_API_KEY': ''})
        self.environment.start()
        for registry in (
            server.SESSIONS, server.PENDING, server.TRACES, server.USAGE,
            server.SESSION_STUDIES, server.STUDIES,
        ):
            registry.clear()
        server.COMPLETED.clear()
        self.handler = object.__new__(server.Handler)
        from types import SimpleNamespace
        self.handler.server = SimpleNamespace(server_port=8000)
        self.handler.headers = {'Host': '127.0.0.1:8000', 'Content-Type': 'application/json'}
        self.handler._json = lambda status, body: setattr(self, 'response', body)

    def tearDown(self):
        self.environment.stop()
        self.store_patch.stop()
        self.temp.cleanup()

    def test_participant_count_includes_optional_tasks_and_final_correction(self):
        from test_studio import draft
        from choicegap import studio
        study = studio.approve(draft(), {'confirmed': True, 'design': draft()['design'],
            'method': 'combined', 'recording': False, 'task_prompt': 'Optional fictional task'})
        study['comparisons'] = {'reviewed': True}
        server.STORE.put('studio_study', study['id'], study)
        self.handler.path = '/api/studio/participant?id=' + study['id']
        self.handler.do_GET()
        self.assertEqual(self.response['base_questions'], 7 + 2 + 1 + 3 + 1)

    def start(self, **overrides):
        payload = {'ratings': {'impact': 5, 'price': 3, 'convenience': 3, 'trust': 3}}
        payload.update(overrides)
        self.handler._start(payload)
        return self.response

    def answer(self, data, choice='a', **overrides):
        payload = {
            'session_id': self.token,
            'experiment_id': data['experiment']['id'],
            'answer_token': data['answer_token'],
            'choice': choice,
        }
        payload.update(overrides)
        self.handler._answer(payload)
        return self.response

    def test_full_session_records_pre_response_plans_and_holdout(self):
        data = self.start()
        self.token = data['session_id']
        for _ in range(4):
            data = self.answer(data)
        self.assertTrue(data['holdout'])
        session = server.SESSIONS[self.token]
        canonical = session.holdout_source['choice']
        displayed = ('b' if canonical == 'a' else 'a') if data['experiment']['flipped'] else canonical
        data = self.answer(data, displayed)
        self.assertTrue(data['done'])
        self.assertTrue(data['report']['holdout_consistent'])
        trace = data['report']['decision_trace']
        self.assertEqual(len(trace), 5)
        self.assertEqual(len(trace[0]['p_canonical_a_by_hypothesis']), 4)
        self.assertEqual(trace[0]['posterior_before'], {key: .25 for key in Session.create('impact', '').posterior})
        self.assertEqual(trace[-1]['posterior_before'], trace[-1]['posterior_after'])
        self.assertEqual(len(server.COMPLETED), 1)
        self.assertNotIn(self.token, server.SESSIONS)
        self.assertNotIn('statement', server.COMPLETED[0])

    def test_participant_session_makes_no_model_requests_even_when_configured(self):
        with patch.dict('os.environ', {'MODEL_API_KEY': 'test-not-a-real-key'}), patch.object(server.MetaClient, '_structured', side_effect=AssertionError('Participant loop must not call Muse')):
            data = self.start(statement='I care about lower emissions')
            self.token = data['session_id']
            for _ in range(4):
                data = self.answer(data)
            if data.get('holdout'):
                data = self.answer(data)
            self.assertTrue(data['done'])
            self.assertEqual(server.COMPLETED[0]['api_usage'], [])

    def test_replayed_answer_and_wrong_experiment_do_not_mutate_evidence(self):
        first = self.start()
        self.token = first['session_id']
        with self.assertRaises(ValueError):
            self.answer(first, experiment_id='invented')
        self.assertEqual(server.SESSIONS[self.token].rounds, 0)
        self.answer(first)
        before = dict(server.SESSIONS[self.token].posterior)
        with self.assertRaises(ValueError):
            self.answer(first)
        self.assertEqual(server.SESSIONS[self.token].rounds, 1)
        self.assertEqual(server.SESSIONS[self.token].posterior, before)

    def test_browser_cannot_change_orientation_or_finish_early(self):
        data = self.start()
        self.token = data['session_id']
        issued = data['experiment']
        self.answer(data, flipped=not issued['flipped'], holdout=True)
        session = server.SESSIONS[self.token]
        self.assertEqual(session.rounds, 1)
        self.assertEqual(session.history[0]['flipped'], issued['flipped'])
        self.assertFalse(self.response['done'])

    def test_all_outside_responses_finish_without_manufacturing_evidence(self):
        data = self.start()
        self.token = data['session_id']
        for _ in range(4):
            data = self.answer(data, 'outside')
        self.assertTrue(data['done'])
        self.assertEqual(data['report']['evidence_quality'], 'low')
        self.assertFalse(data['report']['gap_detected'])

    def test_missing_linked_study_fails_instead_of_switching_to_default(self):
        with self.assertRaises(ValueError):
            self.start(study_id='expired')

    def test_compiled_study_can_be_loaded_from_participant_link(self):
        server.STUDIES['test-study'] = compile_study(DESIGN)
        self.handler.path = '/api/study?id=test-study'
        self.handler.do_GET()
        self.assertEqual(self.response['study']['title'], DESIGN['title'])
        data = self.start(study_id='test-study', ratings={key: 3 for key in 'abcd'})
        self.assertEqual(data['study_title'], DESIGN['title'])
        self.assertEqual(set(data['posterior']), set('abcd'))

    def test_tied_stated_priorities_cannot_manufacture_a_gap(self):
        session = Session.create('impact', '', stated_ratings={
            'impact': 5, 'price': 5, 'convenience': 2, 'trust': 2,
        })
        for _ in range(4):
            session.observe('impact-v-price', 'b', False)
        session.holdout_consistent = True
        report = session.report()
        self.assertEqual(report['leading_driver'], 'price')
        self.assertEqual(report['stated_priorities'], ['impact', 'price'])
        self.assertFalse(report['gap_detected'])

    def test_consistent_answers_without_a_clear_leader_do_not_claim_alignment(self):
        session = Session.create('impact', '')
        for _ in range(4):
            session.observe('impact-v-price', 'a', False)
        session.posterior = {'impact': .25, 'price': .25, 'convenience': .25, 'trust': .25}
        session.holdout_consistent = True
        report = session.report()
        self.assertFalse(report['gap_detected'])
        self.assertIn('do not yet distinguish', report['headline'])
        client = server.MetaClient()
        client.api_key = 'test-only'
        narrative = client.narrate_report(report)
        self.assertEqual(narrative['source'], 'quality-guardrail')

    def test_research_routes_publish_and_restore_approved_workspace(self):
        self.handler.path = '/api/research/draft'
        self.handler._body = lambda: {
            'decision': 'Which change should we test for lower-impact delivery adoption?',
            'evidence': EXAMPLE_EVIDENCE, 'example': True,
        }
        self.handler.do_POST()
        draft = self.response
        self.assertEqual(draft['status'], 'draft')
        self.assertEqual(draft['evidence_origin'], 'fictional-example')
        self.handler.path = '/api/study?id=' + draft['id']
        self.handler.do_GET()
        self.assertIn('error', self.response)
        self.handler.path = '/api/research/approve'
        self.handler._body = lambda: {
            'id': draft['id'], 'blueprint': draft['blueprint'],
            'mapping': draft['mapping'], 'confirmed': True,
        }
        self.handler.do_POST()
        self.assertEqual(self.response['status'], 'approved')
        server.STUDIES.clear()
        self.handler.path = '/api/study?id=' + draft['id']
        self.handler.do_GET()
        self.assertEqual(self.response['study']['title'], 'Sustainable grocery delivery')
        data = self.start(study_id=draft['id'], ratings={key: 3 for key in 'abcd'})
        self.token = data['session_id']
        for _ in range(4):
            data = self.answer(data, 'outside')
        self.handler.path = '/api/research/report?id=' + draft['id']
        self.handler.do_GET()
        self.assertEqual(self.response['completed_sessions'], 1)
        self.assertEqual(self.response['response_checks_passed'], 0)
        self.assertEqual(len(self.response['field_tests']), 4)

    def test_design_review_endpoint_persists_only_validated_review(self):
        from choicegap.research import draft_workspace
        from test_review import fixture_review

        class Reviewer:
            enabled = True
            model = 'test-only-reviewer'
            usage = []

            def review_stage(self, *args):
                result = fixture_review()
                result['findings'][0]['topic'] = 'level_wording'
                return result

        draft = draft_workspace('Which delivery change should we test?', EXAMPLE_EVIDENCE, server.MetaClient())
        server.STORE.put('workspace', draft['id'], draft)
        self.handler.path = '/api/research/review'
        self.handler._body = lambda: {
            'id': draft['id'], 'blueprint': draft['blueprint'], 'mapping': draft['mapping'],
        }
        with patch.object(server, 'MetaClient', return_value=Reviewer()):
            self.handler.do_POST()
        self.assertEqual(self.response['design_review']['source'], 'test-only-reviewer')
        saved = server.STORE.get('workspace', draft['id'])
        self.assertTrue(saved['design_review_current'])
        self.assertEqual(saved['status'], 'draft')


if __name__ == '__main__':
    unittest.main()
