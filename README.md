# ChoiceGap

ChoiceGap is an adaptive UX research prototype. Its product direction is to combine surveys, text interviews and choice tasks, then give researchers an evidence-linked analysis of stated priorities, study responses, possible explanations and practical next steps. Sustainability is the first context.

The current implementation combines a short survey, adaptive controlled choices, a bounded text interview, participant corrections, and up to two single-detail condition comparisons. The researcher report links statements, task responses, corrections, rival explanations and proposed next tests. See [the product direction](docs/product-direction.md) and [the integrated study guide](docs/adaptive-interviews.md). Separate behavioural experiments are an advanced option.

Updated 30 October: newly approved interviews use the complete session as Muse evidence. A bounded native tool call can choose the order of the two approved comparisons. Muse then reviews the first result and the final responses, preserving source references and the actual earlier reading. At most four calls are made per normal completed interview; no new participant questions were added. Existing version-one approvals retain their narrower one-call protocol. See [the Muse demonstration guide](docs/muse-demonstration.md).

To try the full flow, restart the server and open Researcher view. Select **Set up this study**, review the prepared survey/interview plan and delivery details, confirm, then **Create participant link**. Open it in another tab, complete the study, and return to **View findings**. No imported evidence or hypothesis configuration is needed. See [the simple study guide](docs/simple-study.md).

Evidence import, editable designs and model-review controls remain under **More settings and detailed research tools**. Previously approved studies retain their original flow; create a new draft to add interviews. The participant link is local to the computer running the app.

The researcher workbench now supports an evidence-to-follow-up workflow: import source excerpts, review competing explanations, approve exact factor levels, collect adaptive choice responses, and export a study decision brief with proposed field contrasts.

## Evidence workbench

Updated 28 October: design review runs three times independently of the screenshot, with a separate optional visual review. Broad topic frequency is run consistency, not confidence. The brief leads with per-task counts and separate denominators; model leaders are secondary. Individual headlines contain no rating-mismatch claim. Opening EIG ties and the repeated task are seeded and randomized independently of the inferred leader. Repeat disagreement is descriptive and never excludes a session.

For the detailed workflow, open <http://127.0.0.1:8000/?mode=researcher>, expand **More settings and detailed research tools**, and use **Resolve a research decision**:

1. Enter the product decision and paste one evidence excerpt per line using `type | source label | excerpt`. Supported types are `statement`, `observed` (a researcher-reported action), and `hypothetical`.
2. Select **Map evidence and draft follow-ups**. With Muse enabled, the model maps sources to explanations and identifies missing or contradictory evidence. Without an API key, sources are preserved without automatic semantic assignments; the researcher assigns relationships manually.
3. Review each source relationship, explanation, missing-evidence note, and exact factor level. Source IDs and verbatim quotations are validated; their interpretation and provenance are not independently verified.
   Select **Challenge this design with Muse** for three independent text-only design reviews and, if attached, one separate screenshot review. Broad topics show how many completed design runs raised them; this is consistency, not confidence or identical findings. Results and errors remain visible per run. A local Meta key is required. Image bytes are not saved, and all interpretations need researcher review.
4. Approve the design. Its source map and blueprint are locked, hashed, and saved. Drafts cannot be used for participant collection. Create a new draft for changes to an approved design.
5. Open the participant link and collect responses. Return to the workbench to refresh the decision brief, inspect individual cases, and export the research packet.

Muse review is advisory and does not approve a design. Its input digest is checked when the researcher approves or exports the design; later edits are labelled as not covered by the saved review. The model's source, findings, and optional screenshot digest are included in the decision brief. See `docs/meta-model-role.md` for the capability mapping and submission rationale.

**Load fictional example** supplies clearly labelled demonstration data, so the workflow can be evaluated without recruiting researchers or participants. It does not provide evidence of real product demand, model interpretation quality, or time savings.

The first workbench is scoped to grocery delivery and four editable factor levels. Omitted explanations are recorded as unresolved questions; they are not silently forced into one of the four models. The generated field contrasts change one factor at a time and are proposals only. The application does not execute randomized field experiments or calculate a defensible sample size for them.

The software does not infer a stable personal trait or claim that a short hypothetical study reveals real-world behaviour. It reports which of four prespecified choice models is most consistent with the observed responses under the presented stimuli.

Participant mode does not expose hypotheses, information gain, uncertainty, model status, or experiment rationale while responses are collected. Researcher mode exposes the model state and can compile another sustainability decision context into four candidate explanations and six pairwise experiments. Generated studies must pass structural checks before they can run.

## Architecture and responsibility boundaries

```text
stated preference → competing hypotheses → adaptive controlled choice
       ↑                                             ↓
       └──────── cautious evidence report ← Bayesian update
```

