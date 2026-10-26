# ChoiceGap

**An adaptive UX research agent that tests the gap between what people say matters and what their choices support.**

ChoiceGap is a narrow, working vertical slice for the Meta Global AI Developer Hackathon 2026. A respondent states what matters when choosing an AI meeting assistant. The agent maintains four competing hypotheses—trust, control, price, and risk—then selects controlled pairwise trade-offs that maximize expected information gain. Each choice updates a Bayesian posterior. The final report separates evidence from speculation and makes its limitations explicit.

The participant experience is intentionally blind by default: it does not expose live hypotheses, information gain, uncertainty, model status, or experiment rationale while choices are being collected. An explicit researcher view reveals those mechanics, and analysis appears only in a post-study debrief. This reduces priming and demand effects in the demo design.

## Why this is more than a survey

```text
stated preference → competing hypotheses → adaptive controlled choice
       ↑                                             ↓
       └──────── cautious evidence report ← Bayesian update
```

- **Muse Spark 1.3 intake:** maps free text to a declared driver without pretending it observed behaviour.
- **Muse Spark 1.3 falsification loop:** stages a duel between the leading explanation and its strongest rival, chooses one of three high-information validated experiments, and pre-registers what result would count against its current belief. The engine rejects invented experiment IDs.
- **Deterministic evidence layer:** choice likelihoods, posterior updates, side randomization, and information gain are inspectable Python.
- **Muse Spark 1.3 synthesis:** turns computed evidence into a concise report under an explicit no-causality schema.
- **Safe fallback:** the full study works without an API key, making the demo resilient.

Muse Image is intentionally not used in this slice: generated visuals would add an uncontrolled stimulus and weaken the experimental claim.

### Why Muse is essential rather than decorative

This is not a chatbot wrapper. Muse converts ambiguous respondent language into a testable account, reasons over competing explanations and experiment metadata, and makes an auditable falsification commitment before each observation. Deterministic code owns probabilities and validation; Muse owns semantic interpretation and adversarial experiment strategy. That combination lets the agent adapt without allowing fluent model output to masquerade as evidence.

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
| Adaptive EIG | **89.95%** | **0.0409** | **83.74%** |
| Fixed | 79.80% | 0.0719 | 71.00% |
| Random | 79.45% | 0.0739 | 71.04% |

The adaptive policy gains **10.15 percentage points** over the fixed sequence in this seeded simulation. The committed raw result is in `docs/benchmark-results.json`.

This benchmark validates the inference mechanism under its own stated data-generating assumptions. It does **not** establish external validity with humans.

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
choicegap/meta.py       Meta Model API structured-output client
choicegap/server.py     dependency-free local web server and API
choicegap/benchmark.py  objective simulated-participant evaluation
static/                 demo UI
tests/                  deterministic unit and benchmark checks
docs/                   benchmark snapshot and hackathon execution plan
```

## Three-minute demo path

1. **0:00–0:25 — Problem:** surveys capture stated preference; product choices often expose a different trade-off.
2. **0:25–1:30 — Live study:** state “control,” then choose cheaper or lower-retention options. Show Muse selecting each next test and uncertainty updating.
3. **1:30–2:10 — Report:** point to the gap, posterior, evidence trail, and limitations. Say “support,” never “prove.”
4. **2:10–2:40 — Technical depth:** structured Muse outputs + constrained orchestration + Bayesian EIG + randomized controlled stimuli.
5. **2:40–3:00 — Validation/impact:** show reproducible simulated benchmark; explain how teams could test onboarding, pricing, privacy, or AI-control trade-offs.

## Hackathon status

This repository contains new work begun on 26 October 2026. Before submission, publish the repository, record the three-minute demo, run the live-key smoke test, and include the benchmark output. Submission deadline supplied by the participant guide: **4 November 2026 at 9:00 PM ET**.

## License

MIT
