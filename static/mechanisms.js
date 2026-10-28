let mechanismCatalogue = null;
let mechanismWorkspace = null;
let mechanismPlan = null;
let mechanismSelected = 'default';
let mechanismAssignment = null;

function mechanismLink(id) {
  const url = new URL('/', window.location.href);
  url.searchParams.set('mechanism', id);
  return url.href;
}

function saveMechanismEditor() {
  if (!mechanismPlan || !$('#mechanism-explanation')) return;
  const account = mechanismPlan.accounts.find(a => a.id === mechanismSelected);
  account.explanation = $('#mechanism-explanation').value;
  account.missing_evidence = $('#mechanism-missing').value;
  account.references = [];
  $('#mechanism-editor').querySelectorAll('[data-mechanism-source]').forEach(select => {
    if (select.value === 'none') return;
    const source = mechanismWorkspace.sources.find(s => s.id === select.dataset.mechanismSource);
    const quote = select.closest('.source-reference').querySelector('textarea').value;
    if (!quote.trim() || !source.text.includes(quote)) throw new Error(`${source.id}: use an exact quotation from this source.`);
    account.references.push({source_id: source.id, quote, relation: select.value});
  });
}

function renderMechanismEditor() {
  const spec = mechanismCatalogue.mechanisms.find(s => s.id === mechanismSelected);
  const account = mechanismPlan.accounts.find(a => a.id === mechanismSelected);
  $('#mechanism-approved').checked = false;
  $('#mechanism-editor').innerHTML = `
    <p><strong>Hypothesis, not an established explanation:</strong> ${escapeHtml(spec.hypothesis)}</p>
    <label for="mechanism-explanation">Why this might explain the supplied evidence</label>
    <textarea id="mechanism-explanation" rows="3">${escapeHtml(account.explanation)}</textarea>
    <label for="mechanism-missing">Evidence still needed</label>
    <textarea id="mechanism-missing" rows="2">${escapeHtml(account.missing_evidence)}</textarea>
    <details><summary>Inspect and edit source links</summary>
      ${mechanismWorkspace.sources.map(source => {
        const refs = account.references.filter(r => r.source_id === source.id);
        return (refs.length ? refs : [null]).map(ref => `<div class="source-reference">
          <label>${escapeHtml(sourceName(source))}<select data-mechanism-source="${source.id}">
            ${[['none','Not assigned'],['supports','Supports'],['challenges','Challenges'],['context','Context']].map(([v,label]) => `<option value="${v}" ${v === (ref?.relation || 'none') ? 'selected' : ''}>${label}</option>`).join('')}
          </select></label>
          <label>Exact quotation<textarea rows="2">${escapeHtml(ref?.quote || source.text)}</textarea></label>
          <p>Original: ${escapeHtml(source.text)}</p></div>`).join('');
      }).join('')}
    </details>
    <h4>Rival explanations</h4><ul>${spec.rivals.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
    <p><strong>What would weaken this account:</strong> ${escapeHtml(spec.falsification)}</p>
    <p><strong>Design:</strong> ${escapeHtml(spec.design)}</p>
    <p>${escapeHtml(spec.assignment)}</p><p>${escapeHtml(spec.context)}</p>
    <details><summary>Review every exact experimental arm (${spec.arms.length})</summary>
      ${spec.arms.map(arm => `<article class="mechanism-arm"><h4>${escapeHtml(arm.label)}</h4>
        <div class="trace-options">${['a','b'].map(side => `<div><strong>Canonical ${side.toUpperCase()}</strong><ul>${Object.values(arm[side]).map(fact => `<li>${escapeHtml(fact)}</li>`).join('')}</ul></div>`).join('')}</div>
        <p>Preselection: ${arm.default ? `canonical ${arm.default.toUpperCase()}` : 'none'}.</p></article>`).join('')}
    </details>
    <p><strong>Primary contrast:</strong> ${escapeHtml(spec.contrast.label)}. Outcome: confirmed focal-option choice.</p>
    <p><strong>Limits:</strong> ${escapeHtml(spec.boundary)}</p>
    <p>The numbers describe hypothetical stimuli, not measured delivery emissions or actual service promises.</p>
    <details><summary>Behavioural-science sources and scope</summary>
      <ul>${spec.sources.map(s => `<li><a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.title)}</a></li>`).join('')}</ul>
      <p>Theory motivates these operational adaptations; it does not validate this grocery study or identify a person's motivation.</p>
    </details>`;
}

async function loadMechanismStudies() {
  const data = await researchGet(`/api/mechanisms/studies?id=${encodeURIComponent(mechanismWorkspace.id)}`);
  $('#mechanism-studies').replaceChildren();
  if (data.studies.length) {
    const heading = document.createElement('strong'); heading.textContent = 'Approved behavioural experiments';
    $('#mechanism-studies').append(heading);
  }
  data.studies.forEach((study, index) => {
    const block = document.createElement('div');
    const link = document.createElement('a');
    link.href = mechanismLink(study.id);
    link.target = '_blank'; link.rel = 'noopener';
    link.textContent = `Study ${index + 1}: ${study.label} · open participant study`;
    const reportButton = document.createElement('button');
    reportButton.type = 'button'; reportButton.className = 'secondary';
    reportButton.textContent = `Review results: Study ${index + 1} · ${study.label}`;
    reportButton.addEventListener('click', () => showMechanismResults(study.id));
    block.append(link, reportButton); $('#mechanism-studies').append(block);
  });
}

