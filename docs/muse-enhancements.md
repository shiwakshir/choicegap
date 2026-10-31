# Research tools and 3D moderator

Updated 31 October 2026. The included stylised 3D character is the chosen avatar route. It runs locally with the existing Meta key; no external avatar account is used. It is identified as AI and has approximate speaking animation, not photorealistic video or exact viseme lip sync.

## Start and try

Stop the existing server first. From the project folder, run:

```powershell
.\Start-ChoiceGap.ps1
```

On first use this creates a local environment under `work/choicegap-venv` and installs the declared dependencies. It uses the user's Python 3.14 installation when present. The ignored `.env` stays in the project folder. The script does not print credentials. Alternatively install the package with `python -m pip install -e .` and start `python -m choicegap.server` from the repository directory.

Open `http://127.0.0.1:8000/?mode=researcher`. The usual brief → review → collect → findings flow remains the starting point. Optional tools sit inside expandable sections.

1. Enter a brief. Under **Research the background with cited sources**, choose **Find background with Muse**. Read the summary and linked sources. Check the review box if you want that background to inform study generation. Changing the brief requires a new source review; the server checks the exact brief digest.
2. Under **Add a concept or stimulus**, upload an image, generate one with Muse Image, or edit the attached image. Generation and editing create separate drafts. Select **Use this reviewed concept** explicitly. Inspect all text and visual differences: an image edit is not an experimental-control guarantee.
3. Generate the study and edit the survey/interview guide. Under **Test which conditions change a choice**, draft and review the scenario, option details and proposed changes. Check **Include the reviewed comparison tasks** only when they are appropriate.
4. Optionally enable **Ground the interview in a task recording** and write clear task instructions. Participants can upload a short WebM/MP4 or record a selected window. They preview it before sending to Meta, then confirm/correct proposed visible events. Raw video is not stored by ChoiceGap.
5. For an interview, enable spoken moderation and select **Included 3D AI character**. Optional vocabulary hints help Muse Voice recognise product names. Approve the complete study and publish its participant link.
6. In the participant view, start the spoken interview. The device reads the question; Muse Voice can stream partial transcription and detect a completed speech turn. The participant checks the final transcript before sending. They can pause, type, skip or hide the character.
7. Return to **Findings**. Review exact answers, recording corrections and comparison tables. Generate the evidence-linked analysis and inspect its supporting responses. Downloads include the reviewed inputs, exact tasks, model decisions and presentation metadata.

## What is implemented

| Capability | Integration | Research boundary |
| --- | --- | --- |
| Cited desk research | Spark Responses API with native `web_search`; returned URL annotations are validated and stored | Context, never participant findings. Citation syntax does not establish source quality or truth. |
| Concept creation and revision | Muse Image generations/edits endpoints; original and edited drafts remain separate | Researcher selects the stimulus. Images are not silently substituted during collection. |
| Approved condition comparisons | Spark native function call selects one approved change; code constructs the variant | Exactly one cell changes in the text task. Repetition, sequence and hypothetical context still limit interpretation. |
| Task-grounded interviewing | Spark reads a clip and proposes timestamped visible events; participant corrections enter the subsequent interview context | Approximate model descriptions, not verified click telemetry, gaze, emotion or actual purchase behaviour. |
| Streaming voice | Local WebSocket relay to Muse Voice Transcribe using native endpointing, partial text and optional vocabulary hints | No automatic answer submission. Pauses can end a turn early; transcripts remain editable. |
| Optional 3D presentation | Original procedural Three.js character with neutral idle movement and speaking animation | Presentation aid, not a human moderator or a method for interpreting participants' emotions. |

The earlier Studio recording path remains available if streaming fails. Old approved protocols are not migrated or expanded. New approvals have policy version 3 and snapshot the optional tasks, avatar and voice scope. Earlier controlled-choice studies continue to use their existing routes.

## Recording, voice and evidence handling

Screen clips are limited to 60 seconds and 12 MB. New voice answers are limited to 90 seconds. Screen capture requests video only, not microphone audio. Uploads may contain audio if participants supply an existing file; only share material appropriate for the disclosed study. Model video descriptions use approximate timestamps; sparse frame sampling can miss actions between frames. Unconfirmed events remain explicitly unconfirmed and must not be treated as observations in findings.

The app retains reviewed task descriptions, corrections, question/option copies and a recording hash. It does not retain raw video/audio. Data still goes to Meta for processing; Meta's own terms apply. Unsaved media previews disappear when the participant reloads or leaves the page.

Streaming uses a one-use, short-lived ticket tied to the session's current question. Only the local relay receives the Meta key. It enforces allowed localhost origins, frame size, duration and pacing limits, and rejects an answered question. The relay listens on the app's port plus one (normally 8001). If that port or the dependency is unavailable, the app can still use recorded transcription. This remains a single-computer prototype without researcher authentication; remote participant recruitment is not deployed.

Comparison order is randomized between participants and kept consistent within a participant's baseline/variant pair. The selected change, model rationale, prior response references and anticipated switch/same interpretation are logged before the variant answer. If tool selection fails, an explicitly labelled fixed fallback uses an existing approved change. A skipped baseline does not produce a variant. Pair counts use answered-pair denominators and show skipped/neither cases separately.

Avatar visibility is client-reported per response and included in exports. Hiding the character remains possible. Reduced-motion preferences disable animation. The character has no real person's likeness; renderer code is pinned locally with its MIT license. No external avatar service receives participant material.

## Verification and limits

Live checks used public research briefs and fictional material: cited background (five citations in the test), concept generation/editing, comparison drafting, a four-second synthetic task clip, and a synthetic spoken answer streamed through the actual local relay to Meta. The clip review correctly noted that only a few frames were available and that displayed selection was not click telemetry. Streaming returned partial/final text with native speech-turn completion and no submitted response.

Automated tests cover immutable approvals, all answer types, topic/probe budgets, native comparison selection/fallback, single-cell audits, skips, correction references, task-review validation, timestamp bounds, stale/one-use stream tickets, private credential handling, invalid/stale audio frames, PCM resampling and participant-controller pause/fallback behaviour. Browser checks cover the 3D character, hide/show, local upload/preview and reviewed recording observations. User-device microphone capture and speech playback across browsers still need a hands-on acceptance check. No human UXR validation, causal identification, provider superiority or measured time savings are claimed.

Sources: [Meta speech-to-text](https://dev.meta.ai/docs/speech-to-text), [search grounding](https://dev.meta.ai/docs/search-grounding), [image generation](https://dev.meta.ai/docs/image-generation), [video understanding](https://dev.meta.ai/docs/video-understanding), [tool calling](https://dev.meta.ai/docs/tool-calling), [Three.js](https://threejs.org/).
