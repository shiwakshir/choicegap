# Evidence workbench: evaluation status

## Integrated adaptive UX study, 28 October

The current suite passes 96 Python tests plus the Node source-quote editor check and JavaScript syntax checks. The new integrated path covers survey context, adaptive tasks, a task-anchored bounded interview, one tentative Muse interpretation, participant corrections, two approved single-detail variations, final reflection and an evidence-linked report. Old choice-only sessions remain supported without participant model calls.

The scripted integrated-flow benchmark passes 400 exact single-fact audits and 400 known switch-label checks across 200 synthetic sessions, preserves 100 supplied corrections, leaves 100 unresolved interpretations unadopted, and checks 200 all-neither/skip branches. These are objective software checks of supplied responses, not recovery of latent human motives or measurement of research validity. Results: `adaptive-interview-benchmark-results.json`.

One new actual Muse call on explicitly fictional interview text passed the strict schema and exact-quotation checks. This is a smoke test, not an estimate of semantic accuracy, neutral moderation, reliability or model superiority. The output is `outputs/adaptive-interview-live-smoke.json`.

A browser walkthrough completed the survey, five baseline/repeat choices, two optional interview answers, an interpretation correction, both condition comparisons and a final reflection. The participant saw a neutral thank-you. A separate actual HTTP check completed two fictional automated sessions in an approved dynamic study, including unresolved/skip responses. The researcher UI showed per-case corrections, exact condition edits, conditional switch counts and stage-specific issued/answered denominators. Markdown export completed. No browser console errors were observed in that walkthrough. These checks use isolated fictional data and do not establish product demand, human usability, or time saved.

Baseline choice sessions remain memory-only. Interview-stage state is durable with atomic nonce consumption and final report storage. Tests cover restart/replay/concurrency, invalid quote fallback, correction precedence, neutral unresolved branches, consent and prevention of participant-enabled interviews on an unapproved protocol.

The remaining sections describe earlier revisions and evaluations; their older suite counts and zero-call participant claims apply to the legacy choice-only path.

## Current revision: 28 October

The application now runs separate design and visual reviews, removes rating-mismatch wording from per-session headlines, randomizes opening EIG ties, and samples the repeat uniformly from completed informative tasks independently of the inferred leader. Repeat disagreement is descriptive and never excludes a session. The brief leads with per-task canonical counts, separate recorded-response denominators and conditional shares; model leader counts are secondary and cannot estimate interactions.

The revised 2,000-session-per-condition simulation has in-model adaptive repeat disagreement of 20.4%, 19.4%, 22.8%, and 21.0% for factors a/b/c/d, with no repeat-based exclusions. Initial task counts span all six pairs (314–349 sessions per pair). This is a software/simulation diagnostic, not a claim of fairness or validity in real people. In-model recovery remains 93.35%; mixed-dominant recovery is 60.8% and no-deliberate-dominant recovery is 34.95%. The weak mixed-model performance remains visible rather than being filtered away.

The current verification suite has 69 Python tests plus the Node quote-editor check. A frozen neutral-instruction evaluation with new feature families is specified in `neutral-review-protocol.md`. All 57 calls completed without API or validation errors. All 36 planted visual calls returned findings and the fixed keyword screen matched 34; all 18 intended-neutral visual calls also returned findings, including common design caveats. These counts are not adjudicated detection or false-alarm rates. All three independent design runs returned findings. Aggregate data is in `neutral-review-results.json`; raw calls and images accompany the archive. All spot checks by this assistant and the supplied Claude review are model-based checks by AI agents, not human adjudication.

A fresh browser check verified primary per-task counts/denominators, secondary model counts and repeat caveats using isolated fictional data. A clearly labelled replay of recorded evaluation responses verified the three design critiques, separate prototype review and topic-frequency language. Console errors were absent. Screenshots of these verification states are included in the output bundle; no new model calls were made by those browser checks.

The sections below document earlier verification and the 27 October methods. Their repeat-based filtering and numerical results are historical, not the current exclusion policy. The revised benchmark is saved separately to preserve that comparison.

The product workflow is evaluated without requiring external UXR recruitment. Automated checks and a browser walkthrough establish specific software properties; they do not establish product demand or replace a study with researchers.

## Verified software properties

- Imported sources retain separate types for statements, reported actions, and hypothetical responses.
- Source labels do not automatically link records to the same participant.
- Unknown source IDs and quotations absent from the cited source are rejected.
- Source type is taken from the original record, not from model output.
- Local mode leaves semantic source relationships unassigned.
- An explicit review confirmation is required to publish an evidence-workbench study.
- Draft workspaces cannot be used for participant collection.
- Approved designs cannot be overwritten through the application; their approved inputs have a SHA-256 digest.
- Each proposed field contrast varies exactly one factor and lists three held-constant factors.
- Workspaces, published links, and completed reports persist in SQLite.
- Study summaries exclude other studies and do not count failed response checks as model support.
- Existing replay, option-orientation, opt-out, holdout, and weak-model-separation safeguards remain covered.

