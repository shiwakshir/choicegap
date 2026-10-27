import copy
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from choicegap.workbench_benchmark import run_benchmark, simulate, summarize
from choicegap.review_benchmark import screen_score, digest
from choicegap.review_benchmark import prepare, run, load_protocol, summarize as summarize_review
from choicegap.config import load_env_file
from choicegap.meta import MetaClient
from choicegap.dynamic import DynamicSession, compile_study
from choicegap.research import default_blueprint


class WorkbenchEvaluationTests(unittest.TestCase):
    def test_shipped_engine_simulation_is_repeatable_and_counts_repeat(self):
        first = run_benchmark(20, 51)
        self.assertEqual(first, run_benchmark(20, 51))
        for population in first['populations'].values():
            self.assertEqual(population['adaptive']['total_questions_including_repeat'], 5)
            self.assertEqual(population['all_six']['total_questions_including_repeat'], 7)
            for result in population.values():
                self.assertGreaterEqual(result['null_mismatch_rate_all'], 0)
                self.assertLessEqual(result['null_mismatch_rate_all'], 1)

    def test_benchmark_calls_dynamic_observer_with_every_unique_pair(self):
        original = DynamicSession.observe
        issued = []
        def observe(session, identifier, answer, flipped):
            issued.append(identifier)
            return original(session, identifier, answer, flipped)
        with patch.object(DynamicSession, 'observe', observe):
            simulate('all_six', 'mixed_dominant', 23)
        self.assertEqual(len(set(issued)), 6)

    def test_response_failure_and_weak_separation_are_distinct(self):
        rows = [dict(passed=False, probability=.95, leader_differs=True, correct=False, brier=.4, questions=5),
                dict(passed=True, probability=.3, leader_differs=True, correct=False, brier=.2, questions=5)]
        result = summarize(rows, .45)
        self.assertEqual(result['null_mismatch_rate_all'], 0)
        self.assertEqual(result['response_check_inconclusive_rate'], .5)
        self.assertEqual(result['weak_separation_among_passing'], 1)

    def test_reports_cannot_claim_verified_gap_even_with_confident_disagreement(self):
        study = compile_study(default_blueprint())
        session = DynamicSession.create(study, 'a', '')
        session.posterior = {'a': .01, 'b': .97, 'c': .01, 'd': .01}
        session.history = [{'choice': 'a'}] * 4
        session.holdout_consistent = True
        report = session.report()
        self.assertFalse(report['gap_detected'])
        self.assertTrue(report['rating_choice_mismatch'])
        self.assertIn('£3', report['headline'])
        self.assertIn('Free delivery', report['headline'])
        self.assertEqual(len(report['tested_levels']), 4)

    def test_proxy_requires_visual_basis_and_clean_findings_count_as_alarm(self):
        review = {'findings': [{'basis': 'proposed_design', 'observation': 'A preselected default', 'suggested_control': 'Remove the default'}]}
        self.assertFalse(screen_score(review, {'expected': 'default'})['proxy_detection'])
        review['findings'][0]['basis'] = 'prototype_image'
        self.assertTrue(screen_score(review, {'expected': 'default'})['proxy_detection'])
        self.assertTrue(screen_score(review, {'expected': 'clean'})['clean_alarm'])
        self.assertFalse(screen_score({'findings': []}, {'expected': 'clean'})['clean_alarm'])

    def test_protocol_digest_detects_changed_labels(self):
        protocol = {'cases': [{'id': '01', 'expected': 'clean'}]}
        changed = copy.deepcopy(protocol)
        changed['cases'][0]['expected'] = 'default'
        self.assertNotEqual(digest(protocol), digest(changed))

    def test_local_config_only_reads_supported_keys_and_respects_environment(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'MODEL_API_KEY': 'existing'}):
            path = Path(directory) / '.env'
            path.write_text('MODEL_API_KEY="local-test"\nMETA_MODEL=test-model\nUNSUPPORTED_CONFIG_KEY=ignored\n', encoding='utf-8')
            load_env_file(path)
            self.assertEqual(os.environ['MODEL_API_KEY'], 'existing')
            self.assertNotIn('UNSUPPORTED_CONFIG_KEY', os.environ)
            load_env_file(path, overwrite=True)
            self.assertEqual(os.environ['MODEL_API_KEY'], 'local-test')

    def test_evaluation_freezes_screens_and_resumes_without_repeating_calls(self):
        try:
            import PIL  # Evaluation-only renderer dependency.
        except ImportError:
            self.skipTest('Install Pillow to test evaluation preparation')
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'MODEL_API_KEY': 'test-only-key', 'META_MODEL': 'test-only-model'}):
            root = Path(directory)
            protocol = prepare(root)
            self.assertEqual(len(protocol['payload']['cases']), 18)
            seen = []
            def fake(client, messages, name, schema):
                seen.append(messages)
                return {'summary': 'Fixture only', 'findings': [], 'unresolved': []}
            with patch.object(MetaClient, '_structured', fake):
                run(root, maximum=2, workers=2)
                run(root, maximum=1, workers=1)
            rows = [json.loads(s) for s in (root / 'calls.jsonl').read_text().splitlines()]
            self.assertEqual(len({r['id'] for r in rows}), 3)
            self.assertEqual(len(seen), 3)
            for messages in seen:
                content = messages[-1]['content']
                context = json.loads(content[0]['text'] if isinstance(content, list) else content)
                self.assertNotIn('expected', context)
                self.assertNotIn('target_side', context)
                self.assertEqual(len(context['compiled_experiments']), 6)
            summary = summarize_review(root)
            self.assertEqual(summary['recorded_calls'], 3)
            self.assertEqual(sum(c['primary_adjudicated_calls'] for c in summary['conditions'].values()), 0)
            (root / 'case-01.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                load_protocol(root)

    def test_validation_failures_keep_raw_response_and_denominator(self):
        try:
            import PIL
        except ImportError:
            self.skipTest('Install Pillow to test evaluation preparation')
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'MODEL_API_KEY': 'test-only-key'}):
            root = Path(directory)
            prepare(root)
            with patch.object(MetaClient, '_structured', return_value={'summary': 'invalid fixture', 'findings': [{}], 'unresolved': []}):
                result = run(root, maximum=1)
            row = json.loads((root / 'calls.jsonl').read_text())
            self.assertEqual(row['status'], 'validation_error')
            self.assertIn('raw_response', row)
            self.assertEqual(result['recorded_calls'], 1)
            self.assertEqual(sum(c['validation_failures'] for c in result['conditions'].values()), 1)
