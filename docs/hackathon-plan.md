# Submission plan

## Project thesis

ChoiceGap targets one of sustainability research's hardest failures: treating green intention as revealed behaviour. The preset isolates impact, affordability, convenience, and claim credibility in grocery delivery, while Muse can compile the same falsification workflow for food, mobility, energy, packaging, fashion, and circular consumption.

## Evaluation mapping

| Criterion | Weight | Evidence in this repository |
|---|---:|---|
| Impact | 30% | Finds decision tensions earlier than a static survey; reusable across product choices. |
| Meta tooling | 25% | Muse Spark performs bounded intake, experiment orchestration, and cautious synthesis through structured outputs. |
| Demo | 25% | One participant journey followed by an evidence report; deterministic operation without an API key. |
| Technical depth | 20% | Bayesian updating, expected information gain, position randomization, constrained agent actions, an in-model benchmark, and a misspecified robustness benchmark. |

## Credit budget

One complete respondent uses six small Muse Spark calls: intake, four planning turns, and report synthesis. Keep prompts compact, log API usage before the final submission run, and reserve most of the $150 credit for benchmark variants and demo rehearsal. Use Standard mode (`muse-spark-1.3`) for research data unless the participant explicitly accepts Contributor mode.

## Before submission

- [x] Working vertical slice
- [x] Deterministic local fallback
- [x] Objective simulated-participant benchmark
- [x] Tests and reproducible seed
- [x] Three-minute demo outline
- [x] Add `MODEL_API_KEY` locally and run the live Meta smoke test
- [ ] Validate with 5–10 humans and record qualitative failure cases
- [ ] Publish this repository publicly
- [ ] Record a three-minute demo
- [ ] Submit before 4 November 2026, 9:00 PM ET

## Scientific claims policy

Say “the observed choices are more consistent with…” and “this test reduced uncertainty under the model.” Do not say that four hypothetical choices reveal a true preference, prove a cause, or generalize to a market. Human validation should preregister the primary contrast, randomize order, preserve exact stimulus wording, and analyze more than one respondent.

