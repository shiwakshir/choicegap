// A guided entrance to the existing study, approval and reporting endpoints.
let simpleBrief = null;

function renderSimpleStudy(workspace) {
  if (!researcherMode) return;
  const approved = workspace.status === 'approved';
  state.studyId = approved ? workspace.id : null;
  $('#simple-review').hidden = approved;
  $('#simple-collect').hidden = !approved;
  $('#simple-title').textContent = workspace.blueprint.title;
  $('#simple-levels').innerHTML = `<dl class="simple-levels">${workspace.blueprint.attributes.map(a => `<div><dt>${escapeHtml(a.label)}</dt><dd>${escapeHtml(a.low_label)} <span>or</span> ${escapeHtml(a.high_label)}</dd></div>`).join('')}</dl>`;
  $('#simple-confirm').checked = false;
  $('#simple-publish').disabled = false;
  $('#simple-edited').textContent = 'You changed the detailed design. Review and approve those changes under More settings.';
  $('#simple-edited').hidden = true;
  if (!approved && workspace.sources.length) {
    $('#simple-publish').disabled = true;
    $('#simple-edited').textContent = 'This draft uses imported evidence. Review and approve it under More settings before creating a participant link.';
    $('#simple-edited').hidden = false;
  }
  $('#simple-findings').replaceChildren();
  $('#simple-download').disabled = true;
  simpleBrief = null;
  $('#simple-status').textContent = approved ? 'Your study is ready to share.' : 'Your study is ready to review. No responses have been collected by setting it up.';
  if (approved) {
    const url = participantLink(workspace.id);
    $('#simple-participant-link').href = url;
    $('#simple-share-url').value = url;
  }
}

document.addEventListener('choicegap-workspace', event => renderSimpleStudy(event.detail));

$('#simple-prepare').addEventListener('click', async () => {
  clearError(); $('#simple-prepare').disabled = true;
  $('#simple-status').textContent = 'Preparing your study…';
  try {
    renderWorkspace(await api('/api/research/prepared-delivery', {}));
    $('#simple-review').scrollIntoView({block:'start', behavior:'smooth'});
  } catch (error) { showError(error.message); $('#simple-status').textContent = ''; }
  finally { $('#simple-prepare').disabled = false; }
});

$('#simple-publish').addEventListener('click', async () => {
  clearError();
  if (!$('#simple-confirm').checked) { showError('Review the study and tick the confirmation before creating a participant link.'); return; }
  if (!researchWorkspace || researchWorkspace.status !== 'draft') return;
  $('#simple-publish').disabled = true;
  try {
    const approved = await api('/api/research/approve', {id:researchWorkspace.id, blueprint:researchWorkspace.blueprint, mapping:researchWorkspace.mapping, confirmed:true});
    renderWorkspace(approved);
    $('#simple-collect').scrollIntoView({block:'start', behavior:'smooth'});
  } catch (error) { showError(error.message); $('#simple-publish').disabled = false; }
});

$('#simple-saved').addEventListener('click', async () => {
  clearError(); $('#simple-saved-list').replaceChildren();
  try {
    const data = await researchGet('/api/research/workspaces');
    if (!data.workspaces.length) $('#simple-saved-list').textContent = 'No saved studies yet. Start with Set up this study.';
    for (const study of data.workspaces) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary';
      button.textContent = `${study.status === 'approved' ? 'Ready to share' : 'Draft'} · ${study.decision}`;
      button.addEventListener('click', async () => {
        try { renderWorkspace(await researchGet(`/api/research/workspace?id=${encodeURIComponent(study.id)}`)); }
        catch (error) { showError(error.message); }
      });
      $('#simple-saved-list').append(button);
    }
  } catch (error) { showError(error.message); }
});

$('#simple-results').addEventListener('click', async () => {
  if (!researchWorkspace || researchWorkspace.status !== 'approved') return;
  clearError(); $('#simple-results').disabled = true;
  const workspaceId = researchWorkspace.id;
  try {
    const brief = await researchGet(`/api/research/report?id=${encodeURIComponent(workspaceId)}`);
    if (researchWorkspace.id !== workspaceId) return;
    simpleBrief = brief;
    $('#simple-findings').innerHTML = simpleBrief.completed_sessions
      ? (uxAggregateHtml(simpleBrief.ux_research) || `<p>${simpleBrief.completed_sessions} completed sessions. This older study has choice results under More settings.</p>`)
      : '<p>No finished responses yet. Open the participant link and complete the study, then select View findings again.</p>';
    $('#simple-download').disabled = !simpleBrief.completed_sessions;
  } catch (error) { showError(error.message); }
  finally { $('#simple-results').disabled = false; }
});
$('#simple-download').addEventListener('click', () => {
  if (simpleBrief) downloadResearch(briefMarkdown(simpleBrief), 'choicegap-findings.md', 'text/markdown');
});

// Detailed edits must be reviewed through the detailed approval rather than publishing a stale preview.
$('.researcher-advanced').addEventListener('input', () => {
  if (researchWorkspace?.status === 'draft') { $('#simple-publish').disabled = true; $('#simple-edited').hidden = false; $('#simple-confirm').checked = false; }
});