- **Muse evidence mapping:** interprets supplied excerpts within four predefined, editable grocery-delivery categories. Omitted explanations remain unresolved.
- **Muse design review:** reads source quotes, exact study levels and an optional prototype screenshot together, identifying possible confounds and suggested controls before fieldwork.
- **Computed baseline question selection:** maximum expected information gain selects each baseline task and records the predicted disagreement before observing a response. Baseline selection makes no model call; enabled version-two interviews use Muse for bounded comparison ordering and result reviews.
- **Deterministic evidence layer:** compiles a complete six-pair design, audits controls and coverage, then owns choice likelihoods, posterior updates, side randomization, and information gain.
- **Computed reporting:** preserves exact tested levels and distinguishes hypothetical choices from reported actions. Source interpretations and new session results appear side by side without assuming participant matching.
- **Deterministic operation:** the fixed study works without an API key.
- **Research quality layer:** neutral practice example, genuine outside option, reversed-side holdout, and de-identified JSON export.

Participants rate every factor plus a general lower-impact intention item; the choice-model posterior begins uniform. Baseline task selection and numerical analysis make no model calls. In a version-two interview, Muse receives the survey, exact choices and interview responses for a tentative interpretation with an exact quoted span. After participant correction it can select an existing approved comparison through a validated tool call, then review the first result and final response. Local mode uses literal text and computed ordering. Free text and corrections appear in the integrated export.

The repeat samples a completed informative task uniformly using a seeded draw independent of the inferred leader, then reverses its sides. Agreement is descriptive: it does not filter sessions or update probabilities. Outside selections also leave probabilities unchanged.

Muse Image is not used in this prototype because generated visuals would add an uncontrolled stimulus.

### Model boundary

Muse performs bounded semantic interpretation, pre-fieldwork review, approved-comparison ordering and evidence-linked reconsideration. Code owns baseline question selection, study validation, allowed-task checks, likelihoods, probability updates, randomization and descriptive reporting. A model response cannot override an inconclusive numerical result or introduce an unvalidated experiment. Legacy standalone compiler/API methods remain for compatibility but are hidden from the main researcher workflow.

### Dynamic study workflow

1. Open **Researcher view**.
2. Describe a decision, population, and uncertainty in the Muse study compiler.
3. Muse returns four structured candidate explanations with concrete high/low levels.
4. The local compiler produces the six unique pairwise experiments.
5. The audit checks four accounts, complete pairwise coverage, binary factor levels, two varying factors per test, unique experiment IDs, and exact agreement between displayed copy and encoded levels.
6. Open the generated participant link in a separate tab. Published designs and their links are saved locally and survive a server restart.
7. Return to the researcher console and select **Load completed sessions** to open a report.

Every completed report includes a decision trail: the plan recorded before each response, computed choice probabilities for all four models, the exact displayed stimuli and their SHA-256 digest, option orientation, and posterior probabilities before and after the response. Entropy may increase after an unexpected answer; the trail preserves that outcome. The digest identifies the recorded payload; it does not provide an external timestamp or independent preregistration.

The server owns question order and orientation. Each issued question has a one-use response token. Replayed answers, out-of-order responses, and responses for an unissued experiment are rejected before evidence is updated.

## Run locally

Requires Python 3.10+ and no third-party packages.

```powershell
$env:MODEL_API_KEY = "your-key"
python -m choicegap.server
```

Open <http://127.0.0.1:8000>. Set `META_MODEL` to override the default `muse-spark-1.3`. Without `MODEL_API_KEY`, the app runs in deterministic local mode and clearly labels that state.

Alternatively save `MODEL_API_KEY=your-key` in a local `.env` file in the project folder. The server reads that file at startup; existing environment variables take precedence. The file is excluded from Git and source ZIPs. Do not include keys in shared research packets.

Participant mode is the default and contains no researcher controls or debrief access. Open <http://127.0.0.1:8000/?mode=researcher> for the researcher console.

Meta Model API configuration follows the official OpenAI-compatible endpoint:

- Base URL: `https://api.meta.ai/v1`
- Endpoint: `POST /chat/completions`
- Auth: `Authorization: Bearer $MODEL_API_KEY`
- Structured output: `response_format.type = json_schema`

Research data is stored in `work/choicegap-data/research.sqlite3` relative to the server's starting directory. Set `CHOICEGAP_DATA_DIR` to a fixed directory to keep the same store when starting the server from another location. The store is local and unencrypted. Baseline choice sessions remain memory-only. The integrated interview is persisted once the baseline finishes and can reopen in the same browser tab after refresh or restart.

## Test

```powershell
python -m unittest discover -s tests -v
python -m choicegap.benchmark --participants 2000 --output benchmark-results.json
python -m choicegap.workbench_benchmark --participants 2000 --output outputs/workbench-benchmark.json
```

