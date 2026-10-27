# ChoiceGap

ChoiceGap is a research prototype for comparing stated sustainability priorities with choices made under controlled trade-offs. The default study examines grocery-delivery decisions across environmental impact, price, convenience, and claim credibility.

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
5. The audit verifies four accounts, complete pairwise coverage, exactly two varying factors per test, shared held-constant copy, and position randomization.
6. Switch to **Participant view** and run the blind adaptive study.
7. Review the evidence report after data collection.

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

## Test

```powershell
python -m unittest discover -s tests -v
python -m choicegap.benchmark --participants 2000 --output benchmark-results.json
```

The benchmark generates simulated participants with known latent drivers and noisy logistic choices. It compares the adaptive expected-information-gain policy with fixed and random four-question policies. It reports top-1 driver recovery, multiclass Brier score, and probability assigned to the true driver. Seeds are fixed and side placement is randomized reproducibly.

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

The posterior is over four deliberately simple models, not over a person's identity. A “gap” is shown only when at least three responses are informative, the reversed-side holdout is consistent, and the leading behavioural hypothesis differs from the stated driver with at least 45% posterior probability. The report always discloses:

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
static/                 participant and researcher web interfaces
tests/                  deterministic unit and benchmark checks
docs/                   research basis, validation protocol, benchmark, and submission plan
```

The sustainability choices and claims boundary are grounded in `docs/sustainability-research-basis.md`. The path from prototype to incentive-compatible research, design-specific power simulation, and mixed-logit analysis is specified in `docs/field-validation-protocol.md`.

## Data handling and deployment boundary

- Session state is held in memory and is cleared when the server restarts.
- The interface does not request direct identifiers.
- Free-text statements are excluded from the research-data export.
- When Muse is enabled, study inputs and derived reports may be sent to the configured Meta endpoint.
- The local server has no authentication, encrypted persistence, retention controls, or multi-user isolation. It is not a production deployment.

Hackathon-specific deadlines and presentation work are isolated in `docs/hackathon-plan.md`.

## License

MIT
