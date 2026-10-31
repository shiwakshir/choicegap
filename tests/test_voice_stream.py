import asyncio
import importlib.util
import json
import unittest
from unittest.mock import patch

from choicegap import voice_stream


class Browser:
    def __init__(self, frame=b'\0'*3200):
        self.request=type('Request',(),{'path':'/voice?ticket=fixture'})()
        self.frame=frame;self.sent=[]
    async def send(self,data):self.sent.append(json.loads(data))
    def __aiter__(self):
        async def receive():
            yield self.frame
            await asyncio.sleep(10)
        return receive()


class Provider:
    def __init__(self):self.sent=[];self.audio=asyncio.Event()
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def send(self,data):
        self.sent.append(data)
        if isinstance(data,bytes):self.audio.set()
    async def recv(self):return '{"sessionId":"provider-fixture"}'
    def __aiter__(self):
        async def receive():
            await self.audio.wait()
            yield json.dumps({'type':'transcript','transcript':'A partial answer','final':False})
            yield json.dumps({'type':'speechComplete','transcript':'A final answer.','turnId':1})
        return receive()


@unittest.skipUnless(importlib.util.find_spec('websockets'),'Install the declared WebSocket dependency for relay tests')
class RelayTests(unittest.IsolatedAsyncioTestCase):
    def grant(self,nonce='issued'):
        store=type('Store',(),{'get':lambda *args:{'nonce':nonce,'status':'active','responses':[]}})()
        return {'state_id':'s','nonce':'issued','seconds':5,'keywords':['Gemini'],'store':store}

    async def exercise(self,browser,grant):
        provider=Provider()
        meta=type('Meta',(),{'api_key':'fictional-private-key'})
        with patch.object(voice_stream,'consume',return_value=grant),patch.object(voice_stream,'MetaClient',meta),patch('websockets.asyncio.client.connect',return_value=provider):
            await voice_stream.Bridge(8780,8781).relay(browser)
        return provider

    async def test_relay_keeps_credentials_private_and_never_submits_transcripts(self):
        browser=Browser();provider=await self.exercise(browser,self.grant())
        self.assertEqual(browser.sent[0]['type'],'ready')
        self.assertEqual(browser.sent[-1]['transcript'],'A final answer.')
        self.assertNotIn('fictional-private-key',json.dumps(browser.sent))
        settings=json.loads(provider.sent[0]);self.assertEqual(settings['mode'],'ENDPOINTING')
        self.assertEqual(settings['keywords'],['Gemini'])
        self.assertEqual(settings['authorization']['accessToken'],'Bearer fictional-private-key')
        self.assertEqual(self.grant()['store'].get()['responses'],[])

    async def test_invalid_audio_frame_is_not_forwarded(self):
        browser=Browser(b'x'*32001);provider=await self.exercise(browser,self.grant())
        self.assertEqual(browser.sent[-1]['type'],'error')
        self.assertFalse(any(isinstance(chunk,bytes) for chunk in provider.sent))

    async def test_answered_question_cannot_keep_streaming(self):
        browser=Browser();provider=await self.exercise(browser,self.grant('already-advanced'))
        self.assertEqual(browser.sent[-1]['type'],'error')
        self.assertFalse(any(isinstance(chunk,bytes) for chunk in provider.sent))


if __name__=='__main__':unittest.main()
