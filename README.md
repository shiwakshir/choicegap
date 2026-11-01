# ChoiceGap

**Brief-led adaptive surveys and AI-moderated UX research, built with Meta Muse.**

ChoiceGap turns a researcher brief, hypotheses, and an optional concept stimulus into an editable survey and AI-moderated interview guide. After researcher approval, participants complete a survey, an adaptive spoken or typed interview, or both—with bounded follow-up probes, single-detail controlled comparisons selected via native tool calling, and a participant member-check step to correct the model's tentative understanding. Researchers receive findings linked to exact response IDs, participant corrections, competing explanations, and proposed next tests.

---

## Project Highlights (Meta Global AI Developer Hackathon)

| Dimension | What ChoiceGap Delivers |
| :--- | :--- |
| **Problem & Real-World Impact**<br>*(Build for Your World)* | Bridges the gap between rigid static surveys and costly human-moderated UX interviews. Researchers start from a plain-language brief and hypotheses, approve the generated study, and collect adaptive survey + spoken/typed interview responses with findings tied to exact response IDs, participant corrections, and rival explanations. |
| **Depth of Meta AI Tooling** | Combines **Muse Spark (`muse-spark-1.3`)** (native `web_search` grounding, strict JSON schemas, reasoning effort, native `select_approved_condition` tool calling, and multimodal `input_video` / `image_url` inspection), **Muse Image (`muse-image-1.0`)** (`/images/generations` and `/images/edits` for concept stimuli), and **Muse Voice Transcribe (`muse-voice-transcribe-1.0`)** (realtime `wss://api.meta.ai/v1/asr/realtime` streaming with endpointing + file ASR fallback). |
| **Technical Depth & Verifiability** | Enforces strict model/code boundaries: immutable study approvals, SHA-256 stimulus/brief digests, single-cell factorial change auditing, capped & topic-bound adaptive probes, participant member-checks (`C1`) that supersede model interpretations, `0–4` finding synthesis (allowing inconclusive results), capability-scoped one-use WebSocket tickets, and 154 Python + 5 JS test suites. |
| **End-to-End Live Workflow** | Ships a complete vertical slice (`Start-ChoiceGap.ps1`) featuring cited background research, concept generation/editing, multi-type surveys, a spoken 3D AI moderator (local Three.js character + streaming voice), video task review, controlled comparisons, and de-identified JSON exports. |

---

## Meta AI Models & Capabilities Used

ChoiceGap integrates the **Meta Model API** across preparation, multimodal stimulus creation, live spoken moderation, adaptive experimentation, and evidence-linked synthesis:

| Meta Model / Endpoint | Capability Used | Role in ChoiceGap | Implementation |
| :--- | :--- | :--- | :--- |
| **`muse-spark-1.3`**<br>`POST /v1/responses` | **Native Web Search Grounding** (`tools: [{"type": "web_search"}]`) | Conducts cited desk research from a study brief, validating returned `url_citation` spans and storing a brief SHA-256 digest before study generation. | [`choicegap/studio_capabilities.py`](choicegap/studio_capabilities.py) (`background`) |
| **`muse-image-1.0`**<br>`POST /v1/images/generations`<br>`POST /v1/images/edits` | **Concept Generation & Visual Editing** | Generates or edits fictional UX/product concept stimuli for researcher review prior to study approval (keeping original and edited drafts distinct). | [`choicegap/studio_capabilities.py`](choicegap/studio_capabilities.py) (`concept`) |
| **`muse-spark-1.3`**<br>`POST /v1/chat/completions` | **Structured Outputs (`json_schema`, `strict: True`) & Reasoning Effort** | Drafts multi-type surveys and interview guides; plans bounded follow-up probes within approved topics; generates tentative member-check summaries; synthesizes cited reports (supporting `0–4` findings, including inconclusive results) and runs multimodal pre-fieldwork design critiques. | [`choicegap/studio.py`](choicegap/studio.py) (`generate`, `probe`, `synthesize`)<br>[`choicegap/meta.py`](choicegap/meta.py)<br>[`choicegap/review.py`](choicegap/review.py) |
| **`muse-spark-1.3`**<br>`POST /v1/chat/completions` | **Native Function / Tool Calling** (`select_approved_condition`) | Reviews live session evidence mid-study and selects one researcher-approved single-detail comparison variant to help separate a leading explanation from a rival account. | [`choicegap/studio_capabilities.py`](choicegap/studio_capabilities.py) (`select_comparison`)<br>[`choicegap/muse_research.py`](choicegap/muse_research.py) |
| **`muse-spark-1.3`**<br>`POST /v1/responses` | **Multimodal Video & Image Understanding** (`input_video`, `image_url`) | Inspects participant-uploaded/recorded task clips (up to 60s) to propose timestamped visible events for participant confirmation/correction, and inspects prototype screenshots for visual confounds. | [`choicegap/studio_capabilities.py`](choicegap/studio_capabilities.py) (`inspect_clip`)<br>[`choicegap/studio.py`](choicegap/studio.py) (`model_context`) |
| **`muse-voice-transcribe-1.0`**<br>`wss://api.meta.ai/v1/asr/realtime`<br>`POST /v1/audio/transcriptions` | **Realtime Streaming ASR & File ASR** (`PCM_16KHZ`, `ENDPOINTING`, vocabulary `keywords`) | Streams live partial transcripts and speech-turn endpointing through a capability-scoped local WebSocket relay (plus file-based WAV transcription fallback) for the spoken AI moderator. | [`choicegap/voice_stream.py`](choicegap/voice_stream.py) (`Bridge.relay`)<br>[`choicegap/studio.py`](choicegap/studio.py) (`transcribe_voice`) |

