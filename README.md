# ChoiceGap

**An adaptive sustainability research agent that tests the gap between green intentions and controlled trade-off choices.**

ChoiceGap is a working vertical slice for the Meta Global AI Developer Hackathon 2026. The evidence-backed preset studies sustainable grocery delivery: a respondent states what matters, then chooses between controlled alternatives that trade environmental impact against affordability, convenience, and credibility of green claims. Each choice updates competing explanations, and Muse selects the next falsification test. The report separates evidence from speculation.

The preset is no longer the boundary of the product. In Researcher view, a researcher can describe a completely different decision problem in natural language. Muse compiles it into four non-overlapping falsifiable accounts and concrete binary factor levels. Deterministic code then constructs all six pairwise trade-offs and refuses to run the generated study unless it passes structural controls.

The participant experience is intentionally blind by default: it does not expose live hypotheses, information gain, uncertainty, model status, or experiment rationale while choices are being collected. An explicit researcher view reveals those mechanics, and analysis appears only in a post-study debrief. This reduces priming and demand effects in the demo design.

## Why this is more than a survey

```text
stated preference → competing hypotheses → adaptive controlled choice
       ↑                                             ↓
       └──────── cautious evidence report ← Bayesian update
```

- **Muse Spark 1.3 intake:** maps free text to a declared driver without pretending it observed behaviour.
- **Muse Spark 1.3 study compiler:** turns an open research context into four testable explanations and displayable factor levels using constrained JSON—not arbitrary survey prose.
- **Muse Spark 1.3 falsification loop:** stages a duel between the leading explanation and its strongest rival, chooses one of three high-information validated experiments, and pre-registers what result would count against its current belief. The engine rejects invented experiment IDs.
- **Deterministic evidence layer:** compiles a complete six-pair design, audits controls and coverage, then owns choice likelihoods, posterior updates, side randomization, and information gain.
- **Muse Spark 1.3 synthesis:** turns computed evidence into a concise report under an explicit no-causality schema.
- **Safe fallback:** the full study works without an API key, making the demo resilient.

The stated-attitude measurement and behavioural inference are intentionally separate. Participants rate every factor plus a general lower-impact intention item; the behavioural posterior still begins uniform. Muse may interpret optional free text, but it cannot overwrite the structured ratings or probability update.

Muse Image is intentionally not used in this slice: generated visuals would add an uncontrolled stimulus and weaken the experimental claim.

### Why Muse is essential rather than decorative

This is not a chatbot wrapper. Muse converts ambiguous respondent language into a testable account, reasons over competing explanations and experiment metadata, and makes an auditable falsification commitment before each observation. Deterministic code owns probabilities and validation; Muse owns semantic interpretation and adversarial experiment strategy. That combination lets the agent adapt without allowing fluent model output to masquerade as evidence.

### Dynamic study workflow

1. Open **Researcher view**.
2. Describe a decision, population, and uncertainty in the Muse study compiler.
3. Muse returns four structured candidate explanations with concrete high/low levels.
4. The local compiler produces the six unique pairwise duels.
5. The audit verifies four accounts, complete pairwise coverage, exactly two varying factors per test, shared held-constant copy, and position randomization.
6. Switch to **Participant view** and run the blind adaptive study.
7. Open the researcher debrief only after data collection.

## Run locally

Requires Python 3.10+ and no third-party packages.

```powershell
$env:MODEL_API_KEY = "your-key"
python -m choicegap.server
```

Open <http://127.0.0.1:8000>. Set `META_MODEL` to override the default `muse-spark-1.3`. Without `MODEL_API_KEY`, the app runs in deterministic local mode and clearly labels that state.

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

This benchmark validates the inference mechanism under its own stated data-generating assumptions. It does **not** establish external validity with humans.

Generated studies receive a structural design audit, not automatic domain validation. A human researcher must still review whether Muse selected the right explanations and realistic factor levels before recruiting participants.

## Method and guardrails

The candidate set is a small fractional-factorial-style library of paired choices. Each pair either holds all but one attribute constant or presents a clearly disclosed two-attribute trade-off. Product names are neutral, copy is templated, and left/right order is randomized. This reduces obvious wording and position confounds; it does not eliminate hypothetical-choice bias.

The posterior is over four deliberately simple models, not over a person's identity. A “gap” is shown only when the leading behavioural hypothesis differs from the stated driver and exceeds 45% posterior probability. The report always discloses:

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
static/                 demo UI
tests/                  deterministic unit and benchmark checks
docs/                   benchmark snapshot and hackathon execution plan
```

The sustainability choices and claims boundary are grounded in the cited evidence review at `docs/sustainability-research-basis.md`.

## Three-minute demo path

1. **0:00–0:25 — Problem:** surveys capture stated preference; product choices often expose a different trade-off.
2. **0:25–1:30 — Live study:** state “environmental impact,” then make realistic delivery choices where fees, timing, and claim credibility create friction. Show Muse choosing falsification tests.
3. **1:30–2:10 — Report:** point to the gap, posterior, evidence trail, and limitations. Say “support,” never “prove.”
4. **2:10–2:40 — Technical depth:** structured Muse outputs + constrained orchestration + Bayesian EIG + randomized controlled stimuli.
5. **2:40–3:00 — Validation/impact:** show the reproducible benchmark; explain how sustainability teams can test food, travel, energy, packaging, fashion, and circular-economy say–do gaps.

## Hackathon status

This repository contains new work begun on 26 October 2026. Before submission, publish the repository, record the three-minute demo, run the live-key smoke test, and include the benchmark output. Submission deadline supplied by the participant guide: **4 November 2026 at 9:00 PM ET**.

## License

MIT