The optional Node check `node tests/research_ui.test.cjs` exercises the quote editor serializer. See `docs/review-evaluation-protocol.md` to prepare or resume the live Muse review evaluation; it requires a local key and uses synthetic inputs.

The original benchmark below is a legacy preset-engine diagnostic. The workbench benchmark evaluates the engine used by approved workbench studies, adds an all-six-pairs baseline, null rating–model mismatch rates, repeat-failure rates, mixed preferences and threshold sensitivity. It uses no model API calls. Its seeded results and limitations are described in `docs/evaluation-status.md`. The Muse review evaluation is specified separately in `docs/review-evaluation-protocol.md` and uses live API calls only when explicitly run.

### Current seeded result

| Four-round policy | Top-1 recovery | Mean Brier ↓ | Probability on true driver |
|---|---:|---:|---:|
| Adaptive EIG | **91.60%** | **0.0333** | **86.86%** |
| Fixed | 81.10% | 0.0689 | 71.99% |
| Random | 79.30% | 0.0721 | 72.15% |

The adaptive policy gains **10.50 percentage points** over the fixed sequence in this seeded sustainability simulation. The committed raw result is in `docs/benchmark-results.json`.

That result is an in-model calibration diagnostic. A misspecified simulation—with continuous mixed preferences, variable noise, 8% attention lapses, and 6% left-side bias—produces **60.3%** adaptive recovery versus **55.0%** fixed. Neither simulation establishes external validity with humans.

Generated studies receive a structural design audit, not automatic domain validation. A human researcher must still review whether Muse selected the right explanations and realistic factor levels before recruiting participants.

## Method and guardrails

The candidate set is a small fractional-factorial-style library of paired choices. Each pair either holds all but one attribute constant or presents a clearly disclosed two-attribute trade-off. Product names are neutral, copy is templated, and left/right order is randomized. This reduces obvious wording and position confounds; it does not eliminate hypothetical-choice bias.

The posterior is over four deliberately simple models, not a person's identity. Tied highest ratings are retained. The 45% threshold is an uncalibrated separation heuristic. Individual headlines make no comparison with importance ratings. The legacy `gap_detected` field stays false; `rating_choice_mismatch` is export-only descriptive metadata. Repeat disagreement does not filter sessions. Task shares are conditional on adaptive assignment, have separate denominators, and cannot be pooled into population preferences. Additive single-factor models cannot estimate interactions. The report always discloses:

1. one respondent and four choices cannot prove causality;
2. conclusions are local to this scenario;
3. omitted explanations can matter;
4. results depend on model and stimulus design.

## Project map

```text
choicegap/engine.py     Bayesian model, experiment design, session state
choicegap/dynamic.py    generic study compiler, audit, and adaptive session
choicegap/meta.py       Meta Model API structured-output client
choicegap/server.py     dependency-free local web server and API
choicegap/benchmark.py  objective simulated-participant evaluation
choicegap/workbench_benchmark.py  shipped-engine simulation and all-six comparison
choicegap/review_benchmark.py     frozen multimodal review evaluation and resume
choicegap/evaluation_report.py    readable reports from recorded results
choicegap/research.py   source validation, approval, decision briefs, SQLite workspaces
choicegap/review.py     validated Muse review of semantic and visual confounds
static/                 participant and researcher web interfaces
tests/                  deterministic unit and benchmark checks
docs/                   research basis, validation protocol, benchmark, and submission plan
```

The sustainability choices and claims boundary are grounded in `docs/sustainability-research-basis.md`. The path from prototype to incentive-compatible research, design-specific power simulation, and mixed-logit analysis is specified in `docs/field-validation-protocol.md`.

## Data handling and deployment boundary

- Baseline choice sessions are memory-only; workspaces, published studies, issued interview follow-ups and completed reports are saved in SQLite.
- The interface does not request direct identifiers.
- Integrated interview exports include survey free text, interview answers and corrections. Review for identifying information before sharing. Legacy choice-only records exclude the intake comment.
- App exports include exact stimuli, decision trails, model source, and returned API token usage when available. Separate evaluation reports estimate token cost using explicitly documented published rates.
- Muse receives imported excerpts and draft study inputs for researcher-requested mapping/review, plus the optional screenshot when requested. A newly approved version-two interview makes at most four calls using survey responses, exact choices, interview answers, corrections and factor definitions. Skipping all interview text makes no call. Version-one approvals retain their original two-answer, one-call scope. Failed/invalid model output falls back to the recorded evidence and approved local ordering.
- Imported excerpts are persisted and may appear in the decision-brief export. Use de-identified material you are authorized to process.
- The local server has no authentication, encrypted storage, retention controls, or multi-user isolation. It is not a production deployment.

The automated and browser evaluation scope is recorded in `docs/evaluation-status.md`.

Hackathon-specific deadlines and presentation work are isolated in `docs/hackathon-plan.md`.

## License

MIT