See [Why Meta models matter to ChoiceGap](docs/meta-model-role.md) and [Muse enhancements and boundaries](docs/muse-enhancements.md) for detailed capability mappings.

---

## Verifiable Agent Architecture & Responsibility Boundaries

```text
Researcher Brief + Hypotheses
   ├──► Muse Spark (/responses + web_search) ──► Cited Desk Research (researcher-reviewed)
   ├──► Muse Image (/images/generations|edits) ──► Visual Concept Stimulus (researcher-reviewed)
   └──► Muse Spark (Structured Output) ──► Editable Survey, Interview Guide & Comparison Matrix
                                                   │
                                      [ Immutable Study Approval ]
                                                   │
                                                   ▼
Participant Session (Survey / Spoken or Typed AI Interview / Task Recording)
   ├──► Muse Voice Transcribe (Realtime WSS) ──► Editable Live Transcript (+ 3D AI Moderator)
   ├──► Muse Spark (/responses + input_video) ──► Timestamped Task Events (participant-confirmed)
   ├──► Muse Spark (Bounded Probe Planner) ──► Adaptive Follow-Ups (capped & topic-checked)
   ├──► Muse Spark (Native Tool Call) ──► Single-Cell Variant Selection (code-audited)
   └──► Muse Spark (Member Check) ──► Participant Correction Step (supersedes model reading)
                                                   │
                                                   ▼
Evidence-Linked Research Report
   └──► Muse Spark (Strict Schema Synthesis) ──► 0–4 Findings + Exact Response Citations + Next Tests
```

### Strict Code vs. Model Separation

Muse performs bounded semantic generation, live moderation, approved-comparison selection, and evidence-linked synthesis. Deterministic application code enforces the research guardrails:

- **No unapproved stimuli:** Generated desk research, `muse-image-1.0` visuals, survey questions, and comparison matrices are drafts until explicitly approved by the researcher. Once published, study designs and stimuli are locked and hashed.
- **Bounded adaptive probing:** Code enforces probe budgets (at most 2 added survey probes across 4 attempts; at most 3 added interview probes across 6 attempts) and checks that every follow-up question belongs verbatim to the researcher's approved `followup_topics`.
- **Audited single-cell comparisons:** When Muse calls `select_approved_condition`, code constructs the variant so **exactly one cell** changes relative to the baseline table, randomizes option order between participants while keeping order consistent within a participant's baseline/variant pair, and logs the rationale before observing the answer.
- **Participant corrections take precedence:** Before finishing, participants review and can correct Muse's tentative summary (`C1`) and any proposed video task events. Unconfirmed video events are never promoted to observations.
- **Hallucination & citation checks:** Synthesis accepts `0–4` findings (so weak or fictional evidence cleanly produces an inconclusive report with zero forced findings). Any non-empty finding must cite valid, non-skipped response IDs and preserve participant corrections.
- **Scoped credentials & local request guards:** Meta API keys stay on the server. Streaming voice uses short-lived, one-use WebSocket tickets tied to the active question nonce. The HTTP server checks `Host`, `Origin`, and `Content-Type` before reading payloads or calling Meta APIs.

---

## Quickstart (Research Studio)

