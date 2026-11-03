# Submission plan

## Project thesis

ChoiceGap turns a researcher brief into an editable survey and interview guide. After approval, Muse asks bounded follow-ups, can select a reviewed single-detail comparison, and gives participants a chance to correct its interpretation. Findings link to the exact answers and distinguish stated priorities, reported episodes, hypothetical choices and reviewed recording descriptions. Sustainability delivery research is one clear demonstration domain.

## Evaluation mapping

| Criterion | Weight | Evidence in this repository |
|---|---:|---|
| Impact | 30% | Connects survey answers, adaptive interviewing and evidence-linked findings; human usability, demand and time savings remain unmeasured. |
| Meta tooling | 25% | Spark designs and moderates; native tool calling selects approved comparisons; Muse Voice transcribes; optional visual context, cited background and Muse Image support study preparation. |
| Demo | 25% | One brief → researcher review → participant interview → correction → findings flow. Recorded outputs and fictional material are clearly labelled. |
| Technical depth | 20% | Immutable approvals, bounded probes, checked evidence IDs, participant corrections, audited single-cell changes, stale-response protection and scoped streaming tickets. |

## Credit budget

The current Studio uses model calls during collection, unlike the earlier deterministic choice engine. Survey probe attempts are capped at four, interview probe attempts at six, with at most two and three added probes respectively. A completed session may also call member-check synthesis and approved-condition selection. Streaming/file transcription and optional task review add their own processing. Generation, desk research, images and final synthesis are separate calls. Do not claim a fixed per-study cost without current account pricing and usage. No application-wide spend cap is implemented; public access remains blocked pending deployment controls.

## Before submission

- [x] Working vertical slice
- [x] Explicit Meta-unavailable handling; approved collection can continue without adaptive probes
- [x] Objective simulated-participant benchmark for the earlier choice engine, clearly separated from Studio integration checks
- [x] Tests and reproducible seed
- [x] Three-minute demo outline
- [x] Add `MODEL_API_KEY` locally and run the live Meta smoke test
- [ ] Collect independent UXR feedback if available; external recruitment is not a prerequisite for continuing development
- [x] Publish this repository publicly (`https://github.com/shiwakshir/choicegap`)
- [x] Record a three-minute demo
- [ ] Post the demo on X and submit the link for the Most Viral Project bonus prize
- [ ] Submit before 4 November 2026, 9:00 PM ET

## Track & bonus prize positioning

- **Primary Problem Statement:** **Build for Your World** — bringing Meta's multimodal and reasoning models into UX and market research so teams can run brief-led, adaptive, evidence-linked studies without losing methodological rigor.
- **Best Agentic Use-Case ($5,000):** ChoiceGap acts as a **verifiable, bounded research agent**. It conducts live web-grounded desk research (`web_search`), generates structured multi-type studies, autonomously decides when to ask bounded follow-up probes within researcher-approved topics, invokes native tool calling (`select_approved_condition`) mid-session to test a single-cell variant against a rival explanation, checks its tentative mental model with the participant (`C1`), and synthesizes cited findings.
- **Best Creative Build ($5,000):** Uses **Muse Image (`muse-image-1.0`)** (`/v1/images/generations` and `/v1/images/edits`) inside Research Studio so researchers can generate and iteratively refine visual concept stimuli before locking the approved study.
- **Most Viral Project ($20,000) & Community Vote ($10,000):** Post the 3-minute demo video on X and submit the post URL on the Cerebral Valley submission form (engagement counted through November 8 EOD).

## Three-minute demonstration

1. 0:00–0:25: Explain the retailer's decision: which change would make lower-impact delivery practical? Introduce ChoiceGap as a research workflow, without promising to reveal hidden motives.
2. 0:25–1:00: Show the brief, **Muse Spark `web_search` desk research**, **Muse Image (`muse-image-1.0`) concept generation/edit**, and researcher edits to the **Muse Spark (`muse-spark-1.3`)** draft. Approve the survey/interview guide and comparison matrix.
3. 1:00–1:45: Show a participant's priorities and a contextual account, a relevant Muse follow-up probe, and spoken moderation with **Muse Voice Transcribe (`muse-voice-transcribe-1.0`)** realtime WebSocket streaming + the 3D AI moderator. Clearly label scripted responses as fictional.
4. 1:45–2:20: Show the exact approved change selected via **Muse Spark native tool calling (`select_approved_condition`)**, the hypothetical choice, the model's prospective rationale, and the participant correction (`C1`). Use a clearly labelled saved run if latency requires it.
5. 2:20–3:00: Show findings and supporting responses, uncertainty, and JSON export. Explain Meta's contribution and the validation boundary. An inconclusive report is valid. Do not claim human research quality, provider superiority, measured time savings, or causal proof.

The earlier evidence workbench and its benchmarks remain historical supporting material; do not imply those metrics evaluate the new Studio moderator. See [the current audit](choicegap-audit-2026-11-01.md) for tested scope and remaining submission work.

Do not script a guaranteed gap: an inconclusive result should remain visible when the evidence is weak.

## Scientific claims policy

Say “the observed choices are more consistent with…” and “this test reduced uncertainty under the model.” Do not say that four hypothetical choices reveal a true preference, prove a cause, or generalize to a market. Human validation should preregister the primary contrast, randomize order, preserve exact stimulus wording, and analyze more than one respondent.
