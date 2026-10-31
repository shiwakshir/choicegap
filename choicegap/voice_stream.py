"""Local, capability-scoped WebSocket relay. Meta credentials never reach the browser."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import secrets
import threading
import time
from urllib.parse import parse_qs, urlparse

from .meta import MetaClient

_bridge = None
_tickets = {}
_lock = threading.Lock()


def available():
    return bool(_bridge and _bridge.ready)


def ticket(study, state, nonce, store):
    if not available():
        raise ValueError('Streaming voice is unavailable. Install the project dependencies and restart; recorded voice still works.')
    if not MetaClient().enabled or not study['recording'] or not study['policy'].get('streaming_voice'):
        raise ValueError('This approval does not enable streaming voice')
    if state['status'] != 'active' or state['nonce'] != nonce or state['queue'][state['index']]['type'] != 'open':
        raise ValueError('Streaming voice does not match the issued question')
    token = secrets.token_urlsafe(32)
    with _lock:
        for key in list(_tickets):
            if _tickets[key]['expires'] < time.monotonic():
                del _tickets[key]
        _tickets[token] = {'expires': time.monotonic() + 30, 'state_id': state['id'], 'nonce': nonce,
            'seconds': study['policy'].get('recording_seconds', 90), 'store': store,
            'keywords': study.get('voice_keywords', [])}
    return {'url': f'ws://127.0.0.1:{_bridge.port}/voice?ticket={token}', 'expires_seconds': 30,
            'model': 'muse-voice-transcribe-1.0', 'audio_encoding': 'PCM_16KHZ'}


def consume(token):
    with _lock:
        grant = _tickets.pop(token, None)
    if not grant or grant['expires'] < time.monotonic():
        raise ValueError('Voice session expired. Start recording again.')
    state = grant['store'].get('studio_session', grant['state_id'])
    if state['status'] != 'active' or state['nonce'] != grant['nonce']:
        raise ValueError('This interview question is out of date')
    return grant


def checked_event(event):
    kind = event.get('type')
    if kind not in ('speechStart', 'speechEnd', 'speechComplete', 'transcript'):
        return None
    result = {'type': kind}
    if 'transcript' in event:
        transcript = event['transcript']
        if not isinstance(transcript, str) or len(transcript) > 6000:
            raise ValueError('Invalid voice transcript')
        result['transcript'] = transcript
    for key in ('turnId', 'audioProcessedMs', 'final'):
        if key in event:
            result[key] = event[key]
    return result


class Bridge:
    def __init__(self, http_port, port):
        self.http_port, self.port = http_port, port
        self.ready = False
        self.started = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='choicegap-voice')

    async def relay(self, browser):
        from websockets.asyncio.client import connect
        try:
            parsed = urlparse(browser.request.path)
            if parsed.path != '/voice':
                raise ValueError('Unknown voice stream')
            grant = consume(parse_qs(parsed.query).get('ticket', [''])[0])
            async with connect('wss://api.meta.ai/v1/asr/realtime', open_timeout=20, max_size=100_000, proxy=None) as meta:
                settings = {'authorization': {'accessToken': 'Bearer ' + MetaClient().api_key},
                    'model': 'muse-voice-transcribe-1.0', 'audioEncoding': 'PCM_16KHZ',
                    'mode': 'ENDPOINTING', 'partialMode': 'CUMULATIVE', 'emitAudioProgress': False}
                if grant['keywords']:
                    settings['keywords'] = grant['keywords']
                await meta.send(json.dumps(settings))
                acknowledgement = json.loads(await asyncio.wait_for(meta.recv(), 15))
                if not acknowledgement.get('sessionId'):
                    raise ValueError('Muse Voice could not start')
                await browser.send(json.dumps({'type': 'ready'}))
                finished = asyncio.Event()
                started, total = time.monotonic(), 0

                async def send_audio():
                    nonlocal total
                    async for chunk in browser:
                        if isinstance(chunk, bytes):
                            if not chunk or len(chunk) > 32000 or len(chunk) % 2:
                                raise ValueError('Invalid audio frame')
                            total += len(chunk)
                            if total > grant['seconds'] * 32000 or total / 32000 > time.monotonic() - started + 2:
                                raise ValueError('Voice duration or pacing limit reached')
                            # A session answered in another tab must not keep sending audio.
                            state = await asyncio.to_thread(grant['store'].get, 'studio_session', grant['state_id'])
                            if state['nonce'] != grant['nonce'] or state['status'] != 'active':
                                raise ValueError('This question has already advanced')
                            await meta.send(chunk)
                        else:
                            control = json.loads(chunk)
                            if control != {'type': 'endStream'}:
                                raise ValueError('Invalid voice control')
                            await meta.send(json.dumps(control))
                            await finished.wait()
                            return

                async def receive_text():
                    async for message in meta:
                        if not isinstance(message, str):
                            continue
                        raw = json.loads(message)
                        if raw.get('type') == 'error':
                            raise ValueError('Muse Voice stream unavailable')
                        event = checked_event(raw)
                        if event:
                            await browser.send(json.dumps(event))
                            if event['type'] == 'speechComplete':
                                finished.set()
                                return
                    finished.set()

                send = asyncio.create_task(send_audio())
                receive = asyncio.create_task(receive_text())
                try:
                    done, pending = await asyncio.wait([send, receive], timeout=grant['seconds'] + 20,
                                                       return_when=asyncio.FIRST_COMPLETED)
                    if not done:
                        raise ValueError('Voice stream timed out')
                    for task in done:
                        task.result()
                finally:
                    for task in (send, receive):
                        task.cancel()
                    await asyncio.gather(send, receive, return_exceptions=True)
        except Exception:
            try:
                await browser.send(json.dumps({'type': 'error', 'message':
                    'Streaming stopped. You can transcribe the recorded clip or type your answer.'}))
            except Exception:
                pass

    async def serve(self):
        from websockets.asyncio.server import serve
        self.stop_event = asyncio.Event()
        self.loop = asyncio.get_running_loop()
        origins = [f'http://127.0.0.1:{self.http_port}', f'http://localhost:{self.http_port}']
        try:
            async with serve(self.relay, '127.0.0.1', self.port, origins=origins, max_size=40000,
                             max_queue=8, compression=None):
                self.ready = True
                self.started.set()
                await self.stop_event.wait()
        finally:
            self.ready = False
            self.started.set()

    def run(self):
        try:
            asyncio.run(self.serve())
        except Exception:
            self.started.set()

    def stop(self):
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.stop_event.set)
            self.thread.join(timeout=3)


def start(http_port, port=None):
    global _bridge
    if not importlib.util.find_spec('websockets'):
        return None
    _bridge = Bridge(http_port, port or http_port + 1)
    _bridge.thread.start()
    _bridge.started.wait(timeout=3)
    return _bridge
