import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from choicegap.dynamic import compile_study
from choicegap.research import (
    EXAMPLE_EVIDENCE, ResearchStore, approve_workspace, decision_report,
    draft_workspace, local_map, parse_evidence, validate_map, prepared_delivery_study,
)


class OfflineMeta:
    enabled = False
    usage = []


class ResearchWorkflowTests(unittest.TestCase):
    def test_prepared_study_does_not_invent_prior_research_or_bypass_approval(self):
        draft = prepared_delivery_study()
        self.assertEqual(draft['sources'], [])
        self.assertEqual(draft['api_usage'], [])
        self.assertEqual(draft['status'], 'draft')
        self.assertEqual(draft['blueprint']['title'], 'Grocery delivery preferences')
        self.assertEqual(draft['evidence_origin'], 'new-study-no-prior-data')
        self.assertTrue(all(not a['references'] for a in draft['mapping']['accounts']))
        with self.assertRaises(ValueError): approve_workspace(draft, draft['blueprint'], draft['mapping'], False)
        approved = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        self.assertEqual(approved['status'], 'approved')
        self.assertEqual(approved['blueprint']['experience_version'], 2)
        self.assertEqual(decision_report(approved, [])['completed_sessions'], 0)

    def draft(self):
        return draft_workspace('Which change should improve lower-impact grocery delivery adoption?', EXAMPLE_EVIDENCE, OfflineMeta())

    def test_import_preserves_source_types_and_does_not_match_participants(self):
        sources = parse_evidence(EXAMPLE_EVIDENCE)
        self.assertEqual([item['id'] for item in sources], ['S1', 'S2', 'S3', 'S4', 'S5'])
        self.assertEqual(sources[1]['kind'], 'observed')
        self.assertEqual(sources[4]['kind'], 'hypothetical')
        self.assertNotIn('participant_id', sources[0])

    def test_local_draft_does_not_claim_automatic_semantic_mapping(self):
        draft = self.draft()
        self.assertEqual(draft['source'], 'local-unmapped')
        self.assertTrue(all(not account['references'] for account in draft['mapping']['accounts']))

    def test_invalid_model_citation_falls_back_without_losing_sources(self):
        class FaultyMeta:
            enabled = True
            model = 'test-model'
            usage = []

            def map_research_evidence(self, decision, sources):
                mapping = local_map(sources)
                mapping['accounts'][0]['references'] = [{
                    'source_id': 'invented', 'quote': 'Fabricated evidence', 'relation': 'supports',
                }]
                return mapping

        workspace = draft_workspace('Which delivery change should we test next?', EXAMPLE_EVIDENCE, FaultyMeta())
        self.assertEqual(workspace['source'], 'local-unmapped')
        self.assertEqual(len(workspace['sources']), 5)
        self.assertTrue(workspace['warning'])
        self.assertFalse(workspace['mapping']['accounts'][0]['references'])

    def test_field_plan_keeps_lower_impact_claim_fixed_for_cost_test(self):
        draft = self.draft()
        approved = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        cost = next(test for test in approved['field_tests'] if test['account'] == 'b')
        self.assertEqual(cost['baseline']['a'], draft['blueprint']['attributes'][0]['high_label'])
        self.assertEqual(cost['baseline']['a'], cost['intervention']['a'])

    def test_fabricated_source_and_misquoted_evidence_are_rejected(self):
        sources = parse_evidence(EXAMPLE_EVIDENCE)
        for reference in (
            {'source_id': 'S999', 'quote': sources[0]['text'], 'relation': 'supports'},
            {'source_id': 'S1', 'quote': 'The user always chooses free delivery.', 'relation': 'supports'},
        ):
            mapping = local_map(sources)
            mapping['accounts'][0]['references'] = [reference]
            with self.assertRaises(ValueError):
                validate_map(mapping, sources)

    def test_source_kind_is_attached_from_original_not_model(self):
        sources = parse_evidence(EXAMPLE_EVIDENCE)
        mapping = local_map(sources)
        mapping['accounts'][0]['references'] = [{
            'source_id': 'S1', 'quote': sources[0]['text'], 'relation': 'context', 'source_kind': 'observed',
        }]
        mapped = validate_map(mapping, sources)
        self.assertEqual(mapped['accounts'][0]['references'][0]['source_kind'], 'statement')

    def test_approval_requires_confirmation_and_locks_design(self):
        draft = self.draft()
        with self.assertRaises(ValueError):
            approve_workspace(draft, draft['blueprint'], draft['mapping'], False)
        approved = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        self.assertEqual(len(approved['design_sha256']), 64)
        self.assertEqual(len(compile_study(approved['blueprint']).experiments), 6)
        with self.assertRaises(ValueError):
            approve_workspace(approved, approved['blueprint'], approved['mapping'], True)

    def test_every_field_contrast_changes_exactly_one_factor(self):
        draft = self.draft()
        approved = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        for contrast in approved['field_tests']:
            changes = [key for key in contrast['baseline'] if contrast['baseline'][key] != contrast['intervention'][key]]
            self.assertEqual(changes, [contrast['account']])
            self.assertEqual(len(contrast['held_constant']), 3)

    def test_revised_levels_change_design_digest(self):
        draft = self.draft()
        first = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        changed = copy.deepcopy(draft['blueprint'])
        changed['attributes'][1]['low_label'] = '£2 delivery fee'
        second = approve_workspace(draft, changed, draft['mapping'], True)
        self.assertNotEqual(first['design_sha256'], second['design_sha256'])

    def test_workspace_survives_reopening_store_and_approved_design_cannot_be_overwritten(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'research.sqlite3'
            draft = self.draft()
            first = ResearchStore(path)
            first.put('workspace', draft['id'], draft)
            second = ResearchStore(path)
            restored = second.get('workspace', draft['id'])
            self.assertEqual(restored, draft)
            approved = approve_workspace(restored, restored['blueprint'], restored['mapping'], True)
            second.put('workspace', approved['id'], approved)
            with self.assertRaises(ValueError):
                first.put('workspace', approved['id'], draft)

    def test_study_report_excludes_other_studies_and_low_quality_leaders(self):
        draft = self.draft()
        approved = approve_workspace(draft, draft['blueprint'], draft['mapping'], True)
        records = [
            {'study_id': approved['id'], 'evidence_quality': 'high', 'report': {'confidence': .8, 'leading_driver': 'b'}},
            {'study_id': approved['id'], 'evidence_quality': 'low', 'report': {'confidence': .9, 'leading_driver': 'a'}},
            {'study_id': 'other', 'evidence_quality': 'high', 'report': {'confidence': .9, 'leading_driver': 'a'}},
        ]
        report = decision_report(approved, records)
        self.assertEqual(report['completed_sessions'], 2)
        self.assertEqual(report['response_checks_passed'], 1)
        self.assertEqual(report['session_leader_counts']['b'], 1)
        self.assertEqual(report['session_leader_counts']['a'], 0)


if __name__ == '__main__':
    unittest.main()
