let researchWorkspace = null;
let researchBrief = null;
let fictionalEvidence = false;

async function researchGet(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not load research data.');
  return data;
}

function sourceName(source) {
  const kind = source.kind === 'observed' ? 'reported action' : source.kind;
  return `${source.id} · ${source.label} · ${kind}`;
}

function participantLink(identifier) {
  const url = new URL('/', window.location.href);
  url.searchParams.set('study', identifier);
  return url.href;
}

function renderWorkspace(workspace) {
  researchWorkspace = workspace;
  researchBrief = null;
  $('#evidence-decision').value = workspace.decision;
  $('#evidence-text').value = workspace.sources.map(source => `${source.kind} | ${source.label} | ${source.text}`).join('\n');
  fictionalEvidence = workspace.evidence_origin === 'fictional-example';
  const approved = workspace.status === 'approved';
  $('#workspace-review').hidden = false;
  $('#workspace-title').value = workspace.blueprint.title;
  $('#workspace-prompt').value = workspace.blueprint.decision_prompt;
  $('#workspace-meta').textContent =
    `${workspace.status.toUpperCase()} · ${workspace.source} · ` +
    `${workspace.evidence_origin === 'fictional-example' ? 'FICTIONAL EXAMPLE — demonstration only' : 'Researcher-supplied evidence; provenance unverified'}. ` +
    (workspace.warning || 'Source links are checked for exact quotation. Interpretations still require researcher review.');
  $('#evidence-sources').innerHTML = `
    <details class="source-list"><summary>Imported sources (${workspace.sources.length})</summary>
      ${workspace.sources.map(source => `
        <p><strong>${escapeHtml(sourceName(source))}</strong><br>${escapeHtml(source.text)}</p>
      `).join('')}
    </details>
  `;
  $('#research-accounts').innerHTML = workspace.blueprint.attributes.map(attribute => {
    const account = workspace.mapping.accounts.find(item => item.id === attribute.id);
    return `
      <article class="account-card" data-account="${attribute.id}">
        <h3>${escapeHtml(attribute.label)}</h3>
        <label>Factor name<input type="text" data-field="label" value="${escapeHtml(attribute.label)}"></label>
        <label>Baseline level<input type="text" data-field="low_label" value="${escapeHtml(attribute.low_label)}"></label>
        <label>Alternative level<input type="text" data-field="high_label" value="${escapeHtml(attribute.high_label)}"></label>
        <label>Competing explanation<textarea data-field="explanation" rows="3">${escapeHtml(account.explanation)}</textarea></label>
        <label>Missing evidence<textarea data-field="missing_evidence" rows="2">${escapeHtml(account.missing_evidence)}</textarea></label>
        <p>For each source, review its relationship to this explanation. This is an interpretation, not a verified mechanism.</p>
        ${workspace.sources.map(source => {
          const reference = account.references.find(item => item.source_id === source.id);
          return `
            <div class="source-reference">
              <label>${escapeHtml(sourceName(source))}
                <select data-source="${source.id}">
                  ${[['none', 'Not assigned'], ['supports', 'Supports'], ['challenges', 'Challenges'], ['context', 'Context only']]
                    .map(([value, label]) => `<option value="${value}" ${value === (reference?.relation || 'none') ? 'selected' : ''}>${label}</option>`).join('')}
                </select>
              </label>
              <details><summary>Read source</summary><p>${escapeHtml(source.text)}</p></details>
            </div>
          `;
        }).join('')}
      </article>
    `;
  }).join('');
  $('#unresolved-questions').value = workspace.mapping.unresolved.join('\n');
  $('#workspace-approved').checked = approved;
  $('#workspace-review').querySelectorAll('input, textarea, select').forEach(input => {
    input.disabled = approved;
  });
  $('#approve-workspace').disabled = approved;
  $('#approve-workspace').textContent = approved ? 'Approved design is locked' : 'Approve design and create participant link';
  $('#workspace-link').innerHTML = approved
    ? `<strong>Approved version ${workspace.version}</strong>
       <a href="${escapeHtml(participantLink(workspace.id))}" target="_blank" rel="noopener">Open approved participant study →</a>
       <span>Design digest: ${escapeHtml(workspace.design_sha256)}</span>`
    : '<span>Drafts cannot be used for participant collection. Review the plan and approve it first.</span>';
  $('#workspace-summary').replaceChildren();
  $('#export-brief').disabled = true;
  $('#export-brief-data').disabled = true;
  const url = new URL(window.location.href);
  url.searchParams.set('workspace', workspace.id);
  if (approved) url.searchParams.set('study', workspace.id);
  else url.searchParams.delete('study');
  window.history.replaceState({}, '', url);
}

$('#example-evidence').addEventListener('click', async () => {
  clearError();
  try {
    const data = await researchGet('/api/research/example');
    $('#evidence-decision').value = data.decision;
    $('#evidence-text').value = data.evidence;
    fictionalEvidence = true;
  } catch (error) { showError(error.message); }
});

