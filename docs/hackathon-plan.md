# Submission plan

## Project thesis

ChoiceGap targets one of sustainability research's hardest failures: treating green intention as revealed behaviour. The preset isolates impact, affordability, convenience, and claim credibility in grocery delivery, while Muse can compile the same falsification workflow for food, mobility, energy, packaging, fashion, and circular consumption.

## Evaluation mapping

| Criterion | Weight | Evidence in this repository |
|---|---:|---|
| Impact | 30% | Finds decision tensions earlier than a static survey; reusable across product choices. |
| Meta tooling | 25% | Muse receives computed predictions, selects bounded experiments, and records its challenge before each response. Completed records preserve source and returned token usage. |
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
- [ ] Collect independent UXR feedback if available; external recruitment is not a prerequisite for continuing development
- [ ] Publish this repository publicly
- [ ] Record a three-minute demo
- [ ] Submit before 4 November 2026, 9:00 PM ET

## Three-minute demonstration

1. 0:00–0:25: Show a sustainability intention and the practical trade-offs that can prevent it becoming a choice.
2. 0:25–0:55: Compile a study with Muse. Inspect its concrete factor levels and structural audit, then open its participant link.
3. 0:55–1:45: Complete the four choices and repeated choice without showing research signals to the participant.
4. 1:45–2:30: Reopen the completed report in the researcher console. Expand one decision-trail entry: show the prediction, recorded challenge, actual response, and probability update.
5. 2:30–3:00: Show the in-model and misspecified-model benchmarks together. State that they evaluate deterministic selection, and identify human validation and a Muse-versus-EIG ablation as remaining work.

The evidence-workbench demonstration can start with the labelled fictional corpus, map and review its sources, approve a study, and export a decision brief without external recruitment. Describe it as a workflow demonstration rather than customer validation.

Do not script a guaranteed gap: an inconclusive result should remain visible when the evidence is weak.

## Scientific claims policy

Say “the observed choices are more consistent with…” and “this test reduced uncertainty under the model.” Do not say that four hypothetical choices reveal a true preference, prove a cause, or generalize to a market. Human validation should preregister the primary contrast, randomize order, preserve exact stimulus wording, and analyze more than one respondent.