async function showMechanismWorkspace(workspace) {
  if (!researcherMode || mechanismWorkspace?.id === workspace.id) return;
  mechanismWorkspace = workspace;
  $('#mechanism-workbench').hidden = false;
  $('#mechanism-results').replaceChildren();
  try {
    mechanismCatalogue ||= await researchGet('/api/mechanisms/catalog');
    const plan = await researchGet(`/api/mechanisms/plan?id=${encodeURIComponent(workspace.id)}`);
    if (mechanismWorkspace.id !== workspace.id) return;
    mechanismPlan = plan;
    $('#mechanism-select').innerHTML = mechanismCatalogue.mechanisms.map(s => `<option value="${s.id}">${escapeHtml(s.label)}</option>`).join('');
    $('#mechanism-select').value = mechanismSelected;
    $('#mechanism-plan-status').textContent = `Planning source: ${plan.source}. Unlinked hypotheses require source review. ${plan.unresolved.join(' ')}`;
    renderMechanismEditor(); await loadMechanismStudies();
  } catch (error) { showError(error.message); }
}

document.addEventListener('choicegap-workspace', event => showMechanismWorkspace(event.detail));
if (researchWorkspace) showMechanismWorkspace(researchWorkspace);

$('#mechanism-select').addEventListener('change', event => {
  try { saveMechanismEditor(); mechanismSelected = event.target.value; renderMechanismEditor(); }
  catch (error) { event.target.value = mechanismSelected; showError(error.message); }
});
$('#mechanism-editor').addEventListener('input', () => { $('#mechanism-approved').checked = false; });
$('#mechanism-plan-button').addEventListener('click', async () => {
  clearError(); const button = $('#mechanism-plan-button'); button.disabled = true;
  $('#mechanism-plan-status').textContent = 'Muse is connecting sources to competing mechanisms…';
  try {
    mechanismPlan = await api('/api/mechanisms/plan', {workspace_id: mechanismWorkspace.id});
    $('#mechanism-plan-status').textContent = `Planning source: ${mechanismPlan.source}. ${mechanismPlan.unresolved.join(' ')}`;
    renderMechanismEditor();
  } catch (error) { showError(error.message); $('#mechanism-plan-status').textContent = 'Planning was unavailable. The manual catalogue remains usable.'; }
  finally { button.disabled = false; }
});
$('#mechanism-publish').addEventListener('click', async () => {
  clearError(); const button = $('#mechanism-publish'); button.disabled = true;
  try {
    saveMechanismEditor();
    await api('/api/mechanisms/approve', {workspace_id: mechanismWorkspace.id, plan: mechanismPlan,
      mechanism_id: mechanismSelected, confirmed: $('#mechanism-approved').checked});
    $('#mechanism-approved').checked = false;
    await loadMechanismStudies();
  } catch (error) { showError(error.message); }
  finally { button.disabled = false; }
});

async function showMechanismResults(identifier) {
  clearError();
  try {
    const result = await researchGet(`/api/mechanisms/report?id=${encodeURIComponent(identifier)}`);
    const c = result.contrast;
    const pp = value => `${(value * 100).toFixed(1)} percentage points`;
    $('#mechanism-results').innerHTML = `<section class="brief-section"><h3>Behavioural explanation brief: ${escapeHtml(result.study.protocol.label)}</h3>
      <p>${escapeHtml(result.evidence_status)}</p><p>${escapeHtml(result.study.account.explanation)}</p>
      <h4>Response to the manipulation</h4>
      <table class="mechanism-table"><thead><tr><th>Arm</th><th>Assigned</th><th>Completed</th><th>Focal</th><th>Other</th><th>Neither</th><th>Missing</th></tr></thead>
        <tbody>${Object.values(result.arms).map(a => `<tr><td>${escapeHtml(a.label)}</td><td>${a.assigned}</td><td>${a.completed}</td><td>${a.a}</td><td>${a.b}</td><td>${a.outside}</td><td>${a.missing}</td></tr>`).join('')}</tbody></table>
      <p><strong>${escapeHtml(result.study.protocol.contrast.label)}:</strong> ${c.estimate === null ? 'Not yet estimable' : `${pp(c.estimate)}; uncertainty range ${pp(c.lower)} to ${pp(c.upper)}`}.</p>
      <p>${escapeHtml(c.status)}</p><p>${escapeHtml(result.why_summary)}</p>
      <details><summary>Analysis assumptions</summary><p>${escapeHtml(c.method || 'Required experimental arms need responses.')}</p><p>Estimates use completed responses; missing assignments remain visible and may bias comparison.</p></details>
      <h4>What remains a rival explanation</h4><ul>${result.study.protocol.rivals.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
      <h4>Evidence still needed</h4><p>${escapeHtml(result.study.account.missing_evidence)}</p>
      ${result.study.account.references.map(r => `<p>${escapeHtml(r.source_id)} · ${escapeHtml(r.relation)}</p><blockquote>${escapeHtml(r.quote)}</blockquote>`).join('')}
      <ul>${result.limitations.map(l => `<li>${escapeHtml(l)}</li>`).join('')}</ul>
      <button type="button" class="secondary" id="mechanism-export-json">Download mechanism evidence (.json)</button>
      <button type="button" class="secondary" id="mechanism-export-md">Download explanation brief (.md)</button></section>`;
    $('#mechanism-export-json').addEventListener('click', () => downloadResearch(JSON.stringify(result, null, 2), 'choicegap-mechanism-evidence.json', 'application/json'));
    $('#mechanism-export-md').addEventListener('click', () => downloadResearch(mechanismMarkdown(result), 'choicegap-mechanism-brief.md', 'text/markdown'));
  } catch (error) { showError(error.message); }
}

