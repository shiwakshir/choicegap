# Interface design

The current Studio uses a restrained research-workspace layout: a workflow rail, readable system typography, one dark green action colour, consistent borders and spacing, and status labels for drafts and published studies. The brief includes specific guidance instead of a promotional hero. The participant interface uses a separate quiet canvas, one question at a time and a compact five-point rating control.

A collapsible **About ChoiceGap** section sits above the researcher workflow. It explains the product, say–do-gap exploration, the four study stages, researcher benefits, a sustainability example, Meta's role and the prototype's evidence and data boundaries. It remains available across researcher screens and is not part of the participant questionnaire.

`static/studio.css` supplies the existing structural and media states; `static/studio-theme.css` is the shared visual layer for Studio. Both are included in the installable package. Historical delivery-workbench screens retain their own styles.

AI moderation, Meta processing, storage limits and optional recording remain disclosed. The participant's required consent is separate from the optional voice details. The redesign changes presentation and wording, not approved study content or collection permissions.

Checked in the browser with fictional audit data: brief and examples, study library, question editor and draft save, collection link, findings, participant consent, session resume, five-point rating, skips and the included 3D moderator. Phone-width checks at 390 px cover navigation and participant controls without horizontal overflow. Keyboard activation and visible focus were checked; reduced-motion preferences remain supported. These are implementation checks, not a human usability study or a full accessibility certification.
