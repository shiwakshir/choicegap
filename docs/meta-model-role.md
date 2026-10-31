# Why Meta models matter to ChoiceGap

## Integrated capabilities, 31 October

The primary Studio workflow now uses Spark's native web search for cited desk research, Muse Image for researcher-reviewed concept generation/editing, Spark video understanding for participant-reviewed task descriptions, native function calls to select an approved single-detail comparison, and Muse Voice Transcribe's streaming endpoint for partial text and speech-turn completion. The included 3D character is local rendering, not a Meta-generated video avatar. The user chose this route rather than an external avatar service.

These capabilities connect preparation, observation, adaptive inquiry and synthesis around the approved study. Code fixes permitted task levels, checks source IDs and timestamps, separates desk research from participant evidence, preserves corrections and logs exact stimuli and model decisions. Live checks used public briefs and fictional clips/answers; they establish the integrations, not psychological validity, participant usability, causal effects or superiority over other models. See [the implementation and limits](muse-enhancements.md).

## Research Studio, 30 October

The primary product now starts from a brief, hypotheses and optional text/image concept. Muse Spark 1.3 drafts an editable multi-type survey and open interview guide; reads the approved stimulus alongside responses when planning bounded probes; offers a tentative participant account for correction; and synthesizes completed sessions with validated evidence IDs. This connects study creation, collection and interpretation around one approved objective rather than using a model only to summarize an exported survey.

