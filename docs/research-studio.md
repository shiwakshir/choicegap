# Research Studio

Updated 30 October 2026. This is the primary workflow at `/?mode=researcher`; earlier delivery studies remain at `/index.html?mode=researcher`.

## Product workflow

Brief → Muse draft → researcher edits and approves → adaptive survey/interview → participant correction → researcher findings.

The platform is domain independent. The two example briefs cover AI-assistant adoption and sustainable shopping. They are fictional starting points, not evidence or validated instruments. A brief should state the decision, target population, context and learning objectives. Hypotheses are optional starting explanations. Add concept text or a PNG/JPEG/WebP image up to 1 MB. Muse receives the image when drafting; only approved questions marked “show stimulus” display it to participants.

Researchers can edit question wording, type, answer labels, order, purpose and evidence category; add/remove questions; edit the interview guide and permitted follow-up topics; and save/reopen drafts. Publication creates a separate immutable snapshot. Subsequent draft edits cannot change a running study. Researchers should inspect generated options for neutrality, realistic assumptions and confounds. Combining several differences in a choice can explore a trade-off but cannot isolate the effect of one difference.

The seven types currently implemented are open ended, single select, multi select, full ranking with keyboard-accessible up/down buttons, 1–5 scale, numeric and hypothetical choice. Each guide supports up to 18 questions. There are no matrix, conjoint, date, attachment-response, panel management or automatic recruitment features. “Other” is currently a selectable label; use an open follow-up for the explanation.

## What adapts

The approved base questions remain in order. After a non-skipped base answer, Muse can insert one neutral open probe about a permitted topic. It reads the study objective, starting hypotheses, responses so far, prior probes and upcoming questions. The probe should clarify a specific episode, constraint or alternative explanation; the participant need not exhibit a discrepancy.

Survey: at most two inserted probes and four planning attempts. Interview: at most three inserted probes and six planning attempts. Probes do not recursively create probes. A further optional member-check question gives the participant an opportunity to correct Muse's tentative account. Skipping is not confirmation. An all-skipped session makes no moderation or member-check model call. Failed/invalid planning continues the approved guide and records the failure. Topic membership/source-ID validation limits structural scope; it cannot guarantee that a question is neutral or semantically within scope.

This is bounded adaptive probing, not arbitrary generated questionnaire branching, automatic question replacement, a synchronous live conversation, or an avatar. Respondents may wait for a model request between turns. There is no validated behavioural-science scale and no emotion, personality or deception inference.

## Voice answers

If enabled at approval, open questions offer an explicit microphone recording action. Recordings stop after 30 seconds. Participants can listen locally before selecting “Transcribe this recording.” The browser converts audio to mono 16 kHz PCM WAV and sends it to the local server; the server validates its duration and sends it to Meta. The recording is held in browser/request memory rather than persisted by ChoiceGap. Browser/device permission and support are required. Participants can type instead.

The transcript appears in the answer field for correction. It is submitted only with “Send answer,” then stored as `confirmed_transcript`. This label records the UI input mode, not an independently verified verbatim transcript. Raw audio is not retained for later researcher playback. Optional question read-aloud uses browser speech synthesis, not Muse speech generation.

Meta's [video/audio documentation](https://dev.meta.ai/docs/video-understanding) currently warns that audio in Spark 1.3 is not fully supported and shows Spark 1.2 examples. Accordingly audio transcription uses `muse-spark-1.2`; generation, probing, member checking and analysis use configured Spark 1.3. Both use Meta Model API, not another AI provider. This is not evidence that Meta is uniquely capable of the workflow.

## Findings and evidence

The researcher can inspect every submitted response and the moderator's recorded rationale. Analysis includes the latest completed sessions within a 30-session / 180,000-character evidence limit, disclosing the included count and exact session IDs. No answer text is truncated; an individual session exceeding the limit cannot be synthesized here. Unfinished sessions are counted separately. Every finding must reference existing, non-skipped records. When a cited participant supplied a final correction, the finding must also include that correction source. Actual answer text is displayed from the stored record, not re-created by the model.

Findings distinguish stated priorities, reported past actions, hypothetical choices, context and explanations. These are researcher-editable measurement labels, not independently verified provenance. The report proposes tentative behavioural interpretations, rivals, product tests and further research. It cannot establish an actual say-do gap or causal mechanism from self-reports and hypothetical tasks. A researcher must decide whether two measures concern comparable decisions and contexts. No representative prevalence or time-saving claims have been validated.

## Local setup and persistence

From the repository directory:

```powershell
& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m choicegap.server
```

Configure `MODEL_API_KEY` in the ignored local `.env`, then restart. Do not paste credentials into the brief. No extra Python packages are required. `PORT` changes the port; `CHOICEGAP_DATA_DIR` changes the SQLite directory. Default: `work/choicegap-data/research.sqlite3`. New static assets are included in package data. The server serves Research Studio at the root, while existing study query links continue to use the earlier app.

Research Studio records use separate `studio_study`, `studio_session` and `studio_report` document kinds. A durable nonce rejects duplicate/stale responses; the response and next issued question commit atomically. If a network response is lost after commit, resume the saved session instead of resubmitting a stale nonce. Draft designs and published snapshots persist across restarts. A session token is stored locally in the participant browser for explicit resume.

This is a single-computer prototype. It has no authentication, encryption, retention/deletion UI, incentives, sample management or remote deployment. Do not expose the server publicly as a production research service. Consent explains use of Meta and local text storage; enabling voice does not silently expand earlier study approvals. Meta's own retention policies also apply to submitted data.

## Verification

- Automated tests cover all seven answer validators, researcher edits/snapshot isolation, explicit consent, inserted probes, caps, skip handling, out-of-scope fallback, final corrections, immutable approvals, durable duplicate rejection and evidence-reference validation.
- Full existing regression checks are retained for earlier studies.
- A live fictional check used actual Spark 1.2 transcription of synthetic speech, Spark 1.3 probing/member check and evidence-linked synthesis. Synthetic speech and scripted responses are software fixtures, not human validation. Raw check output is in the ignored `outputs/studio-fictional-live-check.json`.
- Browser QA covers actual brief generation, editing/adding a numeric question, saving, publishing and the participant flow.

Unknowns remain: real researcher usability, participant burden, transcription quality across accents/languages, moderation neutrality, semantic validity, accessibility across assistive technologies, cost/latency at scale and generalizable product demand.

The latest run passed 125 Python tests (13 for Research Studio), the two existing JavaScript checks and the new script's syntax check. See [the validation record](studio-validation.json). Live transcription used synthetic speech; actual microphone capture across browsers remains unverified.
