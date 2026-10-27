# Field validation protocol

The web demo is a rapid diagnostic. Use this protocol before making behavioural, commercial, or environmental claims.

## 1. Preregister

Freeze the study blueprint, attribute wording, candidate set, primary contrast, exclusion rules, stopping rule, and analysis plan before recruitment. Record the commit SHA and exported study audit. Define whether the target is individual preference recovery, average attribute utility, segment heterogeneity, or a real intervention effect.

## 2. Make one decision consequential

Partner with a retailer, campus service, employer, or delivery provider. Tell participants that one randomly selected choice may be implemented or determine a real voucher, fee, delivery slot, or donation. The implementation probability, budget, and fulfillment process must be disclosed truthfully. Do not describe the current demo as incentive-compatible until this mechanism exists operationally.

## 3. Preserve participant agency

Include the outside option (“keep my usual choice”), avoid moralized wording, and explain data use and withdrawal. Treat repeated outside choices as evidence that the candidate set is incomplete—not as low sustainability motivation.

## 4. Quality controls

- Use the neutral pre-task practice example to confirm participants can compare profile details.
- Repeat one task with sides reversed as a holdout consistency check.
- Add one preregistered dominant-choice attention check only if a clearly dominant profile is realistic.
- Do not automatically exclude an inconsistent respondent; report results with and without the quality filter.
- Pilot wording through cognitive interviews before launch.

## 5. Sample size

Do not use the single-participant posterior as a population estimate. Determine sample size through simulation using the final design, plausible coefficient ranges, expected opt-out rate, desired precision, and planned subgroup/interactions. Report assumptions and simulation code. Simple rules of thumb are not a substitute for design-specific power analysis.

## 6. Population analysis

Export de-identified long-form records from Researcher view. For an adequate sample, estimate a preregistered conditional logit as the interpretable baseline and a mixed logit or hierarchical Bayesian model for preference heterogeneity. Include an alternative-specific constant for the outside option; use effect or dummy coding consistently; cluster repeated choices by respondent; and report uncertainty, model fit, holdout prediction, and sensitivity to exclusions.

Recommended tooling includes R packages such as `apollo`, `mixl`, or `gmnl`, or an equivalent reviewed implementation. The repository intentionally does not manufacture a “mixed-logit result” without participant data.

## 7. Claims

The hypothetical study can identify promising mechanisms and question sequences. Only a real-consequence or field experiment can support claims about observed behaviour, intervention effects, willingness to pay, or emissions avoided. Environmental impact values shown in prototypes must be sourced from the deployment partner’s defensible methodology and labeled with their system boundary.