New Studio approvals use [Muse Voice Transcribe](https://dev.meta.ai/docs/speech-to-text) for recorded answers. Together with device speech synthesis and Spark's next-question planning, this supplies an optional spoken moderator without a human attending. Participants correct/confirm transcripts before submitting. Existing version-one approvals retain their Spark 1.2 transcription path. The outgoing voice is device speech, not a Meta-generated voice or live avatar. See [the spoken moderator implementation](spoken-moderator.md).

Code validates question types and answers, freezes published designs, enforces follow-up-topic membership and probe budgets, rejects stale answers, preserves participant corrections and checks report source IDs. These checks constrain the model but do not prove semantic accuracy or neutral moderation. The workflow is supported by Meta's structured and multimodal APIs; no exclusive capability or superiority over other providers has been established. See [Research Studio](research-studio.md) for verification and limitations. Sections below describe the earlier controlled-choice workflow, which remains available separately.

## Current participant loop, 30 October

Muse now receives the full session in newly approved version-two studies. It interprets the participant's words alongside exact choices, requests one existing approved comparison through native tool calling, and reconsiders after observing the first and final results. Code owns selection validation, exact one-detail edits, orientation normalization, counts, correction precedence and the four-call cap. The actual initial reading and plan are preserved; a strengthened explanation is not presented as a different previous belief.

Both comparisons still run; the model chooses their order within the existing approved pair. It cannot create a task, expand the hypothesis catalogue or override the participant's selected eligible detail. Its post-task reading is explicitly separate from the participant's confirmed/corrected account. Strict source validation does not establish semantic accuracy. See `muse-demonstration.md` for the recorded run, unsuccessful checks and evaluation limits.

The older one-call descriptions below apply to version-one studies. Previously approved input-sharing scopes remain unchanged.

## Current review workflow (28 October)

The product runs three text-only design critiques and a separate optional prototype review. Screenshot findings cannot suppress the independent design critique. Broad topic frequency across runs is consistency, not confidence or semantic consensus. The legacy combined reviewer below is retained to reproduce v4. The new neutral-instruction evaluation tests previously unused visual features without naming them in the prompts.

## Product role

Muse Spark connects a researcher's source material to competing explanations, controlled follow-ups, and a reviewable record of how the interpretation changed. It performs semantic work that the numerical choice engine cannot perform:

1. Map varied interview excerpts to explanations while retaining supporting, challenging, and missing evidence.
2. Critically review an editable study design and identify alternative interpretations or semantic confounds.
3. Optionally inspect a prototype screenshot alongside the evidence and design to flag visible defaults, hierarchy, wording, or availability as competing explanations.
4. Return observations, competing explanations, and proposed controls in a schema that code validates before displaying it for researcher review.

The workbench maps evidence into four predefined editable grocery-delivery categories; it does not autonomously discover an unrestricted hypothesis space. Task selection and numerical reporting are computed locally. In the integrated study, Muse additionally interprets two optional participant responses once using a strict schema: tentative summary, exact quotation, candidate factor and rival (or unresolved). Code rejects unsupported quote spans or unknown factors. Participants can confirm, correct or leave that interpretation unresolved; rejected interpretations cannot silently steer task ordering. This does not independently validate semantic accuracy.

The screenshot review does not infer clicks, attention, motives, or real purchases from a static image. Visual findings are model interpretations requiring researcher verification.

The reviewer receives the exact compiled task pairs as well as the study-wide factor definitions. This prevents changes between different tasks being mistaken for an uncontrolled change within one task. It is allowed to return an empty finding list when the controls are satisfied.

## Meta capability mapping

| Meta capability | ChoiceGap use | Observable output |
|---|---|---|
| Native image understanding | Compare visible prototype context with textual explanations and the proposed study | Findings explicitly labelled `prototype_image` |
| Reasoning | Challenge a leading account and propose distinguishing controls | Observation, competing explanation, suggested control, unresolved questions |
| Structured output | Convert model reasoning into a known research-review schema | Locally validated citations, evidence basis, account IDs, and review fields |
| Contextual pre-fieldwork review | Compare source evidence, proposed design and screenshot in one request | Observation, rival explanation and proposed control with explicit evidence basis |

Implementation uses the Meta Model API with `muse-spark-1.3` by default, schema strict mode, and high reasoning effort for the critical design-review task. The screenshot is sent as a native `image_url` content part in a user message.

Official documentation consulted on 27 October 2026:

- [Muse Spark model capabilities](https://dev.meta.ai/docs/models)
- [Image input through Chat Completions](https://dev.meta.ai/docs/cookbook/vision-input)
- [Structured output](https://dev.meta.ai/docs/structured-output)
- [Reasoning effort](https://dev.meta.ai/docs/reasoning)

## Example demonstration

The researcher begins with a price explanation for low uptake of a lower-impact delivery slot. A prototype screenshot could reveal that the standard slot is preselected or visually more prominent. Muse's reviewer should identify that visible feature as a possible competing explanation and suggest keeping default selection and prominence equal during the price contrast. This is an illustrative scenario; it is not a measured result from a live Muse run.

The demonstration should show the supplied image, the finding's evidence basis, the proposed control, the researcher-approved stimulus, and the subsequent decision trail. It should preserve an inconclusive outcome when the available evidence cannot distinguish explanations.

## Without the model

The deterministic engine still compiles designs and updates probabilities. A researcher must manually interpret source material, inspect prototype context, identify semantic confounds, and formulate the proposed controls. Offline mode does not fabricate a Muse review.

## Claims boundary

This is a distinctive application of Meta's capabilities, not evidence that only Meta can perform the task. Provider exclusivity or superiority requires a comparative evaluation. The existing simulated-participant benchmark measures deterministic experiment selection; it is not a measure of Muse's multimodal reasoning or reviewer quality.

The frozen 18-case screenshot-versus-text evaluation is specified in `review-evaluation-protocol.md`. Keyword screening is not a substitute for adjudicated accuracy, and a prepared test set is not a live model result.

The recorded v4 development evaluation completed 108 calls successfully. Image-conditioned screening matched 32/36 planted calls and none of 18 clean image calls returned findings. These are fixed-rule screening counts on one synthetic checkout template, not human-adjudicated accuracy. The raw outputs and unblinded developer spot checks make the examples inspectable; external UXR value and provider superiority remain unmeasured.

Image bytes are not stored in the research workspace or included in the decision brief. The review stores an image digest, findings, model source, returned API usage, and a digest of the design inputs reviewed. Image signatures, source references, and current-design matching are checked locally; these checks do not prove the semantic accuracy of a finding.
