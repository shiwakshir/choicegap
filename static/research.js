let researchWorkspace = null;
let researchBrief = null;
let fictionalEvidence = false;
let prototypeImage = null;

function renderDesignReview(review, current = true) {
  if (!review) {
    $('#design-review').textContent = 'No Muse design review has been run for this draft.';
    return;
  }
  const findingHtml = finding => `
    <article class="review-finding"><p><strong>Basis: ${escapeHtml(finding.basis)}</strong> · ${escapeHtml(finding.source_ids.join(', '))}</p>
      <p><strong>Observation:</strong> ${escapeHtml(finding.observation)}</p>
      ${finding.quote ? `<blockquote>${escapeHtml(finding.quote)}</blockquote>` : ''}
      <p><strong>Competing explanation:</strong> ${escapeHtml(finding.alternative_explanation)}</p>
      <p><strong>Proposed control:</strong> ${escapeHtml(finding.suggested_control)}</p></article>`;
  const stages = review.runs ? `
    <h4>Design review — independent of screenshot</h4>
    <p>Each run below is a separate AI response. Broad topic frequency describes consistency, not confidence or identical findings.</p>
    <ul>${review.topic_frequency.filter(item => item.raised_in).map(item => `<li>${escapeHtml(item.topic)}: raised in ${item.raised_in}/${item.completed_runs} completed runs (${item.planned_runs} planned)</li>`).join('')}</ul>
    ${review.runs.map(run => `<details class="trace-entry"><summary>${run.stage === 'design' ? 'Design critique' : 'Prototype review'} · run ${run.run} · ${escapeHtml(run.status)}</summary>
      ${run.status === 'ok' ? `<p>${escapeHtml(run.summary)}</p>${run.findings.map(findingHtml).join('')}${!run.findings.length ? '<p>No findings returned in this run; this is not approval of the overall design.</p>' : ''}` : `<p>${escapeHtml(run.error)}</p>`}</details>`).join('')}
  ` : review.findings.map(findingHtml).join('');
  $('#design-review').innerHTML = `
    <p><strong>${escapeHtml(review.source)} · ${review.prototype ? 'Evidence + screenshot review' : 'Evidence + design review'}</strong></p>
    <p id="review-current">${current ? 'Review matches the saved design inputs.' : 'The design has changed since this review. Review the revised inputs again.'}</p>
    <p>${escapeHtml(review.summary)}</p>
    ${stages}
    <ul>${review.unresolved.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    <p>${escapeHtml(review.scope)}</p>
    ${review.prototype ? `<p class="trace-hash">Reviewed screenshot digest: ${escapeHtml(review.prototype.sha256)}</p>` : ''}
  `;
}

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
  if (researchWorkspace?.id !== workspace.id) {
    prototypeImage = null;
    $('#prototype-image').value = '';
    $('#prototype-preview').hidden = true;
    $('#prototype-preview').removeAttribute('src');
  }
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
          const references = account.references.filter(item => item.source_id === source.id);
          return (references.length ? references : [null]).map(reference => `
            <div class="source-reference">
              <label>${escapeHtml(sourceName(source))}
                <select data-source="${source.id}">
                  ${[['none', 'Not assigned'], ['supports', 'Supports'], ['challenges', 'Challenges'], ['context', 'Context only']]
                    .map(([value, label]) => `<option value="${value}" ${value === (reference?.relation || 'none') ? 'selected' : ''}>${label}</option>`).join('')}
                </select>
              </label>
              <label>Exact quoted evidence
                <textarea data-quote="${source.id}" rows="2">${escapeHtml(reference?.quote || source.text)}</textarea>
              </label>
              <details><summary>Read source</summary><p>${escapeHtml(source.text)}</p></details>
            </div>
          `).join('');
        }).join('')}
      </article>
    `;
  }).join('');
  $('#unresolved-questions').value = workspace.mapping.unresolved.join('\n');
  $('#experience-enabled').checked = workspace.blueprint.experience_version === 1;
  $('#workspace-approved').checked = approved;
  $('#workspace-review').querySelectorAll('input, textarea, select').forEach(input => {
    if (!input.closest('#mechanism-workbench')) input.disabled = approved;
  });
  $('#approve-workspace').disabled = approved;
  $('#challenge-design').disabled = approved;
  renderDesignReview(workspace.design_review, workspace.design_review_current !== false);
  $('#approve-workspace').textContent = approved ? 'Approved design is locked' : 'Approve design and create participant link';
  $('#workspace-link').innerHTML = approved
    ? `<strong>Approved version ${workspace.version}</strong>
       <a href="${escapeHtml(participantLink(workspace.id))}" target="_blank" rel="noopener">Open approved participant study →</a>
       <span>Design digest: ${escapeHtml(workspace.design_sha256)}</span>`
    : '<span>This trade-off study needs approval before collection. Behavioural experiments have their own approval above.</span>';
  $('#workspace-summary').replaceChildren();
  $('#export-brief').disabled = true;
  $('#export-brief-data').disabled = true;
  const url = new URL(window.location.href);
  url.searchParams.set('workspace', workspace.id);
  if (approved) url.searchParams.set('study', workspace.id);
  else url.searchParams.delete('study');
  window.history.replaceState({}, '', url);
  document.dispatchEvent(new CustomEvent('choicegap-workspace', { detail: workspace }));
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

function readWorkspaceEditor() {
  const blueprint = structuredClone(researchWorkspace.blueprint);
  blueprint.experience_version = $('#experience-enabled').checked ? 1 : 0;
  delete blueprint.experience_policy;
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
      const quote = select.closest('.source-reference').querySelector('[data-quote]').value;
      if (!quote.trim() || !source.text.includes(quote)) {
        throw new Error(`${source.id}: quoted evidence must be an exact, contiguous part of the source.`);
      }
      references.push({ source_id: source.id, quote, relation: select.value });
    });
    mapping.accounts.push({ id, explanation: field('explanation'), missing_evidence: field('missing_evidence'), references });
  });
  return { blueprint, mapping };
}

$('#prototype-image').addEventListener('change', async event => {
  prototypeImage = null;
  $('#prototype-preview').hidden = true;
  const file = event.target.files[0];
  if (!file) return;
  if (!['image/png', 'image/jpeg'].includes(file.type) || file.size > 1_000_000) {
    event.target.value = '';
    showError('Choose a PNG or JPEG screenshot smaller than 1 MB.');
    return;
  }
  try {
    prototypeImage = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Could not read the selected screenshot.'));
      reader.readAsDataURL(file);
    });
    $('#prototype-preview').src = prototypeImage;
    $('#prototype-preview').hidden = false;
    if ($('#review-current')) $('#review-current').textContent = 'A screenshot is selected. Run Muse review to include it.';
  } catch (error) { showError(error.message); }
});

$('#workspace-review').addEventListener('input', event => {
  if (event.target.closest('#mechanism-workbench')) return;
  if (event.target.id === 'prototype-image' || event.target.id === 'workspace-approved') return;
  if ($('#review-current')) $('#review-current').textContent = 'Design inputs have been edited. The saved review may be out of date; run it again before relying on it.';
  $('#workspace-approved').checked = false;
});

$('#challenge-design').addEventListener('click', async () => {
  clearError();
  if (!researchWorkspace) return;
  const button = $('#challenge-design');
  button.disabled = true;
  button.textContent = 'Muse is reviewing the design in three runs…';
  $('#approve-workspace').disabled = true;
  $('#workspace-review').querySelectorAll('input, textarea, select').forEach(input => { if (!input.closest('#mechanism-workbench')) input.disabled = true; });
  try {
    const { blueprint, mapping } = readWorkspaceEditor();
    const reviewed = await api('/api/research/review', {
      id: researchWorkspace.id, blueprint, mapping, prototype_image: prototypeImage,
    });
    renderWorkspace(reviewed);
    $('#workspace-approved').checked = false;
  } catch (error) { showError(error.message); }
  finally {
    const approved = researchWorkspace.status === 'approved';
    button.disabled = approved;
    button.textContent = 'Challenge this design with Muse';
    $('#approve-workspace').disabled = approved;
    $('#workspace-review').querySelectorAll('input, textarea, select').forEach(input => { if (!input.closest('#mechanism-workbench')) input.disabled = approved; });
  }
});

$('#approve-workspace').addEventListener('click', async () => {
  clearError();
  if (!researchWorkspace) return;
  const button = $('#approve-workspace');
  button.disabled = true;
  try {
    const { blueprint, mapping } = readWorkspaceEditor();
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
        ${typeof uxAggregateHtml === 'function' ? uxAggregateHtml(brief.ux_research) : ''}
        <p>${escapeHtml(brief.decision)}</p>
        <p>${brief.completed_sessions} completed sessions · ${brief.response_checks_passed} with sufficient choice coverage ·
          ${brief.inconclusive_response_checks} with insufficient choice coverage · ${brief.weak_model_separation} with weak model separation.</p>
        <p>${escapeHtml(brief.next_step)}</p>
        <h4>Choices by exact task</h4>
        <p>Each denominator contains recorded responses to that adaptively assigned task. Repeats are excluded. These shares cannot be pooled into population preferences.</p>
        ${(brief.pairwise_choices || []).map(task => `<details class="trace-entry"><summary>${escapeHtml(task.experiment_id)} · ${task.exposures_with_recorded_response} recorded responses</summary>
          <div class="trace-options"><div><strong>Canonical A</strong><ul>${task.canonical_a.map(fact => `<li>${escapeHtml(fact)}</li>`).join('')}</ul></div><div><strong>Canonical B</strong><ul>${task.canonical_b.map(fact => `<li>${escapeHtml(fact)}</li>`).join('')}</ul></div></div>
          <p>A: ${task.counts.a}; B: ${task.counts.b}; neither: ${task.counts.outside}. A share among A/B responses: ${task.canonical_a_share_among_ab === null ? 'unavailable' : `${Math.round(task.canonical_a_share_among_ab * 100)}% (${task.counts.a}/${task.informative_responses})`}.</p></details>`).join('')}
        <p>Repeated task: ${brief.repeat_agreement?.consistent || 0} same, ${brief.repeat_agreement?.inconsistent || 0} different, ${brief.repeat_agreement?.unavailable || 0} unavailable. Descriptive only; disagreement does not exclude a session.</p>
        <details><summary>Secondary model diagnostics: session leaders</summary>
          <ul>${Object.entries(brief.session_leader_counts).map(([id, count]) => `<li>${escapeHtml(labelsById[id])}: ${count} sessions</li>`).join('')}</ul>
        </details>
        <h4>Compare source interpretations with these sessions</h4>
        ${(brief.account_evidence || []).map(account => `<details class="trace-entry"><summary>${escapeHtml(labelsById[account.account])}: ${account.sessions_led} session leaders</summary>
          <p>Tested levels: ${escapeHtml(account.baseline_level)} versus ${escapeHtml(account.alternative_level)}.</p>
          <p>${escapeHtml(account.explanation)}</p>
          ${account.source_references.map(ref => `<p>${escapeHtml(ref.source_id)} · ${escapeHtml(ref.relation)}</p><blockquote>${escapeHtml(ref.quote)}</blockquote>`).join('')}
          <p>Missing evidence: ${escapeHtml(account.missing_evidence)}</p><p>${escapeHtml(account.interpretation)}</p></details>`).join('')}
        <details><summary>Inspect individual and contradictory cases</summary>
          ${brief.session_cases.map(item => `<p>Session ${item.case}: ${escapeHtml(item.response_quality)} response quality; leading model ${escapeHtml(labelsById[item.leading_account])} (${Math.round(item.model_probability * 100)}%); stated priorities ${escapeHtml(item.stated_priorities.map(id => labelsById[id]).join(', '))}; outside choices ${item.outside_choices}; repeat ${item.holdout_consistent === true ? 'consistent' : 'inconsistent or unavailable'}.</p>`).join('')}
        </details>
        <h4>Proposed field contrasts — not executed</h4>
        <p>${escapeHtml(brief.field_test_basis || '')}</p>
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
    `${brief.completed_sessions} completed sessions; ${brief.response_checks_passed} with sufficient choice coverage; ` +
      `${brief.inconclusive_response_checks} with insufficient choice coverage; ${brief.weak_model_separation} with weak model separation.`, '',
    brief.next_step, '',
  ];
  if (typeof uxAggregateMarkdown === 'function' && brief.ux_research) lines.push(uxAggregateMarkdown(brief.ux_research));
  lines.push('## Choices by exact task (primary descriptive output)', '',
    'Task-specific denominators reflect adaptive assignment and recorded answers. Repeats are excluded; do not pool shares or infer population preferences.', '');
  (brief.pairwise_choices || []).forEach(task => lines.push(`### ${task.experiment_id}`, '',
    `Canonical A: ${task.canonical_a.join('; ')}`, '', `Canonical B: ${task.canonical_b.join('; ')}`, '',
    `A: ${task.counts.a}; B: ${task.counts.b}; neither: ${task.counts.outside}. Recorded responses: ${task.exposures_with_recorded_response}; A/B denominator: ${task.informative_responses}.`, ''));
  lines.push('## Secondary model diagnostics: session leaders', '',
    ...Object.entries(brief.session_leader_counts).map(([id, count]) => `- ${labelById[id]}: ${count} sessions`), '',
    '## Competing explanations', '');
  brief.mapping.accounts.forEach(account => {
    lines.push(`### ${labelById[account.id]}`, '', account.explanation, '', `Missing evidence: ${account.missing_evidence}`, '');
    if (!account.references.length) lines.push('No source relationships assigned.', '');
    account.references.forEach(ref => lines.push(`- ${ref.source_id}: ${ref.relation} (${ref.source_kind})`, `  > ${ref.quote.replace(/\n/g, '\n  > ')}`, ''));
  });
  lines.push('## Other explanations and unresolved questions', '', ...brief.mapping.unresolved.map(item => `- ${item}`), '');
  if (brief.design_review) {
    const review = brief.design_review;
    lines.push('## Muse critical design review', '',
      `Reviewer: ${review.source}. Review matches current design: ${brief.design_review_current ? 'yes' : 'no; inputs changed'}.`, '',
      review.summary, '', review.scope, '');
    if (review.runs) {
      lines.push('### Independent review stages', '', 'Topic frequency is run consistency, not confidence or identical findings.', '');
      review.topic_frequency.forEach(item => lines.push(`- ${item.topic}: ${item.raised_in}/${item.completed_runs} completed design runs (${item.planned_runs} planned)`));
      review.runs.forEach(run => lines.push('', `#### ${run.stage} run ${run.run}: ${run.status}`, '', run.status === 'ok' ? run.summary : run.error, '',
        ...(run.findings || []).flatMap(f => [f.observation, '', `Control: ${f.suggested_control}`, ''])));
    }
    review.findings.forEach(finding => lines.push(
      `### ${finding.basis}${finding.source_ids.length ? ': ' + finding.source_ids.join(', ') : ''}`, '',
      `Observation: ${finding.observation}`, '',
      ...(finding.quote ? [`> ${finding.quote.replace(/\n/g, '\n> ')}`, ''] : []),
      `Competing explanation: ${finding.alternative_explanation}`, '',
      `Suggested control: ${finding.suggested_control}`, '',
    ));
    lines.push(...review.unresolved.map(item => `- ${item}`), '');
    if (review.prototype) lines.push(`Reviewed screenshot digest: ${review.prototype.sha256}`, '');
  }
  lines.push('## Proposed field contrasts — not executed', '');
  lines.push(brief.field_test_basis || 'Generic single-factor templates, not result-derived recommendations.', '');
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
