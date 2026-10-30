# Demonstrating Muse within the existing study

Updated 30 October 2026. No new participant screens or question types are required.

## What to show in three minutes

1. Show a clearly labelled fictional participant who values verified environmental claims but selects free unverified delivery over a paid verified option.
2. Show their own correction: the extra fee exceeds their budget; verification itself is welcome.
3. Open the report's **How Muse’s reading changed** section. Show the recorded rival explanations, why the fee comparison came first, and what the model predicted before the response.
4. Show the exact approved comparison: remove the fee difference while holding the other details fixed. The scripted participant selects the verified option when both are free.
5. Show Muse's evidence-linked review and what remains unanswered. If the fee was already its leading explanation, call this strengthened support, not a change of mind. The next review must also account for the second comparison and final explanation.

Use a recording or clearly labelled saved live run if the API latency would dominate the three-minute presentation. Do not present saved responses as a fresh live inference. The demonstration is synthetic, not human research or proof of causal mechanisms.

## Reproduce the real model loop

Configure the existing local `.env` and run:

```powershell
python -m choicegap.muse_demo --live --output outputs/muse-reasoning-demo.json
```

This makes up to four actual Muse calls on fictional data. Without `--live`, the command uses local fallback and does not spend API credits. The fixture declares a seed whose first computed task compares fee and verification; it uses the shipped four-task adaptive engine. Its scripted utility rule prioritizes free delivery, then verification and environmental impact. This hidden rule is not disclosed to Muse. No model output is used to choose the fixture or a winning run.

The saved result includes the exact stimuli, original interpretation, participant correction, native tool request, checked tool result, both model reviews, source references and token usage. Failed checks remain explicit; no model answer is guaranteed.

For normal collection, create a new researcher workspace, review and approve the enabled version-two protocol, and use its participant link. Previously approved version-one studies keep the old narrower sharing scope. Model calls can take time; the participant sees a saving state and can retry after a request error.

## What is distinctive about the implementation

The semantic interpretation changes what happens in the study: Muse requests the order of existing comparisons, with a reason and response predictions recorded before answers. Code rejects unknown factors, forged quotations, changed stimuli and attempts to override a participant-selected eligible factor. Both comparisons remain part of the approved protocol.

After observing results, Muse receives the real tool result and full evidence again. The report preserves earlier readings and explicitly distinguishes a change in leading factor from strengthened/weakened support. The final review must reference the latest comparison and final participant explanation. The model is allowed to remain uncertain or unchanged.

Meta's [tool-calling documentation](https://dev.meta.ai/docs/tool-calling) currently permits only `tool_choice: "auto"`. The application accepts a valid single tool call or retains the local order. Tool schema strictness is not a guarantee of argument correctness; application validation remains necessary. The first smoke attempt used an unsupported named tool choice and was rejected with HTTP 400; the corrected automatic call was verified in subsequent runs. The source retains no credential in reports or archives.

## Evidence and limits

The regression suite covers complete four-call operation, usage accounting, exact quote checks, allowed-task boundaries, participant corrections, actual assistant/tool message formatting, latest-response references, skips, fallback, restart/concurrency and version-one compatibility.

`python -m choicegap.muse_context_benchmark --live` runs six real calls on three fixed fictional cases, comparing the original two-answer input with added full-session evidence under the same interpretation prompt. The initial development run matched the scripted leading factor in 0/3 cases in each condition; all six outputs passed structural and quotation checks. In two full-context outputs the scripted factor appeared as an alternative, whereas the narrow outputs lacked it. That alternative observation is exploratory, not a prespecified accuracy endpoint. The labels often followed the participant's words, so this tiny check does not establish better behavioural interpretation from context alone.

Expected factors come from a simulated choice rule. They are not validated human motives, and a factor match cannot establish a psychological cause. There is no measured provider superiority, human moderation quality, time saving or product demand. The stronger demonstrated capability is the checked planning/result/reconsideration loop, not an accuracy claim.