$('#draft-workspace').addEventListener('click', async () => {
  clearError();
  const button = $('#draft-workspace');
  button.disabled = true;
  button.textContent = 'Preparing evidence map…';
  try {
    const workspace = await api('/api/research/draft', {
      decision: $('#evidence-decision').value,
      evidence: $('#evidence-text').value,
      example: fictionalEvidence,
    });
    renderWorkspace(workspace);
  } catch (error) { showError(error.message); }
  finally {
    button.disabled = false;
    button.textContent = 'Map evidence and draft follow-ups';
  }
});

$('#load-workspaces').addEventListener('click', async () => {
  clearError();
  try {
    const data = await researchGet('/api/research/workspaces');
    $('#workspace-list').replaceChildren();
    if (!data.workspaces.length) $('#workspace-list').textContent = 'No saved workspaces yet.';
    data.workspaces.forEach(workspace => {
      const button = document.createElement('button');
      button.className = 'secondary';
      button.textContent = `${workspace.status} · ${workspace.decision}`;
      button.addEventListener('click', async () => {
        try {
          const loaded = await researchGet(`/api/research/workspace?id=${encodeURIComponent(workspace.id)}`);
          renderWorkspace(loaded);
          if (loaded.status === 'approved') {
            const study = await researchGet(`/api/study?id=${encodeURIComponent(loaded.id)}`);
            applyStudy(study);
          }
        } catch (error) { showError(error.message); }
      });
      $('#workspace-list').append(button);
    });
  } catch (error) { showError(error.message); }
});

$('#approve-workspace').addEventListener('click', async () => {
  clearError();
  if (!researchWorkspace) return;
  const blueprint = structuredClone(researchWorkspace.blueprint);
  blueprint.title = $('#workspace-title').value;
  blueprint.decision_prompt = $('#workspace-prompt').value;
  const mapping = { accounts: [], unresolved: $('#unresolved-questions').value.split('\n').filter(Boolean) };
  document.querySelectorAll('[data-account]').forEach(card => {
    const id = card.dataset.account;
    const field = key => card.querySelector(`[data-field="${key}"]`).value;
    const attribute = blueprint.attributes.find(item => item.id === id);
    ['label', 'low_label', 'high_label'].forEach(key => { attribute[key] = field(key); });
    attribute.hypothesis_label = attribute.label;
    attribute.hypothesis_description = field('explanation');
    const references = [];
    card.querySelectorAll('[data-source]').forEach(select => {
      if (select.value === 'none') return;
      const source = researchWorkspace.sources.find(item => item.id === select.dataset.source);
      references.push({ source_id: source.id, quote: source.text, relation: select.value });
    });
    mapping.accounts.push({ id, explanation: field('explanation'), missing_evidence: field('missing_evidence'), references });
  });
  const button = $('#approve-workspace');
  button.disabled = true;
  try {
    const approved = await api('/api/research/approve', {
      id: researchWorkspace.id, blueprint, mapping, confirmed: $('#workspace-approved').checked,
    });
    renderWorkspace(approved);
    const study = await researchGet(`/api/study?id=${encodeURIComponent(approved.id)}`);
    applyStudy(study);
  } catch (error) {
    showError(error.message);
    button.disabled = false;
  }
});

$('#workspace-report').addEventListener('click', async () => {
  clearError();
  if (!researchWorkspace) return;
  try {
    researchBrief = await researchGet(`/api/research/report?id=${encodeURIComponent(researchWorkspace.id)}`);
    const brief = researchBrief;
    const attributes = researchWorkspace.blueprint.attributes;
    const labelsById = Object.fromEntries(attributes.map(item => [item.id, item.label]));
    const facts = levels => Object.entries(levels).map(([id, value]) =>
      `<li>${escapeHtml(labelsById[id] || id)}: ${escapeHtml(value)}</li>`).join('');
    $('#workspace-summary').innerHTML = `
      <section class="brief-section">
        <h3>Decision brief</h3>
        <p>${escapeHtml(brief.decision)}</p>
        <p>${brief.completed_sessions} completed sessions · ${brief.response_checks_passed} passed response checks ·
          ${brief.inconclusive_response_checks} failed or missing response checks · ${brief.weak_model_separation} with weak model separation.</p>
        <p>${escapeHtml(brief.next_step)}</p>
        <h4>Session leaders within the candidate model set</h4>
        <ul>${Object.entries(brief.session_leader_counts).map(([id, count]) => `<li>${escapeHtml(labelsById[id])}: ${count} sessions</li>`).join('')}</ul>
        <details><summary>Inspect individual and contradictory cases</summary>
          ${brief.session_cases.map(item => `<p>Session ${item.case}: ${escapeHtml(item.response_quality)} response quality; leading model ${escapeHtml(labelsById[item.leading_account])} (${Math.round(item.model_probability * 100)}%); stated priorities ${escapeHtml(item.stated_priorities.map(id => labelsById[id]).join(', '))}; outside choices ${item.outside_choices}; repeat ${item.holdout_consistent === true ? 'consistent' : 'inconsistent or unavailable'}.</p>`).join('')}
        </details>
        <h4>Proposed field contrasts — not executed</h4>
        ${brief.field_tests.map(test => `
          <details class="trace-entry field-contrast">
            <summary>${escapeHtml(test.factor)}</summary>
            <p>${escapeHtml(test.prediction)}</p>
            <div class="trace-options"><div><strong>Baseline focal option</strong><ul>${facts(test.baseline)}</ul></div>
              <div><strong>Intervention focal option</strong><ul>${facts(test.intervention)}</ul></div></div>
            <p>Held constant: ${escapeHtml(test.held_constant.join(', '))}.</p>
            <p>${escapeHtml(test.design)}</p><p>Outcome: ${escapeHtml(test.outcome)}</p>
            <p>${escapeHtml(test.limitations)}</p>
          </details>
        `).join('')}
        <ul>${brief.limitations.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
      </section>
    `;
    $('#export-brief').disabled = false;
    $('#export-brief-data').disabled = false;
  } catch (error) { showError(error.message); }
});