function mechanismMarkdown(result) {
  const spec = result.study.protocol;
  const c = result.contrast;
  return [`# Behavioural explanation brief: ${spec.label}`, '', `Evidence origin: ${result.study.evidence_origin}. Planning source: ${result.study.planning_source}.`, '',
    result.study.decision, '', '## Hypothesis and operational test', '', result.study.account.explanation, '', spec.design, '', spec.falsification, '',
    '## Experimental arm results', '', '| Arm | Assigned | Completed | Focal | Other | Neither | Missing |', '|---|---:|---:|---:|---:|---:|---:|',
    ...Object.values(result.arms).map(a => `| ${a.label} | ${a.assigned} | ${a.completed} | ${a.a} | ${a.b} | ${a.outside} | ${a.missing} |`), '',
    `Primary contrast: ${spec.contrast.label}.`, '', `Estimate: ${c.estimate}; lower: ${c.lower}; upper: ${c.upper} (proportion units). ${c.status}`, '', c.method || '', '', result.why_summary, '',
    '## Rival explanations', '', ...spec.rivals.map(r => `- ${r}`), '', '## Missing evidence', '', result.study.account.missing_evidence, '',
    ...result.study.account.references.flatMap(r => [`${r.source_id}: ${r.relation}`, '', `> ${r.quote.replace(/\n/g, '\n> ')}`, '']),
    '## Limits', '', ...result.limitations.map(l => `- ${l}`), '', '## Scientific sources', '', ...spec.sources.map(s => `- [${s.title}](${s.url})`), '',
    `Locked design fingerprint: ${result.study.design_sha256}`, ''].join('\n');
}

const mechanismStudyId = new URLSearchParams(window.location.search).get('mechanism');
if (mechanismStudyId && !researcherMode) {
  show('mechanism-participant');
  researchGet(`/api/mechanisms/participant?id=${encodeURIComponent(mechanismStudyId)}`).then(data => {
    $('#mechanism-question').textContent = data.question;
    $('#mechanism-context').textContent = data.context;
  }).catch(error => { $('#mechanism-begin').disabled = true; showError(error.message); });
}
$('#mechanism-begin').addEventListener('click', async () => {
  clearError(); const button = $('#mechanism-begin'); button.disabled = true;
  try {
    mechanismAssignment = await api('/api/mechanisms/start', {study_id: mechanismStudyId, consent: $('#mechanism-consent').checked});
    const stimulus = mechanismAssignment.stimulus;
    $('#mechanism-intake').hidden = true;
    $('#mechanism-choice-form').hidden = false;
    $('#mechanism-choices').innerHTML = `<legend>Delivery options</legend>${['a','b'].map(side => `<label>
      <input type="radio" name="mechanism-choice" value="${side}" ${stimulus.default === side ? 'checked' : ''}>
      <strong>Option ${side.toUpperCase()}</strong><ul>${stimulus[side].map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul></label>`).join('')}
      <label class="mechanism-neither"><input type="radio" name="mechanism-choice" value="outside"> Neither option</label>`;
  } catch (error) { button.disabled = false; showError(error.message); }
});
$('#mechanism-choice-form').addEventListener('submit', async event => {
  event.preventDefault(); clearError(); const button = $('#mechanism-submit'); button.disabled = true;
  try {
    const choice = $('#mechanism-choices input:checked')?.value;
    if (!choice) throw new Error('Choose an option or Neither before confirming.');
    await api('/api/mechanisms/answer', {id: mechanismAssignment.id, answer_token: mechanismAssignment.answer_token, choice});
    $('#mechanism-choice-form').hidden = true; $('#mechanism-complete').hidden = false;
  } catch (error) { button.disabled = false; showError(error.message); }
});