Requires **Python 3.10+** (tested through Python 3.14). Core HTTP routes use the Python standard library; realtime voice streaming uses the declared `websockets` package (automatically installed by `Start-ChoiceGap.ps1` or `pip install -e .`).

### 1. Configure your Meta API Key

Set `MODEL_API_KEY` in your environment or save `MODEL_API_KEY=your-key` in a local `.env` file in the repository root (`.env` is git-ignored):

```powershell
$env:MODEL_API_KEY = "your-key"
```

*(Without `MODEL_API_KEY`, the app starts in deterministic offline/local mode and clearly labels that state.)*

### 2. Start the Server

Run the PowerShell helper from the repository root (prepares `work/choicegap-venv` on first use):

```powershell
.\Start-ChoiceGap.ps1
```

Or run manually:

```powershell
python -m pip install -e .
python -m choicegap.server
```

Open **<http://127.0.0.1:8000/?mode=researcher>** in your browser.

### 3. Try the End-to-End Studio Workflow

1. **Enter a brief & prepare context:** Type a research brief or load the **AI assistant adoption** or **Sustainable shopping** editable example. Optionally expand **Research the background with cited sources** (Muse Spark `web_search`) or **Add a concept or stimulus** (upload or generate/edit with `muse-image-1.0`).
2. **Create & review the study draft:** Select **Create study draft**. Edit questions, answer options, interview guide prompts, permitted follow-up topics, and optional single-detail comparison tasks. Supported question types: **open ended, single select, multi select, ranking, 1–5 rating scale, number, and hypothetical choice**.
3. **Configure collection & approve:** Choose **Survey only**, **Interview only**, or **Survey, then interview**. Optionally enable **spoken AI moderation**, **streaming Muse Voice**, the **included 3D AI character** (local Three.js procedural moderator—no external avatar account needed), and **task recording**. Confirm your review and publish the participant link.
4. **Complete a participant session:** Open the participant link in another tab. Answer or skip questions, try spoken answers (up to 90s with live editable transcription) or a short task clip (up to 60s), complete the baseline/variant comparison, and review/correct Muse's tentative understanding at the end.
5. **Inspect findings & export:** Return to **Findings**, refresh responses, and click **Analyze responses** to inspect cited responses, comparison counts, participant corrections, and JSON exports.

See [interface design notes](docs/interface-design.md), [spoken interview setup and validation](docs/spoken-moderator.md), [the enhanced workflow guide](docs/muse-enhancements.md), [Research Studio setup and boundaries](docs/research-studio.md), and [the 1 November verification audit](docs/choicegap-audit-2026-11-01.md).

---

## Earlier Controlled-Choice & Evidence Workbench Workflows

Research Studio (`studio.html`) is the primary interface and is independent of the earlier grocery-delivery controlled-choice protocol (`index.html`). Existing links and approvals retain their original flow; open <http://127.0.0.1:8000/index.html?mode=researcher> to use those earlier tools:

- **Integrated controlled-choice study (`v2`):** Combines a short rating survey, four adaptive pairwise choices selected by maximum expected information gain (EIG), a bounded text interview, participant corrections, and up to two approved single-detail condition comparisons ordered via a native Muse tool call. See [the simple study guide](docs/simple-study.md), [the integrated study guide](docs/adaptive-interviews.md), [the Muse demonstration guide](docs/muse-demonstration.md), and [the product direction](docs/product-direction.md).
- **Evidence workbench (`v1`):** Imports source excerpts (`statement`, `observed`, `hypothetical`), maps them to four competing explanations, runs three independent text-only Muse design critiques plus an optional separate prototype screenshot review, and compiles six pairwise controlled choices with a neutral practice task, genuine outside option, and reversed-side holdout. (In this legacy controlled-choice engine, stimuli are templated text tables and `muse-image-1.0` is not used so pairwise attributes remain strictly tabular.)

### Seeded Choice-Engine Diagnostic Benchmark

The deterministic choice engine includes a reproducible simulated-participant benchmark (measuring in-model Bayesian EIG question selection vs. fixed and random policies across 2,000 simulated participants; no API calls required):

| Four-round policy | Top-1 recovery | Mean Brier ↓ | Probability on true driver |
|---|---:|---:|---:|
| **Adaptive EIG** | **91.60%** | **0.0333** | **86.86%** |
| Fixed | 81.10% | 0.0689 | 71.99% |
| Random | 79.30% | 0.0721 | 72.15% |