function downloadResearch(content, name, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

function briefMarkdown(brief) {
  const labelById = Object.fromEntries(brief.blueprint.attributes.map(item => [item.id, item.label]));
  const cell = text => String(text).replace(/\|/g, '\\|').replace(/\n/g, ' ');
  const lines = [
    `# ${brief.study_title}: research decision brief`, '',
    `Evidence origin: ${brief.evidence_origin}. Mapping source: ${brief.mapping_source}.`, '',
    ...(brief.evidence_origin === 'fictional-example' ? ['**Fictional demonstration data. This is not customer research.**', ''] : []),
    '## Product decision', '', brief.decision, '',
    `Design version: ${brief.version}. Status: ${brief.status}. Approved: ${brief.approved_at || 'not approved'}.`, '',
    '## Current evidence', '',
    `${brief.completed_sessions} completed sessions; ${brief.response_checks_passed} passed response checks; ` +
      `${brief.inconclusive_response_checks} failed or missing response checks; ${brief.weak_model_separation} with weak model separation.`, '',
    brief.next_step, '', '### Session leaders within the candidate model set', '',
    ...Object.entries(brief.session_leader_counts).map(([id, count]) => `- ${labelById[id]}: ${count} sessions`), '',
    '## Competing explanations', '',
  ];
  brief.mapping.accounts.forEach(account => {
    lines.push(`### ${labelById[account.id]}`, '', account.explanation, '', `Missing evidence: ${account.missing_evidence}`, '');
    if (!account.references.length) lines.push('No source relationships assigned.', '');
    account.references.forEach(ref => lines.push(`- ${ref.source_id}: ${ref.relation} (${ref.source_kind})`, `  > ${ref.quote.replace(/\n/g, '\n  > ')}`, ''));
  });
  lines.push('## Other explanations and unresolved questions', '', ...brief.mapping.unresolved.map(item => `- ${item}`), '');
  lines.push('## Proposed field contrasts — not executed', '');
  brief.field_tests.forEach(test => {
    lines.push(`### ${test.factor}`, '', test.prediction, '', '| Factor | Baseline focal option | Intervention focal option |', '|---|---|---|');
    Object.keys(test.baseline).forEach(id => lines.push(`| ${cell(labelById[id])} | ${cell(test.baseline[id])} | ${cell(test.intervention[id])} |`));
    lines.push('', `Held constant: ${test.held_constant.join(', ')}.`, '', test.design, '', `Outcome: ${test.outcome}`, '', test.limitations, '');
  });
  lines.push('## Imported sources', '');
  brief.sources.forEach(source => lines.push(`### ${sourceName(source)}`, '', `> ${source.text.replace(/\n/g, '\n> ')}`, ''));
  lines.push('## Limits', '', ...brief.limitations.map(item => `- ${item}`), '', `Design digest: ${brief.design_sha256 || 'draft; no approval digest'}`, '');
  return lines.join('\n');
}

$('#export-brief').addEventListener('click', () => {
  if (researchBrief) downloadResearch(briefMarkdown(researchBrief), 'choicegap-decision-brief.md', 'text/markdown');
});

$('#export-brief-data').addEventListener('click', () => {
  if (researchBrief) downloadResearch(JSON.stringify(researchBrief, null, 2), 'choicegap-decision-brief.json', 'application/json');
});

if (researcherMode) {
  const identifier = new URLSearchParams(window.location.search).get('workspace');
  if (identifier) {
    researchGet(`/api/research/workspace?id=${encodeURIComponent(identifier)}`)
      .then(async workspace => {
        renderWorkspace(workspace);
        if (workspace.status === 'approved') {
          applyStudy(await researchGet(`/api/study?id=${encodeURIComponent(workspace.id)}`));
        }
      }).catch(error => showError(error.message));
  }
}
