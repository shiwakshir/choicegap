# Spoken AI moderator

Updated 31 October: new policy-version-three studies can use streaming Muse Voice with native endpointing and an optional local 3D character. See [the enhanced setup](muse-enhancements.md). The earlier recording workflow below remains the fallback and the protocol for existing approvals; no approved study is expanded silently.

ChoiceGap can conduct a turn-by-turn interview without a human attending the session. Muse Spark chooses the approved questions and bounded probes. The device's speech synthesis reads the question. The browser captures a short answer, Meta's Muse Voice Transcribe turns it into text, and the participant reviews/corrects it before submission. Muse then decides what to ask next.

## Try it

1. Restart the server and open `http://127.0.0.1:8000/?mode=researcher`.
2. Generate a study from your brief. Review the interview guide and follow-up topics.
3. Choose **Interview only** or **Survey, then interview**.
4. Enable **Offer a spoken AI moderator and voice answers**, confirm the review and publish.
5. Open the participant link, read the disclosure and start. At the first interview question choose **Start spoken interview**.
6. The device asks the question, then requests microphone access and listens. Allow the microphone if you want to use voice. A quiet pause after sustained sound can stop recording; **Stop recording** remains available. Each new approval permits up to 90 seconds per answer.
7. Muse transcribes the recording. Read/edit the text and select **Send answer**. Transcripts never auto-submit. The next question is read aloud while voice mode remains enabled.
8. Use **Pause voice mode** to stop the spoken flow and type instead. Switching away from the tab also pauses voice mode. Resume is explicit rather than reopening the microphone automatically.

No extra avatar account, key or speech-generation subscription is required. A functioning browser/device voice and microphone are needed. Voice quality varies by device. This is not a talking video avatar or a continuous speech-to-speech connection; the model can take time between turns. Researchers still define the study and review the findings.

## Boundaries and implementation

- New Studio approvals have policy version 2, `muse-voice-transcribe-1.0`, a 90-second recording limit, and an optional spoken-moderator capability. Existing approvals keep Spark 1.2 transcription, the original 30-second limit and their original UI. No approved document is migrated in place.
- Voice mode is an explicit participant action, available for interview/correction open questions when enabled by the researcher. Manual voice answers remain available for survey open questions.
- Microphone capture begins after the spoken question ends. Device/browser permission is still required. The status panel distinguishes asking, listening, transcription, review and next-question planning.
- Browser audio-level timing detects a quiet pause after sustained sound. This is a local capture heuristic, not linguistic endpoint detection or an emotion inference. Background noise can prevent early stopping; the hard duration cap remains. A pause can cut an answer short; participants can record again or edit the transcript.
- In spoken mode a stopped clip is sent automatically for transcription, as disclosed before activation. It is **not** automatically submitted as a research response. Pause does not erase existing typed text. If paused during capture, the clip is retained locally for optional playback/transcription.
- WAV conversion, key handling and audio validation remain as in Studio. The server calls `POST https://api.meta.ai/v1/asr/transcribe` with `request` JSON and an `audio` multipart part. No key enters the browser. There is no third-party speech-recognition service and audio is not saved by ChoiceGap.
- Meta's [dedicated voice documentation](https://dev.meta.ai/docs/speech-to-text) supports WAV transcription and realtime ASR. This implementation uses the file endpoint for each bounded answer; it does not implement the WebSocket realtime endpoint. Meta's [model description](https://dev.meta.ai/docs/models) states that Muse Voice returns text rather than synthesizing speech. Device speech supplies the outgoing voice.
- Spark probe planning uses medium reasoning effort and member checking low effort to reduce unnecessary turn delays. Study design and synthesis retain high effort. These settings are not evidence of moderation quality or guaranteed response times.

## Verification

Live Muse Voice transcribed a 9.28-second synthetic recording. It preserved the broad content but repeated one word, demonstrating why transcript correction matters. A live Spark call produced a concrete recent-episode probe from a scripted fictional interview answer. These are software demonstrations, not human research.

The JavaScript controller tests execute the actual participant controller with fake speech/media/network adapters. They check that capture waits for speech completion, capture stops before transcription, transcripts do not auto-submit, pausing cancels stale speech callbacks, permission cancellation closes a late stream, and microphone denial falls back to text. Separate timing tests cover silence, short noise, thinking pauses and duration caps. Python tests cover the dedicated endpoint, server-side credentials, transcript errors, duration limits and legacy approvals. Browser QA verifies the disclosure, ready-state moderator panel and resume flow; real device capture/voice playback across browsers has not been validated.

Run `node tests/spoken_moderator.test.cjs`, `node tests/spoken_turn.test.cjs`, and `python -m unittest discover -s tests -q` from the repository directory.
