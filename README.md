# ChoiceGap

ChoiceGap is a research prototype for comparing stated sustainability priorities with choices made under controlled trade-offs. The default study examines grocery-delivery decisions across environmental impact, price, convenience, and claim credibility.

The researcher workbench now supports an evidence-to-follow-up workflow: import source excerpts, review competing explanations, approve exact factor levels, collect adaptive choice responses, and export a study decision brief with proposed field contrasts.

## Evidence workbench

Open <http://127.0.0.1:8000/?mode=researcher> and use **Resolve a research decision**:

1. Enter the product decision and paste one evidence excerpt per line using `type | source label | excerpt`. Supported types are `statement`, `observed` (a researcher-reported action), and `hypothetical`.
2. Select **Map evidence and draft follow-ups**. With Muse enabled, the model maps sources to explanations and identifies missing or contradictory evidence. Without an API key, sources are preserved without automatic semantic assignments; the researcher assigns relationships manually.
3. Review each source relationship, explanation, missing-evidence note, and exact factor level. Source IDs and verbatim quotations are validated; their interpretation and provenance are not independently verified.
4. Approve the design. Its source map and blueprint are locked, hashed, and saved. Drafts cannot be used for participant collection. Create a new draft for changes to an approved design.
5. Open the participant link and collect responses. Return to the workbench to refresh the decision brief, inspect individual cases, and export the research packet.

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

- **Muse Spark 1.3 intake:** maps free text to a declared driver without pretending it observed behaviour.
- **Muse Spark 1.3 study compiler:** turns an open research context into four testable explanations and displayable factor levels using constrained JSON—not arbitrary survey prose.
- **Muse Spark 1.3 experiment selector:** compares the leading explanation with its strongest rival, chooses one of three validated experiments, and records what result would count against the current leader. The engine rejects unknown experiment IDs.
- **Deterministic evidence layer:** compiles a complete six-pair design, audits controls and coverage, then owns choice likelihoods, posterior updates, side randomization, and information gain.
- **Muse Spark 1.3 synthesis:** turns computed evidence into a concise report under an explicit no-causality schema.
- **Deterministic operation:** the fixed study works without an API key.
- **Research quality layer:** neutral practice example, genuine outside option, reversed-side holdout, and de-identified JSON export.

The stated-attitude measurement and behavioural inference are intentionally separate. Participants rate every factor plus a general lower-impact intention item; the behavioural posterior still begins uniform. Muse may interpret optional free text, but it cannot overwrite the structured ratings or probability update.

The repeated holdout is not used to update beliefs. Outside-option selections also leave the posterior unchanged and are reported as possible evidence that the offered explanations or choices are incomplete.

Muse Image is not used in this prototype because generated visuals would add an uncontrolled stimulus.

### Model boundary

Muse performs bounded semantic interpretation and experiment selection. Deterministic code owns study validation, likelihoods, probability updates, randomization, evidence-quality thresholds, and the candidate experiments available at each turn. A model response cannot override an inconclusive result or introduce an unvalidated experiment.

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

Participant mode is the default and contains no researcher controls or debrief access. Open <http://127.0.0.1:8000/?mode=researcher> for the researcher console.

Meta Model API configuration follows the official OpenAI-compatible endpoint:

- Base URL: `https://api.meta.ai/v1`
- Endpoint: `POST /chat/completions`
- Auth: `Authorization: Bearer $MODEL_API_KEY`
- Structured output: `response_format.type = json_schema`

Research data is stored in `work/choicegap-data/research.sqlite3` relative to the server's starting directory. Set `CHOICEGAP_DATA_DIR` to a fixed directory to keep the same store when starting the server from another location. The store is local and unencrypted. Active, unfinished participant sessions are still held in memory.

## Test

```powershell
python -m unittest discover -s tests -v
python -m choicegap.benchmark --participants 2000 --output benchmark-results.json
```

The benchmark generates simulated participants with known latent drivers and noisy logistic choices. It compares the deterministic adaptive expected-information-gain policy with fixed and random four-question policies. It reports top-1 driver recovery, multiclass Brier score, and probability assigned to the true driver. Seeds are fixed and side placement is randomized reproducibly. It does not call Muse and does not establish that Muse improves experiment selection; that comparison requires a separately budgeted model ablation.

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

The posterior is over four deliberately simple models, not over a person's identity. Importance ratings may be tied, including all equal ratings. All factors with the highest rating are retained as stated priorities. A “gap” is shown only when at least three responses are informative, the reversed-side holdout is consistent, and the leading behavioural hypothesis falls outside those priorities with at least 45% posterior probability. This threshold is a prototype heuristic awaiting empirical calibration. The report always discloses:

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
choicegap/research.py   source validation, approval, decision briefs, SQLite workspaces
static/                 participant and researcher web interfaces
tests/                  deterministic unit and benchmark checks
docs/                   research basis, validation protocol, benchmark, and submission plan
```

The sustainability choices and claims boundary are grounded in `docs/sustainability-research-basis.md`. The path from prototype to incentive-compatible research, design-specific power simulation, and mixed-logit analysis is specified in `docs/field-validation-protocol.md`.

## Data handling and deployment boundary

- Unfinished session state is held in memory and is cleared when the server restarts. Workspaces, published studies, and completed reports are saved in SQLite.
- The interface does not request direct identifiers.
- Free-text statements are excluded from the research-data export.
- Exported records include exact stimuli, decision trails, model source, and returned API token usage when available. There are no API price estimates.
- When Muse is enabled, study inputs and derived reports may be sent to the configured Meta endpoint.
- Imported excerpts are persisted and may appear in the decision-brief export. Use de-identified material you are authorized to process.
- The local server has no authentication, encrypted storage, retention controls, or multi-user isolation. It is not a production deployment.

The automated and browser evaluation scope is recorded in `docs/evaluation-status.md`.

Hackathon-specific deadlines and presentation work are isolated in `docs/hackathon-plan.md`.

## License

MIT
