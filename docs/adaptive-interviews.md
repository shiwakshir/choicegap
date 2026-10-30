# Integrated adaptive UX studies

## Try it

Run `python -m choicegap.server` from the project directory and open http://127.0.0.1:8000. The default demonstration includes the integrated flow. A configured Meta key enables the version-two Muse loop described in [the demonstration guide](muse-demonstration.md). Local mode uses a literal echo and local task ordering.

For a researcher study, open http://127.0.0.1:8000/?mode=researcher, import evidence or load the fictional example, and create a draft. Review the protocol, enable **Include the bounded interview and condition comparisons**, review all factor levels and approve. Share the approved participant link. Old approved studies remain unchanged; create a new draft to add interviews. The approved policy is snapshotted and included in the design digest. A policy mismatch at collection is rejected.

## Participant flow

1. **Ask:** four importance ratings, intention rating and optional contextual comment. Equal ratings are allowed. Review the interview storage, export and Meta-sharing notice.
2. **Observe:** four adaptive hypothetical A/B tasks with a genuine neither option. A randomly selected reversed repeat is descriptive and does not exclude the session.
3. **Explore:** a selected answered task is shown for explanation. Selection prefers a task where a top-rated factor traded against the selected option; otherwise it uses an answered task without assuming a discrepancy. The participant can describe omitted constraints. A second question asks what circumstances, if any, might change their choice, retaining their earlier response as context.
4. **Correct:** if text exists, Muse may propose a tentative, exact-quote-linked interpretation. Without a key or after a failed/invalid model response, the app echoes the participant's actual words. They confirm, correct or leave the description unresolved, and may select a factor or other/unsure. Corrections supersede the model summary while preserving the original for audit.
5. **Compare:** up to two variants of that same baseline task each change exactly one displayed detail using an approved factor level. They test the two differing factors separately. The participant's factor is tested first when eligible; otherwise a choice-model ranking orders them. New display orientation is randomized and normalized back to baseline option identity. Predictions and reasons are recorded before answers. Neither and skip remain distinct; variations do not update the baseline model posterior.
6. **Reflect:** an optional final question asks what explains the choices across versions. A neutral thank-you ends participation.

Version two sends the complete survey, exact baseline choices, interview answers and corrections to Muse. Its native `select_approved_comparison` tool can order the same two code-audited comparisons; it cannot generate stimuli. A participant-selected eligible factor takes precedence. The model records rival explanations and switch/non-switch predictions before the first response. After the first result and after the final response, it can reconsider with evidence references. The final review must cite the latest comparison and any nonempty final reflection. Rejected or unavailable model outputs remain labelled. This adds no participant steps.

The normal loop is capped at four calls: interpretation, planning, first-result review and final review. All-text skips make no calls. Version-one approved studies retain their previous one-call input scope and are not silently upgraded. Their stored protocol remains validated against version one.

The default flow has up to seven choices including the repeat, and four optional text/interpretation stages. There is no claim about a validated completion time. If all baseline choices are neither, the interview still allows explanation but condition tasks are not issued. Questions and comparisons can be skipped. A corrected interpretation requires correction text; unresolved is available without text.

## Researcher analysis

The report presents survey context, exact task responses, the participant's checked explanation, single-detail changes, descriptive switches or non-switches, candidate behavioural lenses, alternatives, and next validation steps. Every case retains exact questions, answers, issued/answered timestamps, branch reasons, stimuli and hashes. Model source, token usage, original interpretation and corrections remain available. Unresolved and untested explanations stay visible.

The study brief includes completed-case analyses, stage-specific issued/answered counts and separate condition rows for identical baseline facts and the same changed detail. Unfinished interviews are counted separately with pending issued stages. Issued does not mean confirmed viewed. Different adaptive branches do not share a denominator, and counts cannot be treated as population prevalence. Neither, skip and missing answers are not evidence of a preference switch.

The behavioural lenses include practical constraints, costs/benefits and claim credibility. The capability/opportunity/motivation framing draws on [Michie, van Stralen and West (2011)](https://link.springer.com/article/10.1186/1748-5908-6-42). It organizes candidate explanations for review; this implementation does not validate COM-B classification or identify a psychological mediator.

## Boundaries

These are within-session hypothetical comparisons. A single-factor edit does not remove order, learning, repeated exposure or carryover effects. A changed choice is not a causal estimate or proof of a unique motive. A non-switch does not establish irrelevance. Only two approved levels are available; the app does not estimate thresholds. Recommendations propose further tests rather than predicting implementation uplift.

There is no live prototype observation, purchase observation or longitudinal outcome linkage. Imported excerpts are not automatically matched to new participants. Participant confirmation is useful clarification, not independent validation. AI paraphrase quality and neutral moderation still need evaluation with people.

Baseline choice sessions are memory-only. From the first interview question onward, state and one-use tokens are persisted; the same tab can reopen after refresh/server restart. Nonce consumption and final report storage are atomic. There is no authentication, encrypted database, multi-user isolation, retention management or cross-device participant authentication. Use de-identified demonstration material in this local prototype.

## Verification

`python -m unittest discover -s tests -q` covers the original app and integrated flow, including quote rejection, corrections, skips, controlled edits, orientation, replay, concurrency, consent and restart behaviour.

`python -m choicegap.explore_benchmark --participants 200` exercises the shipped state machine with labelled scripted responses. It checks exact single-detail edits, switch identity normalization, correction/unresolved handling and all-neither branches. It does not evaluate model semantic accuracy or infer real mechanisms. A separate single live Muse call on fictional text checks the schema and exact quoted span only.
