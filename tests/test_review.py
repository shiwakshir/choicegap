import base64
import copy
import json
import unittest
from unittest.mock import patch

from choicegap.meta import MetaClient
from choicegap.research import EXAMPLE_EVIDENCE, approve_workspace, draft_workspace
from choicegap.review import prototype_metadata, review_workspace, validate_review


PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg=='


class OfflineMeta:
    enabled = False
    usage = []


def fixture_review():
    return {
        'summary': 'Window precision and delivery speed should be treated separately.',
        'findings': [{
            'account': 'c', 'basis': 'proposed_design', 'source_ids': [], 'quote': '',
            'observation': 'The delivery-window factor varies precision.',
            'alternative_explanation': 'A respondent may be reacting to scheduling certainty rather than speed.',
            'suggested_control': 'Keep delivery date fixed and vary only window length.',
        }],
        'unresolved': ['The prototype may expose availability constraints that the source excerpts omit.'],
    }


class ReviewTests(unittest.TestCase):
    def workspace(self):
        return draft_workspace('Which delivery intervention should we test next?', EXAMPLE_EVIDENCE, OfflineMeta())

    def test_remote_urls_invalid_base64_and_mismatched_image_types_are_rejected(self):
        for value in ('https://example.com/private.png', 'data:image/png;base64,???',
                      'data:image/png;base64,' + base64.b64encode(b'not-a-png').decode()):
            with self.assertRaises(ValueError):
                prototype_metadata(value)
        metadata = prototype_metadata(PNG)
        self.assertEqual(metadata['mime_type'], 'image/png')
        self.assertEqual(len(metadata['sha256']), 64)

    def test_model_cannot_claim_to_have_seen_an_absent_image(self):
        result = fixture_review()
        result['findings'][0]['basis'] = 'prototype_image'
        with self.assertRaises(ValueError):
            validate_review(result, self.workspace()['sources'], has_image=False)

    def test_text_findings_require_verbatim_grounded_citations(self):
        workspace = self.workspace()
        result = fixture_review()
        finding = result['findings'][0]
        finding.update(basis='source_text', source_ids=['S1'], quote='Invented quote')
        with self.assertRaises(ValueError):
            validate_review(result, workspace['sources'], has_image=False)
        finding['quote'] = workspace['sources'][0]['text']
        self.assertEqual(validate_review(result, workspace['sources'], False), result)

    def test_review_saves_digest_and_findings_without_image_bytes(self):
        workspace = self.workspace()

        class Reviewer:
            enabled = True
            model = 'test-only-muse'
            usage = [{'task': 'critical_design_review', 'usage': {'total_tokens': 10}}]

            def review_stage(self, *args):
                if args[-1]:
                    self.received_image = args[-1]
                result = fixture_review()
                result['findings'][0]['topic'] = 'level_wording'
                return result

        reviewer = Reviewer()
        reviewed = review_workspace(workspace, workspace['blueprint'], workspace['mapping'], PNG, reviewer)
        self.assertEqual(reviewer.received_image, PNG)
        self.assertNotIn(PNG, json.dumps(reviewed))
        self.assertTrue(reviewed['design_review_current'])
        approved = approve_workspace(reviewed, reviewed['blueprint'], reviewed['mapping'], True)
        self.assertTrue(approved['design_review_current'])
        revised = copy.deepcopy(reviewed['blueprint'])
        revised['attributes'][1]['low_label'] = '£2 delivery fee'
        changed = approve_workspace(reviewed, revised, reviewed['mapping'], True)
        self.assertFalse(changed['design_review_current'])

    def test_offline_mode_does_not_fabricate_a_model_review(self):
        workspace = self.workspace()
        with self.assertRaises(ValueError):
            review_workspace(workspace, workspace['blueprint'], workspace['mapping'], None, OfflineMeta())

    def test_image_is_sent_as_native_user_content_with_structured_output(self):
        client = MetaClient()
        client.api_key = 'test-only'
        workspace = self.workspace()
        with patch.object(client, '_structured', return_value=fixture_review()) as call:
            client.challenge_research_design(
                workspace['decision'], workspace['sources'], workspace['mapping'],
                workspace['blueprint'], {'passed': True}, PNG,
            )
        messages, task, schema = call.call_args.args
        self.assertEqual(task, 'critical_design_review')
        self.assertEqual(messages[1]['role'], 'user')
        self.assertEqual(messages[1]['content'][1], {'type': 'image_url', 'image_url': {'url': PNG}})
        self.assertFalse(schema['additionalProperties'])

    def test_wire_request_enables_strict_schema_and_review_reasoning(self):
        client = MetaClient()
        client.api_key = 'test-only'
        workspace = self.workspace()
        payload = {'choices': [{'message': {'content': json.dumps(fixture_review())}}], 'usage': {'total_tokens': 123}}
        with patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode('utf-8')
            client.challenge_research_design(
                workspace['decision'], workspace['sources'], workspace['mapping'],
                workspace['blueprint'], {'passed': True}, PNG,
            )
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(body['model'], 'muse-spark-1.3')
        self.assertEqual(body['reasoning_effort'], 'high')
        self.assertTrue(body['response_format']['json_schema']['strict'])
        self.assertEqual(client.usage[0]['usage']['total_tokens'], 123)


if __name__ == '__main__':
    unittest.main()
