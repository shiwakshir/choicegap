# ChoiceGap verification — 1 November 2026

The local research prototype passes the checks below. It is not ready for an unrestricted public demo or real participant recruitment.

## Confirmed and fixed

1. **Local cross-origin requests:** the unauthenticated HTTP server now checks its Host and Origin and rejects cross-site writes and non-JSON POSTs before reading data or making model calls. This reduces cross-site request and DNS-rebinding exposure. It does not add researcher authentication. Public tunnel hostnames are intentionally rejected.
2. **Invisible scale labels:** new/re-edited 1–5 scales require exactly two endpoint labels. Previously extra labels could be accepted but not shown. Existing immutable approvals are not rewritten.
3. **Understated study length:** the participant estimate now includes the optional recording task, up to three comparison questions and final correction, plus a separate disclosure of possible probes. It says “up to” because skipping a baseline can remove follow-up tasks.
4. **Voice expectation:** survey-only welcome text no longer promises a spoken interview; interview wording makes typing and optional voice clear.
5. **Forced findings:** synthesis accepts 0–4 findings. A valid inconclusive report no longer fails simply because it has no supported finding. Nonempty findings still require checked non-skipped evidence and correction references.
6. **Stale submission plan:** the project thesis, demo outline, model usage and evaluation mapping now describe Studio. Earlier choice-engine benchmarks are not presented as moderator-quality scores.

## Verification performed

| Check | Result and scope |
| --- | --- |
| Python regression suite | 154 tests passed, including new request guards, scale validation, question estimate and zero-finding report tests. |
| JavaScript checks | Five passed: research UI, report copy, spoken-turn detection, spoken controller and PCM worklet. Fake devices do not exercise an actual microphone. |
| User Python | App and websockets imported successfully in the startup helper's Python 3.14.5 environment. |
| Installable package | Wheel built and installed in an isolated environment; imported outside the repository with the seven critical Studio/voice/avatar assets present. |
| Fresh Meta generation | Spark generated a sustainability draft; a smaller explicitly reviewed fictional study exercised adaptive collection and approved-condition selection. |
| Fresh collection | Eight scripted responses completed; the approved timing-only variant changed the selected hypothetical option. This is a software fixture, not research on a person. |
| Findings failure investigation | Initial synthesis returned HTTP 400. A diagnostic retry reported “invalid findings structure.” The initial raw model result was not captured, so its exact content is unknown. Review identified that an empty findings array was rejected. After the prompt/validator fix, another live call returned and saved an inconclusive report with zero findings. |
| Correction preservation | The post-fix overview explicitly retained the fictional-material correction and declined substantive adoption claims. Comparison counts remained descriptive and separately labelled. |
| Browser | Saved-study reopening, collection link, participant consent/disclosures and updated question estimate, report display and source review checked; screenshots retained. |
| Local configuration | `.env`, databases, work files and generated outputs are ignored. Distribution archive is scanned for the actual configured key before packaging. |
| Actual HTTP boundary checks | Six passed: normal health request; rejection of foreign Host, foreign Origin and text/plain writes; `.env` unavailable; path traversal rejected. |

Live transcript, video, image, grounding and native-tool integration checks from 31 October remain documented separately. They were not all repeated on November 1. They used synthetic/fictional inputs, not human participants.

## Remaining checks and release work

- User-device microphone permission, real speech, outgoing speech playback, interruption and fallback need a hands-on acceptance test. Do not infer these pass from synthetic audio or fake-device tests.
- Public access requires authenticated researcher controls, participant isolation, rate/spend limits, HTTPS-compatible routing for the streaming relay and an explicit allowed-host deployment configuration. No tunnel or hosting was enabled by this audit.
- The app stores submitted text in a local unencrypted database and has no participant deletion interface. Use fictional data for the hackathon demonstration.
- GitHub publication, a recorded three-minute demo and final submission answers remain outstanding. The supplied participant guide expects a live product but does not explicitly state a hosted URL is mandatory; the actual form/organizer must settle that field.
- Research validity remains unestablished: no human UXR usability study, measured time savings, representative behavioural findings, causal identification or provider superiority. Neutrality and semantic interpretation require human assessment beyond schema/source checks.

## Next action

Run one complete spoken study on the user's device. Fix any observed issue, then freeze a demonstrated workflow, record the video and publish the reviewed source repository. If a hosted demo is needed, implement and test deployment controls before exposure.
