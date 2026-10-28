# Why Meta models matter to ChoiceGap

## Current review workflow (28 October)

The product runs three text-only design critiques and a separate optional prototype review. Screenshot findings cannot suppress the independent design critique. Broad topic frequency across runs is consistency, not confidence or semantic consensus. The legacy combined reviewer below is retained to reproduce v4. The new neutral-instruction evaluation tests previously unused visual features without naming them in the prompts.

## Product role

Muse Spark connects a researcher's source material to competing explanations, controlled follow-ups, and a reviewable record of how the interpretation changed. It performs semantic work that the numerical choice engine cannot perform:

1. Map varied interview excerpts to explanations while retaining supporting, challenging, and missing evidence.
2. Critically review an editable study design and identify alternative interpretations or semantic confounds.
3. Optionally inspect a prototype screenshot alongside the evidence and design to flag visible defaults, hierarchy, wording, or availability as competing explanations.
4. Return observations, competing explanations, and proposed controls in a schema that code validates before displaying it for researcher review.

The workbench maps evidence into four predefined editable grocery-delivery categories; it does not autonomously discover an unrestricted hypothesis space. Task selection and report completion are computed locally and make no model calls.

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
