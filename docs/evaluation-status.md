# Evidence workbench: evaluation status

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

The implementation pass completed 43 automated tests successfully, including the existing choice-engine tests. This is a regression-check count, not a research-quality score.

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
- Researcher planning time and methodological quality relative to their usual tools.
- Researcher willingness to use or pay for the product.
- Human comprehension and realism of the default or revised stimuli.
- Added value of Muse experiment selection over the deterministic expected-information-gain baseline.
- Population prevalence, real adoption outcomes, and causal intervention effects.

The fictional corpus supports repeatable software checks and demonstration. It must not be presented as customer research or evidence of adoption barriers in a real population.
