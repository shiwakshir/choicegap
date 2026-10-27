# Sustainability research basis

ChoiceGap is oriented around the sustainability **intention–behaviour** (or **say–do**) gap. The default scenario is grocery delivery because it makes high-frequency trade-offs legible without claiming that a four-choice demo measures real-world carbon behaviour.

## Evidence used in the design

- An OECD study of 37,000 consumers across 40 countries found that trust and environmental beliefs shape willingness to pay for sustainability claims, while understanding of claims is limited and varies across countries. This supports separating **impact magnitude** from **claim credibility** rather than treating “green” as one factor. [OECD, 2025](https://www.oecd.org/en/publications/how-do-consumers-interact-with-environmental-sustainability-claims-on-food_0587c663-en.html)
- A randomized online food study with 3,074 UK participants found that reflection paired with choice architecture outperformed classic nudges on sustainable dietary intentions. This motivates asking for an explicit priority before the adaptive choice sequence, while keeping the participant free to contradict it. [Nature Sustainability, 2023](https://www.nature.com/articles/s41893-023-01235-0)
- A randomized controlled trial in an experimental online supermarket tested availability and positioning with 1,179 participants, reinforcing that the choice environment—not attitudes alone—shapes sustainable selection. [Appetite, 2024](https://doi.org/10.1016/j.appet.2024.107579)
- A natural field experiment on Fair Trade coffee found that a 20% price reduction increased sales while added information and moral appeals did not. This supports price as a rival behavioural explanation instead of assuming more sustainability information will close the gap. [Social Science Research, 2015](https://doi.org/10.1016/j.ssresearch.2015.02.007)
- An incentivized sustainable-fashion experiment distinguishes stated from revealed preference and reports that price, perceived quality, design, and prior experience can alter whether intentions translate into willingness to pay. [Scientific Reports, 2025](https://www.nature.com/articles/s41598-025-23008-9)
- Across 20 experiments with 16,114 participants, hypothetical nudges usually recovered the direction of real-world effects but produced noisy effect magnitudes. The app therefore treats hypothetical choices as directional evidence and explicitly refuses cost-benefit or causal claims. [Communications Psychology, 2025](https://www.nature.com/articles/s44271-025-00339-x)
- A last-mile delivery discrete-choice study found that respondents disliked delays and emissions but accepted longer waits for lower-impact delivery, with meaningful heterogeneity across respondents. This supports adaptive rather than one-size-fits-all questioning. [Transportation Research Part D, 2021](https://doi.org/10.1016/j.trd.2021.102863)
- A simulated online-shopping experiment found that disclosing delivery emissions could shift people away from expedited shipping, with an effect comparable to price discounts. This supports testing impact information against convenience and price rather than studying each in isolation. [Sustainable Production and Consumption, 2022](https://doi.org/10.1016/j.spc.2022.09.014)
- Good-practice guidance for discrete-choice experiments requires explicit objectives, defensible attributes and levels, sufficient independent variation, balance, and attention to respondent fatigue and comprehension. ChoiceGap uses a small pairwise candidate set for hypothesis discrimination, not population-level utility estimation. [ISPOR Experimental Design Task Force](https://www.valueinhealthjournal.com/article/S1098-3015%2812%2904162-9/fulltext)

## Default rival explanations

1. **Environmental impact:** the respondent selects a materially lower estimated delivery footprint.
2. **Affordability:** delivery fees override the environmental intention.
3. **Convenience:** a precise delivery window overrides the environmental intention.
4. **Claim credibility:** independent verification matters more than the claimed reduction itself.

The six preset experiments cover every pair of these four explanations once. Each comparison changes two factors in opposite directions and holds the remaining factors constant. Left/right position is randomized.

## Question architecture

The participant no longer selects one forced “most important” factor. Before the choice tasks, they rate all four factors on the same five-point importance scale and separately respond to a lower-impact-delivery intention item. The behavioural model starts uniform: stated ratings do **not** seed its posterior. This prevents the analysis from manufacturing alignment with the survey response. Product names and trade-off-revealing titles are hidden; participants see neutral Option A/Option B profiles, while the researcher view preserves the target contrast and falsification rule.

The four adaptive choices are intentionally a rapid diagnostic rather than a conventional DCE claiming population preference weights. The app includes a neutral practice check, repeated holdout, and opt-out/current-choice alternative. Production use still needs cognitive interviewing, a defensible dominant-choice check where realistic, larger samples, and hierarchical or mixed-logit estimation.

The application does not diagnose an individual behaviour gap from hypothetical tasks. A descriptive rating–choice comparison requires at least three informative choices, a consistent repeat and sufficient separation under the candidate models. A skipped or failed repeat yields an inconclusive report. Rating scales and forced trade-offs measure different constructs, and mixed priorities can invalidate a single-factor interpretation even when posterior probability is high.

## Claims boundary

The demo detects which simple account best predicts choices **under its model and stimuli**. It does not measure actual emissions, establish causal effects, diagnose hypocrisy, or imply that responsibility lies only with consumers. For production research, connect the final choice to a real or incentive-compatible action, preregister the primary contrast, recruit an adequately powered sample, and analyze structural constraints such as availability and access.
