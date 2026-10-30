# ChoiceGap product direction

Agreed direction, 28 October 2026: an adaptive UX research platform combining surveys, text interviews and choice tasks. Sustainability is the first study context.

## Product promise

Help a researcher understand what participants say, what they choose in the study, where those agree or differ, and which questions or product changes deserve further investigation.

The participant experiences one coherent study. Behavioural science belongs primarily in the researcher's interpretation and follow-up planning, rather than a separate mechanism-selection workflow.

## Intended study flow

1. The researcher sets the product decision, target participants, research questions, study length and permitted follow-ups. They approve the study before collection.
2. Participants answer short survey questions about their priorities, context and recent experiences.
3. They make relevant choices or complete a prototype task. Hypothetical choices, observed interactions and accounts of past behaviour retain separate labels.
4. The platform compares statements with task responses for that participant. Agreement is a valid finding; a discrepancy is a question to investigate, not evidence of dishonesty or irrationality.
5. A bounded text interview asks a neutral follow-up based on the response. It can explore an apparent discrepancy, clarify an unclear answer, or seek an exception. It must also allow a participant to correct the system's interpretation.
6. Where useful, an approved follow-up choice task distinguishes plausible explanations. Stop at the approved burden limit or when no useful permitted follow-up remains.
7. The researcher receives an evidence-linked analysis across completed sessions, including contradictory cases and unanswered questions.

Adaptation occurs within a researcher-approved question space. Store the question, response, branch reason, model version and displayed task. Do not silently rewrite the study objective, push participants toward consistency, or treat an AI explanation as their own account.

## Example

A participant rates lower delivery emissions highly, then chooses a higher-emissions delivery. Ask: “What mattered most when you chose that option?” If they mention being home for the delivery, clarify the scheduling constraint. A permitted follow-up can compare delivery windows while holding the other displayed details fixed.

The report can say that this participant described a scheduling constraint and selected the lower-impact option when the window changed. It should retain the exact responses and task conditions. It cannot establish their real purchasing behaviour or uniquely prove a psychological mechanism.

## Researcher analysis

“360” means several complementary views of the same evidence, not a claim of complete knowledge:

| View | Researcher receives |
|---|---|
| Stated priorities | Survey distributions and contextual interview excerpts |
| Study responses | Task choices, conditions and denominators |
| Alignment and gaps | Matched statements and responses, including agreement and exceptions |
| Participant explanations | Verbatim reasons and clarifications, separate from model interpretations |
| Behavioural science | Candidate explanations, supporting and challenging evidence, and alternatives |
| Practical constraints | Affordability, access, capability, scheduling and other contextual barriers |
| Product decisions | Proposed changes, evidence supporting them, and a next validation step |
| Limits | Missing responses, uneven question exposure, hypothetical tasks and unresolved accounts |

An adaptive question is not seen by everyone. Reports must show who received it and why; branch-specific responses cannot be presented as population prevalence. Imported excerpts cannot be matched to new participants without explicit provenance.

## Meta's role

Muse should interpret open responses, propose neutral follow-ups within approved boundaries, and synthesize evidence with traceable quotations and rival explanations. The application owns consent, question permissions, task controls, response storage, stopping rules and numerical summaries. Any claim about quality or time saved needs evaluation rather than being assumed from the model choice.

## Implementation boundary

Already implemented: importing interview/survey excerpts, source-linked evidence mapping, researcher-approved controlled choice studies, adaptive task selection, a bounded live text-interview loop, participant interpretation checks and corrections, up to two single-detail condition comparisons, unified per-session analysis and cross-session exposure counts. Separate behavioural experiments are retained as a collapsed advanced option.

The implemented interview uses fixed approved neutral questions anchored to a selected task and the participant's response. Muse can tentatively interpret two answers with a checked exact quote. A participant-selected factor changes the comparison order when it is one of the two differing anchor factors; an untested selected factor remains explicitly unresolved. This is bounded adaptation, not unrestricted question generation. The final report combines participant evidence, descriptive comparisons, candidate behavioural lenses, rivals and next validation steps. Baseline task selection remains computed locally.

On 30 October, new version-two approvals extend that existing flow: Muse interprets full session evidence, requests the order of the approved pair through a native tool call, then reconsiders after the first and final responses. Both approved comparisons still run. The participant can override the eligible detail; code rejects unknown tasks and invalid source references. This is a stronger model role within the existing feature set, not a broader study platform or unrestricted agent.

Not implemented: arbitrary prototype interaction capture, voice interviews, real-world outcome linkage, unrestricted emergent themes or validated psychological diagnosis. Scripted simulations test state transitions and condition comparisons; they do not establish neutral moderation quality, human research validity or product demand.
