import base64
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from choicegap import studio, studio_capabilities as cap, voice_stream
from choicegap.research import ResearchStore
try:
    from test_studio import draft, NoMeta, FakeMeta
except ImportError:
    from tests.test_studio import draft, NoMeta, FakeMeta


def plan():
    return {'context':'Fictional AI assistant options for an everyday task.', 'prompt':'Which would you choose?',
        'a_title':'Familiar assistant','b_title':'New assistant',
        'factors':[{'name':'Setup','a':'No new setup','b':'20 minutes'},
                   {'name':'Source links','a':'Not shown','b':'Shown'},
                   {'name':'Price','a':'Free','b':'Free'}],
        'changes':[{'factor':0,'target':'b','value':'No new setup','explanation':'Setup effort may matter','rival':'Familiarity may matter'},
                   {'factor':1,'target':'a','value':'Shown','explanation':'Checking answers may matter','rival':'Familiarity may matter'}]}


class CapabilityTests(unittest.TestCase):
    def study(self, **kwargs):
        d=draft()
        return studio.approve(d,{'confirmed':True,'method':'interview','recording':True,'design':d['design'],**kwargs})

    def answer(self, study, state, value=None, skip=False, meta=None):
        return studio.answer(study,state,{'nonce':state['nonce'],'answer':value,'skip':skip},meta or NoMeta())

    def at_baseline(self, study):
        state=studio.start(study,True)
        while state['queue'][state['index']]['id']!='CB':
            state=self.answer(study,state,skip=True)
        return state

    def test_comparison_compiler_changes_exactly_one_cell(self):
        p=cap.validate_comparisons(plan()); baseline=cap.comparison_question(p)
        for change in p['changes']:
            variant=cap.comparison_question(p,change)
            differences=[(i,k) for i,row in enumerate(baseline['comparison']['rows']) for k in ('a','b') if row[k]!=variant['comparison']['rows'][i][k]]
            self.assertEqual(differences,[(change['factor'],change['target'])])
            self.assertEqual(baseline['options'],variant['options'])
            self.assertEqual(baseline['prompt'],variant['prompt'])

    def test_invalid_comparison_changes_rejected(self):
        for mutate in [lambda p:p['changes'][0].update(factor=True),lambda p:p['changes'][0].update(factor=10),
                       lambda p:p['changes'][0].update(target='c'),lambda p:p['changes'][0].update(value='20 minutes'),
                       lambda p:p.update(b_title=p['a_title']),lambda p:p['factors'][1].update(name='Setup')]:
            p=plan();mutate(p)
            with self.assertRaises(ValueError):cap.validate_comparisons(p)

    def test_baseline_skip_does_not_issue_an_uninterpretable_variant(self):
        study=self.study(comparisons=plan());state=self.at_baseline(study)
        state=self.answer(study,state,skip=True)
        self.assertEqual(state['queue'][state['index']]['phase'],'correction')
        self.assertFalse(any(q['id']=='CV' for q in state['queue']))

    def test_participant_payload_hides_researcher_rationale(self):
        study=self.study(comparisons=plan());state=self.at_baseline(study)
        question=studio.public_session(state,study)['question']
        self.assertNotIn('purpose',question)
        self.assertEqual(set(question['comparison']),{'rows','display_order'})

    def test_answered_pair_keeps_order_and_counts_only_responded_pairs(self):
        study=self.study(comparisons=plan());state=self.at_baseline(study)
        baseline=state['queue'][state['index']]
        state=self.answer(study,state,baseline['options'][0])
        variant=state['queue'][state['index']]
        self.assertEqual(variant['options'],baseline['options'])
        self.assertEqual(variant['comparison']['display_order'],baseline['comparison']['display_order'])
        state=self.answer(study,state,variant['options'][1])
        while state['status']=='active':state=self.answer(study,state,skip=True)
        result=cap.comparison_results([state])[0]
        self.assertEqual(result['answered_both'],1);self.assertEqual(result['different_option'],1)
        self.assertEqual(state['decisions'][0]['source'],'fixed_fallback')

    def test_native_selection_cannot_edit_stimuli_or_cite_skips(self):
        study=self.study(comparisons=plan());state=self.at_baseline(study)
        state=self.answer(study,state,state['queue'][state['index']]['options'][0])
        evidence=state['responses'][-1]['id']
        def result(ids):return {'choices':[{'message':{'tool_calls':[{'id':'call-test','function':{'name':'select_approved_condition','arguments':json.dumps({'id':'V2','reason':'Check source-link trade-off','source_ids':ids,'if_switch':'Source links may matter here','if_same':'Other details may still matter'})}}]}}]}
        with patch.object(cap,'request',return_value=result([evidence])):
            selected,trace=cap.select_comparison(study,state,FakeMeta())
        self.assertEqual(selected['id'],'V2');self.assertEqual(trace['source'],'muse_native_tool')
        with patch.object(cap,'request',return_value=result(['invented'])):
            selected,trace=cap.select_comparison(study,state,FakeMeta())
        self.assertEqual(selected['id'],'V1');self.assertEqual(trace['source'],'fixed_fallback')

    def test_background_requires_actual_search_and_valid_citations(self):
        payload={'output':[{'type':'web_search_call'},{'type':'message','content':[{'type':'output_text','text':'A sourced background.',
            'annotations':[{'type':'url_citation','url':'https://example.org/paper','title':'Paper','start_index':2,'end_index':9}]}]}]}
        with patch.object(cap,'request',return_value=payload):
            result=cap.background('AI research brief',FakeMeta())
        self.assertEqual(result['kind'],'desk_research_not_participant_evidence')
        self.assertEqual(result['brief_digest'],cap.digest('AI research brief'))
        for bad in ({'output':payload['output'][1:]},{'output':[{'type':'web_search_call'}]}):
            with patch.object(cap,'request',return_value=bad),self.assertRaises(ValueError):cap.background('Brief',FakeMeta())
        payload['output'][1]['content'][0]['annotations'][0]['url']='javascript:alert(1)'
        with patch.object(cap,'request',return_value=payload),self.assertRaises(ValueError):cap.background('Brief',FakeMeta())

    def test_concept_generation_and_edit_use_distinct_endpoints(self):
        encoded=base64.b64encode(b'\xff\xd8\xfffictional-test-image').decode()
        with patch.object(cap,'request',return_value={'data':[{'b64_json':encoded}]}) as call:
            candidate=cap.concept('A fictional card','',FakeMeta())
            self.assertEqual(call.call_args.args[1],'/images/generations')
            self.assertFalse(call.call_args.args[2]['tool_enablement']['enable_web_search'])
            edited=cap.concept('Revise the heading',candidate['image'],FakeMeta())
            self.assertEqual(call.call_args.args[1],'/images/edits')
        self.assertNotEqual(candidate['id'],edited['id']);self.assertIsNotNone(edited['reference_digest'])

    def test_task_recording_requires_approval_and_matching_nonce(self):
        study=self.study(task_prompt='Show a fictional task.')
        state=studio.start(study,True)
        self.assertEqual(state['queue'][0]['type'],'task')
        data={'nonce':state['nonce'],'mime':'video/mp4','duration':4,'video':base64.b64encode(b'\0\0\0\x18ftypisom-fixture').decode()}
        for overrides in ({'nonce':'wrong'},{'duration':61},{'mime':'text/html'},{'video':'not-base64'}):
            with self.assertRaises(ValueError):cap.inspect_clip({**data,**overrides},study,state,FakeMeta())
        self.assertEqual(state['responses'],[])

    def test_task_review_keeps_corrections_and_does_not_promote_unconfirmed_events(self):
        state={'id':'s','nonce':'n'}
        review={'id':'r','session_id':'s','nonce':'n','events':[{'id':'T1','seconds':1,'description':'Option appeared'},{'id':'T2','seconds':2,'description':'Another event'}],'uncertainty':'Approximate timing','video_sha256':'digest'}
        answer=cap.task_answer({'confirmed_event_ids':['T1'],'correction':'T2 is incorrect'},review,state)
        self.assertEqual(len(answer['confirmed_events']),1);self.assertEqual(answer['unconfirmed_events'][0]['id'],'T2')
        self.assertEqual(answer['participant_correction'],'T2 is incorrect')
        for value in ({'confirmed_event_ids':['invented']},{'confirmed_event_ids':[]}):
            with self.assertRaises(ValueError):cap.task_answer(value,review,state)
        with self.assertRaises(ValueError):cap.task_answer({'correction':'No'},review,{'id':'s','nonce':'old'})

    def test_video_observations_have_bounded_timestamps_and_raw_video_is_not_saved(self):
        study=self.study(task_prompt='Show a fictional task.');state=studio.start(study,True)
        payload={'nonce':state['nonce'],'mime':'video/mp4','duration':4,'video':base64.b64encode(b'\0\0\0\x18ftypisom-fixture').decode()}
        output=lambda seconds:{'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'events':[{'seconds':seconds,'description':'A selected option is shown'}],'uncertainty':'No click telemetry'})}]}]}
        with patch.object(cap,'request',return_value=output(2)):
            review=cap.inspect_clip(payload,study,state,FakeMeta())
        self.assertFalse(review['raw_video_saved']);self.assertNotIn('video',review)
        with patch.object(cap,'request',return_value=output(5)),self.assertRaises(ValueError):cap.inspect_clip(payload,study,state,FakeMeta())

    def test_stream_tickets_are_one_use_expiring_and_bound_to_question(self):
        with tempfile.TemporaryDirectory() as temp:
            store=ResearchStore(Path(temp)/'test.sqlite3');study=self.study();state=studio.start(study,True);store.put('studio_session',state['id'],state)
            bridge=type('Bridge',(),{'ready':True,'port':8781})()
            with patch.object(voice_stream,'_bridge',bridge),patch.object(voice_stream,'MetaClient',FakeMeta):
                ticket=voice_stream.ticket(study,state,state['nonce'],store)
            token=ticket['url'].split('ticket=')[1]
            self.assertEqual(voice_stream.consume(token)['state_id'],state['id'])
            with self.assertRaises(ValueError):voice_stream.consume(token)
            with patch.object(voice_stream,'_bridge',bridge),patch.object(voice_stream,'MetaClient',FakeMeta):
                ticket=voice_stream.ticket(study,state,state['nonce'],store)
            token=ticket['url'].split('ticket=')[1];voice_stream._tickets[token]['expires']=time.monotonic()-1
            with self.assertRaises(ValueError):voice_stream.consume(token)

    def test_new_features_are_not_silently_added_to_existing_policies(self):
        study=self.study();study['policy']={'version':1,'recording_model':'muse-spark-1.2','survey_probes':2,'interview_probes':3}
        state=studio.start(study,True);public=studio.public_session(state,study)
        self.assertFalse(public['streaming_voice']);self.assertEqual(public['recording_seconds'],30)
        self.assertNotIn('task', [q['type'] for q in state['queue']])

    def test_confirmed_task_review_can_trigger_a_bounded_grounded_probe(self):
        study=self.study(task_prompt='Show the fictional task.');state=studio.start(study,True)
        answer={'_validated_task_review':True,'confirmed_events':[{'id':'T1','seconds':1,'description':'A comparison is displayed'}],
                'participant_correction':'This was a demonstration, not my real behaviour.'}
        state=self.answer(study,state,answer,meta=FakeMeta())
        self.assertTrue(state['queue'][state['index']]['adaptive'])
        self.assertEqual(state['queue'][state['index']]['phase'],'interview')
        self.assertEqual(state['probes']['interview'],1)
        self.assertEqual(state['responses'][0]['answer']['participant_correction'],'This was a demonstration, not my real behaviour.')

    def test_server_checks_background_review_and_exact_brief_before_generation(self):
        from choicegap import server
        with tempfile.TemporaryDirectory() as temp:
            store=ResearchStore(Path(temp)/'test.sqlite3')
            background={'id':'bg','brief_digest':cap.digest('Exact brief'),'summary':'Context only','citations':[]}
            store.put('studio_background','bg',background)
            handler=object.__new__(server.Handler);handler._json=lambda *args:None
            with patch.object(server,'STORE',store),patch.object(server,'MetaClient',FakeMeta),patch.object(studio,'generate',return_value=draft()) as generate:
                for brief,reviewed in [('Exact brief',False),('Changed brief',True)]:
                    with self.assertRaises(ValueError):handler._studio_post('/api/studio/generate',{'brief':brief,'background_id':'bg','background_reviewed':reviewed})
                generate.assert_not_called()
                handler._studio_post('/api/studio/generate',{'brief':'Exact brief','background_id':'bg','background_reviewed':True})
                self.assertEqual(generate.call_args.args[0]['_reviewed_background'],background)
                handler._studio_post('/api/studio/generate',{'brief':'Any brief','_reviewed_background':{'forged':True}})
                self.assertNotIn('_reviewed_background',generate.call_args.args[0])

    def test_server_does_not_accept_forged_recording_observations(self):
        from choicegap import server
        study=self.study(task_prompt='Show the fictional task.');state=studio.start(study,True)
        with tempfile.TemporaryDirectory() as temp:
            store=ResearchStore(Path(temp)/'test.sqlite3');store.put('studio_study',study['id'],study);store.put('studio_session',state['id'],state)
            handler=object.__new__(server.Handler);handler._json=lambda *args:None
            with patch.object(server,'STORE',store),patch.object(server,'MetaClient',NoMeta),self.assertRaises(ValueError):
                handler._studio_post('/api/studio/answer',{'id':state['id'],'nonce':state['nonce'],'answer':{'_validated_task_review':True,'review_id':'invented','confirmed_event_ids':['T1']}})
            self.assertEqual(store.get('studio_session',state['id'])['responses'],[])


if __name__=='__main__':unittest.main()
