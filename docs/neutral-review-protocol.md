# Neutral-instruction development holdout (28 October)

The v4 evaluation tested sparse screens and a checklist of named departures from an exact design. It supports a narrow prototype-conformance claim. Its 36 planted calls all returned a visual finding, while 18 clean image calls returned none. A fixed keyword rule matched only 32 of those calls; that rule is preserved. A second AI's reading reported correct side and defect in all 36, but neither AI reading is human adjudication. Text-only caveats were often legitimate and their disappearance with an image exposed a weakness in the combined prompt.

## Product change

Three independent text-only design critiques assess the research and analysis regardless of screenshot. A separate visual-context call receives the prototype. Both stages are saved and shown; neither overwrites the other. Every call has a success/error record. Broad topic frequencies describe how many completed design runs raised a category, not identical findings, confidence, or approval. Failed calls are excluded from the completed-run denominator and shown alongside the planned total.

## Frozen new evaluation

The research question is neutral: “What should we investigate before using this checkout study to understand weekly grocery delivery choices?” Neither it nor the visual prompt names the six new feature types.

Eighteen new screens use one checkout template: scarcity cue, social proof, struck-through price anchor, low-contrast emissions text, leaf icon, and a different fact order, each with the affected side reversed. Six intended-neutral controls vary corner shape, heading alignment, shared dividers, a small vertical offset, a shared instruction, or shared button alignment. These controls are intended to be acceptable; no human experiment proves their psychological neutrality.

Run three visual reviews per screen (54 calls), plus three independent design-only runs on the shared text context (57 total). Unlike v4, there are no artificially case-labelled copies of identical text-only input. Protocol, prompts, reviewer method and images are hashed before execution. Resume rejects a changed model, protocol or image and preserves errors rather than retrying selected misses.

Report calls returning visual findings separately from fixed keyword matches. A finding is not automatically a true detection. Clean-screen findings are potential false alarms requiring inspection, not automatic failures: subtle layout differences may plausibly affect interpretation. Correct side, reason and adequate control still require adjudication. These are new feature families held out from v4 development, not independent external validation or proof of causal visual effects.

```powershell
python -m choicegap.neutral_review_benchmark --prepare
python -m choicegap.neutral_review_benchmark --run --env-file .env
```

The recorded run and frozen corpus accompany the source archive in `outputs/neutral-review-evaluation`. The application retains the legacy combined-review method solely for reproducing v4. No parameters or keyword rules are retuned after seeing the new evaluation outputs.