Run all automated checks with:

```powershell
python -m unittest discover -s tests -v
```

The current implementation completes 61 Python tests successfully, including the existing choice-engine tests. The Node editor check additionally verifies exact quote spans, multiple relationships to the same source and rejection of invented quotations. These are regression checks, not research-quality scores. New checks exercise the actual dynamic workbench engine, all-six coverage, descriptive reporting, and zero model requests during configured participant sessions.

The Muse design-review integration additionally checks:

- Native image content is sent in a user message alongside the evidence and proposed design.
- Strict structured output and high reasoning effort are set on the review request.
- Image findings are rejected if no image was supplied.
- Text findings require valid source IDs and verbatim quotations.
- Image bytes are absent from persisted review records; only metadata and a digest are saved.
- Changes to the design invalidate the saved review's current-input flag.
- Offline mode reports that a Meta key is required rather than fabricating a review.

The review display and stale-input behavior were checked in the browser using findings explicitly labelled as a test fixture, not a live model response. This verifies presentation and state handling only.

For the latest revision, a real HTTP walkthrough additionally checked exact quote spans (including two different relationships to one source), approved study loading, four outside responses, an inconclusive report and the source-linked brief. The quote editor serializer was exercised directly in Node. A new visual browser walkthrough was unavailable because the browser automation tool failed to initialize; the earlier browser observations above refer to the previous revision.

## Browser walkthrough

A local walkthrough used the clearly labelled fictional grocery-delivery corpus, with Meta calls disabled:

1. Load the fictional evidence and create a draft.
2. Assign source relationships manually and approve the factor definitions.
3. Verify the design becomes locked and a participant link is generated.
4. Open that link in participant mode.
5. Complete a test session using the outside option throughout.
6. Refresh the study brief: it records one completed session, zero sessions passing response checks, and zero supported model leaders.
7. Restart the server and reopen the approved workspace, participant link, and study brief.
8. Download the decision brief.

The walkthrough produced no JavaScript console errors. The deliberately uninformative session remained inconclusive after restart.

## What remains unmeasured

- Live Muse evidence-mapping accuracy, especially whether support and challenge relationships are interpreted correctly.
- Live Muse visual-review accuracy and whether its suggested controls improve a researcher's study design.
- Researcher planning time and methodological quality relative to their usual tools.
- Researcher willingness to use or pay for the product.
- Human comprehension and realism of the default or revised stimuli.
- Participant question selection is now deterministic; no added value from model selection is claimed.
- Population prevalence, real adoption outcomes, and causal intervention effects.

The fictional corpus supports repeatable software checks and demonstration. It must not be presented as customer research or evidence of adoption barriers in a real population.

## New workbench simulation

`python -m choicegap.workbench_benchmark` evaluates the shipped grocery blueprint and `DynamicSession`, with 2,000 simulated sessions per population/policy. Four adaptive tasks plus one repeat recovered the generating account in 93.35% of in-model sessions; all six pairs plus one repeat recovered it in 93.15%. The small difference is simulation variation, not an accuracy-superiority claim. Adaptive uses two fewer tasks.

Under continuous mixed dominant weights, recovery is 62.45% adaptive versus 61.25% all-six. Adaptive repeat failure is 41.85%. Among passing null-cohort adaptive sessions, 20.46% show a rating–model mismatch despite ratings matching the generating main preference; with no deliberately dominant preference the rate is 39.30%. Thresholds from .45 through .90 do not reduce these adaptive rates. All cohorts, assumptions, sensitivity results, and denominators are in the raw output. This independent simulation does not reproduce Claude's exact percentages because its scripts were not supplied.

The result supports removing automatic behaviour-gap diagnosis; it does not justify a calibrated probability claim. `gap_detected` remains false in new exports for compatibility. Descriptive comparison and model probabilities remain available with limitations and tested levels.

The new visual review evaluation includes 18 frozen screenshots, six clean controls, three repeats and two input conditions. Prepared cases, fixture tests and live measurements are different statuses. See `review-evaluation-protocol.md` and the output run summary for the actual execution status.

## Recorded Muse run

The final v4 development run completed 108/108 calls on `muse-spark-1.3`, with no API errors or validation failures. In the image condition the fixed visual-basis keyword rule matched 32/36 planted calls; 0/18 clean image calls returned findings. Text-only produced findings in 10/18 clean calls, but these include source/design caveats and are not automatically false alarms. The keyword rule excludes text-only image-basis matches by definition, so its condition difference is not an unbiased semantic accuracy lift. Missing primary human adjudications remain missing.

An unblinded Codex development spot check reviewed one recorded example per planted screen and recorded observations, side and proposed-control rationales separately. It is not independent human validation. The final run returned 293,760 input tokens (240,330 cached) and 482,705 output tokens. Published Standard-mode rates give an estimated $2.1543 for that run, excluding pilots and any interrupted calls without returned usage. See Meta's pricing source in the readable output report. The sanitized aggregate is committed as `review-evaluation-results.json`; exact calls, screenshots and pilot records accompany the source ZIP.
