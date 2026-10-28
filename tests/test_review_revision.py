import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from choicegap.dynamic import DynamicSession, compile_study
from choicegap.meta import MetaClient
from choicegap.research import default_blueprint, draft_workspace, decision_report, EXAMPLE_EVIDENCE
from choicegap.review import review_workspace
from choicegap.review_prompts import REVIEW_PROMPTS
from choicegap.neutral_review_benchmark import prepare, load, run
from test_review import PNG, OfflineMeta, fixture_review


class RevisionTests(unittest.TestCase):
    def test_staged_wire_keeps_design_text_only_and_screen_multimodal(self):
        workspace = draft_workspace('Which delivery feature should we study?', EXAMPLE_EVIDENCE, OfflineMeta())
        client = MetaClient()
        with patch.object(client, '_structured', return_value=dict(summary='test-only', findings=[], unresolved=[])) as request:
            client.review_stage(workspace['decision'], workspace['sources'], workspace['mapping'], workspace['blueprint'], {}, 'design')
            messages, task, schema = request.call_args.args
            self.assertEqual(task, 'semantic_design_review')
            self.assertIsInstance(messages[1]['content'], str)
            self.assertIn('topic', schema['properties']['findings']['items']['required'])
            client.review_stage(workspace['decision'], workspace['sources'], workspace['mapping'], workspace['blueprint'], {}, 'screen', PNG)
            messages, task, schema = request.call_args.args
            self.assertEqual(task, 'visual_context_review')
            self.assertEqual(messages[1]['content'][1]['image_url']['url'], PNG)
            with self.assertRaises(ValueError):
                client.review_stage(workspace['decision'], workspace['sources'], workspace['mapping'], workspace['blueprint'], {}, 'design', PNG)

    def test_opening_ties_cover_all_pairs_and_are_reproducible(self):
        study = compile_study(default_blueprint())
        choices = [DynamicSession.create(study, 'a', '', seed=i).next_experiment()['id'] for i in range(120)]
        self.assertEqual(set(choices), {e.id for e in study.experiments})
        self.assertEqual(choices, [DynamicSession.create(study, 'd', '', seed=i).next_experiment()['id'] for i in range(120)])

    def test_repeat_selection_is_independent_of_leader_and_not_always_first(self):
        study = compile_study(default_blueprint())
        selected = set()
        for seed in range(20):
            session = DynamicSession.create(study, 'a', '', seed=seed)
            for e in study.experiments[:4]:
                session.observe(e.id, 'a', False)
            first = session.holdout_experiment()
            session.posterior = dict(a=.01, b=.01, c=.01, d=.97)
            self.assertEqual(first, session.holdout_experiment())
            selected.add(first['id'])
        self.assertGreater(len(selected), 1)

    def test_repeat_disagreement_never_changes_coverage_or_headline(self):
        session = DynamicSession.create(compile_study(default_blueprint()), 'a', '', seed=1)
        for _ in range(4):
            e = session.next_experiment()
            session.observe(e['id'], 'b', e['flipped'])
        session.holdout_consistent = True
        first = session.report()
        session.holdout_consistent = False
        second = session.report()
        self.assertEqual(first['evidence_quality'], second['evidence_quality'])
        self.assertEqual(first['headline'], second['headline'])
        self.assertNotIn('ratings', second['headline'])
        self.assertNotIn('mismatch', second['headline'])

    def test_primary_task_shares_use_canonical_choices_separate_denominators_and_all_sessions(self):
        workspace = draft_workspace('Which delivery feature should we study?', EXAMPLE_EVIDENCE, OfflineMeta())
        workspace['status'] = 'approved'
        records = []
        for index, choice in enumerate(('a', 'b', 'outside')):
            records.append({'study_id': workspace['id'], 'evidence_quality': 'low', 'informative_choices': 1,
                            'holdout_consistent': False,
                            'choices': [{'experiment_id': 'e1', 'choice': choice, 'flipped': True},
                                        {'experiment_id': 'e1', 'choice': 'b', 'holdout': True}],
                            'report': {'confidence': .8, 'leading_driver': 'a'}})
        report = decision_report(workspace, records)
        task = report['pairwise_choices'][0]
        self.assertEqual(task['counts'], dict(a=1, b=1, outside=1))
        self.assertEqual(task['exposures_with_recorded_response'], 3)
        self.assertEqual(task['informative_responses'], 2)
        self.assertEqual(task['canonical_a_share_among_ab'], .5)
        self.assertIsNone(report['pairwise_choices'][1]['canonical_a_share_among_ab'])
        self.assertEqual(report['repeat_agreement']['inconsistent'], 3)

    def test_clean_screen_cannot_suppress_design_findings(self):
        workspace = draft_workspace('Which delivery feature should we study?', EXAMPLE_EVIDENCE, OfflineMeta())
        received = []
        class Reviewer:
            enabled, model, usage = True, 'test-only', []
            def review_stage(self, decision, sources, mapping, blueprint, audit, stage, image):
                received.append((stage, image))
                if stage == 'screen':
                    return dict(summary='No visible issue', findings=[], unresolved=[])
                result = fixture_review()
                result['findings'][0]['topic'] = 'level_wording'
                return result
        result = review_workspace(workspace, workspace['blueprint'], workspace['mapping'], PNG, Reviewer())['design_review']
        self.assertEqual(received.count(('design', None)), 3)
        self.assertIn(('screen', PNG), received)
        self.assertEqual(len(result['findings']), 3)
        frequency = next(f for f in result['topic_frequency'] if f['topic'] == 'level_wording')
        self.assertEqual((frequency['raised_in'], frequency['completed_runs']), (3, 3))

    def test_failed_design_runs_are_visible_and_not_counted_as_agreement(self):
        workspace = draft_workspace('Which delivery feature should we study?', EXAMPLE_EVIDENCE, OfflineMeta())
        class Reviewer:
            enabled, model, usage = True, 'test-only', []
            def review_stage(self, *args):
                raise RuntimeError('test-only failure')
        result = review_workspace(workspace, workspace['blueprint'], workspace['mapping'], None, Reviewer())['design_review']
        self.assertEqual(len(result['runs']), 3)
        self.assertTrue(all(run['status'] == 'error' for run in result['runs']))
        self.assertTrue(all(f['completed_runs'] == 0 for f in result['topic_frequency']))

    def test_neutral_protocol_hides_labels_and_freezes_images(self):
        try:
            import PIL
        except ImportError:
            self.skipTest('Pillow is evaluation-only')
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'MODEL_API_KEY': 'test-only', 'META_MODEL': 'test-only'}):
            root = Path(directory)
            prepare(root)
            seen = []
            def fake(client, messages, task, schema):
                seen.append(messages)
                return dict(summary='test-only', findings=[], unresolved=[])
            with patch.object(MetaClient, '_structured', fake):
                first = run(root, maximum=2, workers=2)
                second = run(root, maximum=1, workers=1)
            self.assertEqual(first['calls'], 2)
            self.assertEqual(second['calls'], 3)
            for messages in seen:
                content = messages[1]['content']
                context = json.loads(content[0]['text'] if isinstance(content, list) else content)
                self.assertNotIn('feature', context)
                self.assertNotIn('side', context)
            for term in ('scarcity', 'social proof', 'anchor', 'leaf', 'fact order', 'low contrast'):
                self.assertNotIn(term, REVIEW_PROMPTS['screen'].lower())
            (root / 'neutral-01.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                load(root)