*Note: This benchmark evaluates the deterministic 6-pair choice engine ([`docs/benchmark-results.json`](docs/benchmark-results.json)), not the Research Studio AI moderator. A misspecified simulation with continuous mixed preferences, variable noise, 8% attention lapses, and 6% left-side bias yields 60.3% adaptive recovery vs. 55.0% fixed. See [`docs/evaluation-status.md`](docs/evaluation-status.md), [`docs/review-evaluation-protocol.md`](docs/review-evaluation-protocol.md), [`docs/sustainability-research-basis.md`](docs/sustainability-research-basis.md), and [`docs/field-validation-protocol.md`](docs/field-validation-protocol.md).*

---

## Testing & Verification

154 Python unit/integration tests and 5 JavaScript test suites verify schema validation, immutable approvals, single-cell comparison audits, probe caps, zero-finding inconclusive reports, WebSocket ticket scoping, PCM resampling, and localhost origin/host guards:

```powershell
# Run the Python test suite (154 tests)
python -m unittest discover -s tests -v

# Run the JavaScript UI & audio/voice controller checks
node tests/research_ui.test.cjs
node tests/report_copy.test.cjs
node tests/spoken_turn.test.cjs
node tests/spoken_moderator.test.cjs
node tests/pcm_worklet.test.cjs

# Run deterministic choice-engine benchmarks
python -m choicegap.benchmark --participants 2000 --output benchmark-results.json
python -m choicegap.workbench_benchmark --participants 2000 --output outputs/workbench-benchmark.json
```

---

## Project Map

```text
choicegap/studio.py               Research Studio workflow: brief-led generation, bounded probes, member check, synthesis
choicegap/studio_capabilities.py  Muse web_search background, Muse Image generation/edit, native tool comparison, clip review
choicegap/voice_stream.py         Capability-scoped local WebSocket relay to Muse Voice Transcribe realtime ASR
choicegap/meta.py                 Meta Model API client (structured outputs, reasoning effort, tool calls)
choicegap/server.py               Local HTTP server, origin/host guards, and REST endpoints
choicegap/research.py             SQLite store, workspace approval, and legacy evidence workbench
choicegap/muse_research.py        Version-2 interview evidence schema and native comparison selection
choicegap/explore.py              Bounded exploratory interview follow-ups for the legacy workbench
choicegap/mechanisms.py           Single-detail condition comparisons for the legacy workbench
choicegap/review.py               Multimodal pre-fieldwork confound critique (text + screenshot)
choicegap/engine.py               Bayesian choice model, EIG selector, and session state
choicegap/dynamic.py              Generic 4-hypothesis / 6-pair compiler and structural audit
choicegap/benchmark.py            Simulated-participant benchmark for the preset choice engine
choicegap/workbench_benchmark.py  Shipped-engine simulation, holdout, and misspecified diagnostics
choicegap/review_benchmark.py     Frozen 18-case multimodal design-review evaluation harness
static/                           Research Studio (studio.html, studio.js, moderator-avatar.js) & legacy workbench UI
tests/                            154 Python unit tests and 5 Node.js test suites
docs/                             Audit report, architecture notes, validation protocols, and hackathon plan
```

---

## Data Handling, Claims & Deployment Boundaries

- **Scientific claims boundary:** ChoiceGap reports which explanations are most consistent with observed responses under the presented stimuli and highlights remaining uncertainty. It does not infer stable personality traits, diagnose psychological biases, claim causal proof from small unrepresentative samples, or equate hypothetical choices with real-world purchases.
- **Privacy & storage:** The app sends researcher briefs, attached stimuli, submitted responses, and optional audio/video clips to Meta Model APIs when those features are invoked. Studies, responses, reviewed task descriptions, and reports are stored in a local unencrypted SQLite database (`work/choicegap-data/research.sqlite3`); raw audio and video bytes are never saved to disk by ChoiceGap.
- **Local-origin security boundary:** The built-in server is designed for single-computer local operation (`127.0.0.1` / `localhost`) without researcher authentication or spend caps, and rejects cross-origin writes and foreign `Host` headers. Public hosting requires authentication, participant isolation, HTTPS/WSS routing, and spend limits.
- **Hackathon submission plan:** See [`docs/hackathon-plan.md`](docs/hackathon-plan.md) and [`docs/choicegap-audit-2026-11-01.md`](docs/choicegap-audit-2026-11-01.md).

## License

MIT
