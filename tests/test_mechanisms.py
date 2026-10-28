import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from choicegap import mechanisms as m, server
from choicegap.meta import MetaClient
from choicegap.research import ResearchStore, draft_workspace, EXAMPLE_EVIDENCE
from choicegap.mechanism_benchmark import run_benchmark


class Offline:
    enabled, usage = False, []


class MechanismTests(unittest.TestCase):
    def workspace(self):
        return draft_workspace('Which delivery mechanism should we investigate?', EXAMPLE_EVIDENCE, Offline())

    def study(self, key='default'):
        w = self.workspace()
        return m.approve_study(w, m.manual_plan(w), key, True)

    def test_protocols_change_only_the_declared_fields(self):
        for key in m.CATALOG:
            p = m.protocol(key)
            self.assertTrue(p['audit']['passed'])
            changed = copy.deepcopy(p)
            changed['arms'][1]['a']['fee'] = '£8'
            self.assertFalse(m.audit_protocol(changed)['passed'])
        self.assertEqual(len(m.protocol('credibility')['arms']), 4)

    def test_default_assignment_keeps_preselection_with_canonical_option_after_flip(self):
        study = self.study()
        first = m.assignment(study, 'focal_default', False)
        flipped = m.assignment(study, 'focal_default', True)
        self.assertEqual(first['stimulus']['default'], 'a')
        self.assertEqual(flipped['stimulus']['default'], 'b')
        self.assertEqual(first['stimulus']['a'], flipped['stimulus']['b'])
        self.assertEqual(m.assignment(study, 'active', True)['stimulus']['default'], None)

    def test_approval_and_source_quotes_are_checked(self):
        w = self.workspace()
        with self.assertRaises(ValueError):
            m.approve_study(w, m.manual_plan(w), 'default', False)
        p = m.manual_plan(w)
        p['accounts'][0]['references'] = [{'source_id': 'S1', 'quote': 'Invented', 'relation': 'supports'}]
        with self.assertRaises(ValueError):
            m.approve_study(w, p, 'default', True)
        p['accounts'][0]['references'][0]['quote'] = 'lower-impact delivery option'
        approved = m.approve_study(w, p, 'default', True)
        self.assertEqual(approved['account']['references'][0]['source_kind'], 'statement')

    def test_canonical_response_is_durable_and_cannot_be_replayed(self):
        with TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / 'data.sqlite3')
            row = m.assignment(self.study(), 'standard_default', True)
            store.put('mechanism_assignment', row['id'], row)
            with self.assertRaises(ValueError):
                store.answer_mechanism(row['id'], 'wrong-token', 'a')
            saved = store.answer_mechanism(row['id'], row['answer_token'], 'a')
            self.assertEqual(saved['choice'], 'b')
            self.assertNotIn('answer_token', saved)
            reopened = ResearchStore(store.path)
            self.assertEqual(reopened.get('mechanism_assignment', row['id'])['choice'], 'b')
            with self.assertRaises(ValueError):
                reopened.answer_mechanism(row['id'], row['answer_token'], 'b')

    def test_concurrent_answer_records_exactly_one_outcome(self):
        with TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / 'data.sqlite3')
            row = m.assignment(self.study())
            store.put('mechanism_assignment', row['id'], row)
            def answer(_):
                try:
                    store.answer_mechanism(row['id'], row['answer_token'], 'a')
                    return True
                except ValueError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sum(pool.map(answer, range(2))), 1)

    def test_approved_mechanism_protocol_is_immutable(self):
        with TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / 'data.sqlite3')
            study = self.study()
            store.put('mechanism_study', study['id'], study)
            with self.assertRaises(ValueError):
                store.put('mechanism_study', study['id'], {**study, 'status': 'draft'})

    def test_missing_responses_are_not_imputed_as_rejections_or_exposed_as_tokens(self):
        study = self.study('planning')
        a = m.assignment(study, 'advance', False)
        b = m.assignment(study, 'later', False)
        b.update(status='completed', choice='a')
        result = m.report(study, [a, b])
        self.assertEqual(result['arms']['advance']['assigned'], 1)
        self.assertEqual(result['arms']['advance']['completed'], 0)
        self.assertEqual(result['arms']['advance']['missing'], 1)
        self.assertIsNone(result['contrast']['estimate'])
        self.assertNotIn(a['answer_token'], json.dumps(result))

    def test_one_respondent_per_arm_does_not_establish_a_mechanism(self):
        cells = {'a': {'completed': 1, 'a': 1}, 'b': {'completed': 1, 'a': 0}}
        c = m.contrast(cells, {'a': 1, 'b': -1})
        self.assertLessEqual(c['lower'], 0)
        self.assertGreaterEqual(c['upper'], 0)

    def test_factorial_contrast_distinguishes_general_endorsement_from_interaction(self):
        result = run_benchmark(per_arm=1000)
        claim = result['scenarios']['benefit_specific_credibility']
        rival = result['scenarios']['general_endorsement_rival']
        self.assertGreater(claim['lower'], 0)
        self.assertLessEqual(rival['lower'], 0)
        self.assertGreaterEqual(rival['upper'], 0)
        self.assertTrue(all(r['contains_generating_contrast'] for r in result['scenarios'].values()))
        self.assertEqual(run_benchmark(20), run_benchmark(20))

    def test_muse_plan_uses_catalogue_and_strict_source_schema(self):
        w = self.workspace()
        client = MetaClient()
        with patch.object(client, '_structured', return_value=m.manual_plan(w)) as call:
            client.propose_mechanisms(w['decision'], w['sources'], list(m.CATALOG.values()))
        messages, task, schema = call.call_args.args
        self.assertEqual(task, 'behavioural_mechanism_plan')
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['properties']['accounts']['minItems'], 3)
        self.assertIn('unobserved psychological mediator', messages[0]['content'])

    def test_http_handlers_do_not_accept_client_arm_or_orientation_or_call_muse(self):
        with TemporaryDirectory() as directory, patch.object(server, 'STORE', ResearchStore(Path(directory) / 'data.sqlite3')):
            study = self.study()
            server.STORE.put('mechanism_study', study['id'], study)
            handler = object.__new__(server.Handler)
            responses = []
            handler._json = lambda code, body: responses.append(body)
            with patch.object(MetaClient, '_structured', side_effect=AssertionError('No participant model calls')):
                handler._mechanism_post('/api/mechanisms/start', {'study_id': study['id'], 'consent': True, 'arm_id': 'invented', 'flipped': 'invented'})
                data = responses[-1]
                saved = server.STORE.get('mechanism_assignment', data['id'])
                self.assertIn(saved['arm_id'], {a['id'] for a in study['protocol']['arms']})
                self.assertIsInstance(saved['flipped'], bool)
                handler._mechanism_post('/api/mechanisms/answer', {'id': data['id'], 'answer_token': data['answer_token'], 'choice': 'outside'})
                self.assertTrue(responses[-1]['done'])
            with self.assertRaises(ValueError):
                handler._mechanism_post('/api/mechanisms/start', {'study_id': study['id'], 'consent': False})


if __name__ == '__main__':
    unittest.main()
