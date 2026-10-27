# Frozen Muse design-review evaluation

This evaluation tests whether Muse notices deliberately introduced defects in checkout prototypes. It does not measure customer demand, researcher time savings, all possible study confounds, or superiority over another provider.

## Cases and controls

Eighteen synthetic grocery-delivery screenshots: twelve planted cases and six clean cases. The six planted categories are a preselected option, unequal button prominence, unilateral recommendation badge, moralizing wording, unequal availability, and an extra fee absent from the stated fee. Each defect is repeated with the affected side reversed. Clean cases preserve equal presentation, availability, wording, and selection state while varying the intended emissions/price trade-off.

Each case runs three times with a screenshot and three times without it: 108 planned calls. Both conditions receive the same decision, source excerpt, four-account mapping and exact study blueprint. Expected labels, target side, filenames and scoring rules are withheld from Muse. The text-only condition deliberately lacks the screenshot contents: this measures the contribution of visual context, not image reasoning versus an equivalent textual description.

The protocol and screenshot bytes are hashed before calls run. Cases, repetition count, order seed, rubric and prompts are frozen. Resume rejects a changed protocol or model and does not retry recorded failures. API failures stop the run to avoid repeating authentication/outage errors. A future changed protocol must use another directory.

## Scoring

Primary detection requires a reviewer to verify both an accurate observation of the planted defect and a proposed control that addresses it. Merely naming a broad possibility does not count. Wrong-side observations fail. A clean-case false alarm is a confidently alleged defect that is absent, rather than a clearly stated question or general limitation. Record a rationale for every label.

The runner exports a shuffled `blind-review-packet.json` without condition or expected-label fields. Adjudicators can inspect the matching image and model findings. Copy `adjudication-template.json` to `adjudication.json` and set `detected` to true/false plus a rationale. For planted cases true means correct detection with an adequate control; for clean cases true means a false alarm. The packet's hashed IDs are used for joining labels. Image-basis language may reveal the condition, so blinding is partial. One reviewer is not independent validation; record who scored and disagreements if multiple reviewers are available.

Automated keyword matches are explicitly an unvalidated screening proxy. They cannot verify the correct side or adequacy of a control and must not be presented as semantic accuracy. The strict clean screening statistic counts any finding, including potentially legitimate caveats; distinguish this from adjudicated false alarms.

Report counts and denominators separately for planted and clean cases, missing human labels, per-case consistency over three repeats, validation failures, API failures, latency and returned token usage. Costs are estimated only if verified per-million token rates are supplied; otherwise cost remains unknown. Errors remain in attempted-call denominators. Repeated calls are not independent cases; do not use 108 as the number of distinct cases or imply statistical generalization.

## Reproduce

Preparation uses Pillow as an evaluation-only dependency. The application still has no third-party runtime dependencies.

```powershell
python -m pip install Pillow
python -m choicegap.review_benchmark --prepare --directory outputs/muse-review-evaluation-v4
python -m choicegap.review_benchmark --run --env-file .env --max-calls 1 --directory outputs/muse-review-evaluation-v4
python -m choicegap.review_benchmark --run --env-file .env --directory outputs/muse-review-evaluation-v4
python -m choicegap.review_benchmark --directory outputs/muse-review-evaluation-v4
```

The one-call smoke run is part of the frozen schedule, not an extra handpicked case. After reviewing the smoke call, the full command resumes the remaining schedule. Set `META_MODEL` in the same local file if your account requires another model version; do not change it during a run. `.env` is excluded from Git. Raw records contain model outputs and usage, never the key. No live results may be claimed until the recorded calls exist, and primary accuracy remains unmeasured until adjudication.

## Pilot and revision record

The first live call under protocol v2 was a text-only pilot. It showed that omitting compiled option pairs caused the reviewer to confuse study-wide factor definitions with changes within e1. Before the main evaluation, the production reviewer was updated to receive all exact compiled pairs, distinguish declared trade-offs from uncontrolled changes, and allow an empty findings list. Protocol v3 freezes that reviewer implementation hash as well as the cases. The v2 pilot is retained separately and excluded from v3 statistics. No v3 prompt changes or handpicked retries are allowed after the main run starts.

The v3 run was stopped when a clean screenshot was found to use semantically equivalent but nonidentical copy (notably £0 versus Free delivery). Those copy mismatches gave the reviewer a legitimate reason to flag a supposedly clean case. The v4 corpus uses the exact compiled text in all base profiles, changing only the planted feature. Earlier calls remain separate pilot data; v4 is the final frozen evaluation. This is a development evaluation, not an untouched external holdout: pilot findings informed the prompt and corpus corrections.

All screenshots use one grocery checkout template. The two instances per defect reverse the affected side; the six clean renders differ only in the neutral footer. They are controlled repeats, not 18 independently sampled real designs. Visual-basis keyword scoring excludes text-only findings by definition; its condition difference must not be described as an unbiased semantic accuracy lift. Human adjudication checks observations and controls in both conditions and is reported separately when available.

The runner uses three concurrent calls by default, with per-call usage records. The final v4 run uses six workers. An API error stops new batches after all in-flight calls have been recorded. Interrupted or error records are not silently replaced.
