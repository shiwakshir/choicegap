let interviewStep = null;

function interviewOptions(stimulus, clickable = false) {
  return ['a', 'b'].map(side => `<${clickable ? 'button type="button"' : 'article'} class="choice" ${clickable ? `data-interview-choice="${side}"` : ''}>
    <h2>Option ${side.toUpperCase()}</h2><ul>${stimulus[side].facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
    </${clickable ? 'button' : 'article'}>`).join('');
}

function renderInterview(step) {
  interviewStep = step;
  try { sessionStorage.setItem('choicegap-interview', JSON.stringify({session: state.sessionId, study: state.studyId})); } catch (_) {}
  show('explore');
  $('#explore-question').textContent = step.question;
  $('#explore-question').focus();
  $('#explore-progress').textContent = 'Optional follow-up · You can skip any question.';
  $('#explore-context').innerHTML = step.context ? `<p>Your earlier choice: ${step.context.choice === 'outside' ? 'neither option' : `Option ${step.context.choice.toUpperCase()}`}</p><div class="choices">${interviewOptions(step.context.stimulus)}</div>` : step.response_context ? `<p>Your earlier response:</p><blockquote>${escapeHtml(step.response_context)}</blockquote>` : '';
  $('#explore-form').hidden = step.kind === 'choice';
  $('#explore-check').hidden = step.phase !== 'check';
  $('#explore-text').value = '';
  $('#explore-text-label').textContent = step.phase === 'check' ? 'Correction or additional context (optional unless correcting)' : 'Your response (optional)';
  $('#explore-status').value = 'unresolved';
  $('#explore-factor').innerHTML = '<option value="unresolved">Other / no single detail / unsure</option>' + (step.factors || []).map(f => `<option value="${escapeHtml(f.id)}">${escapeHtml(f.label)}</option>`).join('');
  $('#explore-interpretation').textContent = step.interpretation ? `Tentative description for you to check: ${step.interpretation.summary}` : '';
  $('#explore-choices').innerHTML = step.kind === 'choice' ? interviewOptions(step.stimulus, true) + '<button type="button" class="outside" data-interview-choice="outside">Neither option — keep my usual choice</button>' : '';
  $('#explore-choices').querySelectorAll('[data-interview-choice]').forEach(b => b.addEventListener('click', () => submitInterview({choice: b.dataset.interviewChoice})));
  $('#explore').querySelectorAll('button').forEach(b => b.disabled = false);
}

async function submitInterview(fields) {
  clearError();
  $('#explore').querySelectorAll('button').forEach(b => b.disabled = true);
  $('#explore-progress').textContent = 'Saving your response…';
  try {
    const data = await api('/api/explore', {session_id: state.sessionId, answer_token: interviewStep.answer_token, ...fields});
    if (data.done) {
      try { sessionStorage.removeItem('choicegap-interview'); } catch (_) {}
      renderReport(data.report, data.narrative);
    } else renderInterview(data.interview);
  } catch (error) {
    showError(error.message);
    $('#explore-progress').textContent = 'Your response has not advanced. You can correct it or retry.';
    $('#explore').querySelectorAll('button').forEach(b => b.disabled = false);
  }
}

$('#explore-form').addEventListener('submit', event => {
  event.preventDefault();
  submitInterview({text: $('#explore-text').value, status: $('#explore-status').value, factor: $('#explore-factor').value});
});
$('#explore-skip').addEventListener('click', () => submitInterview({choice: 'skip', text: '', status: 'unresolved', factor: 'unresolved'}));

function uxAnalysisHtml(a) {
  const explanation = a.participant_explanation;
  return `<section class="brief-section"><h3>Ask → Observe → Explore → Synthesize</h3>
    <h4>Stated context</h4><p>${escapeHtml(a.survey.statement || 'No optional survey comment.')}</p>
    <p>${escapeHtml(a.alignment.trigger)} ${escapeHtml(a.alignment.interpretation)}</p>
    <h4>Participant explanation · ${escapeHtml(explanation.status)}</h4>
    <p>${escapeHtml(explanation.effective)}</p><p>Interpretation source: ${escapeHtml(explanation.source)}. Original interpretation and corrections remain in the evidence record.</p>
    ${a.untested_participant_factor ? `<p>The participant selected factor ${escapeHtml(a.untested_participant_factor)}, which was not varied in the anchor task. This explanation remains untested by the two comparisons.</p>` : ''}
    <details><summary>Inspect original interpretation and correction</summary><p>${escapeHtml(explanation.original_model_interpretation.summary)}</p><p>Quoted response: ${escapeHtml(explanation.original_model_interpretation.quote)}</p><p>Correction: ${escapeHtml(explanation.correction.text || 'None supplied.')}</p></details>
    <h4>Which conditions coincided with a different choice?</h4>
    ${a.condition_tests.length ? a.condition_tests.map(c => `<article class="trace-entry"><h4>${escapeHtml(c.factor_label)}</h4>
      <p>On baseline Option ${escapeHtml(c.changed.baseline_option.toUpperCase())}: ${escapeHtml(c.changed.before)} → ${escapeHtml(c.changed.after)}. All other displayed facts fixed relative to the baseline.</p>
      <p>${c.response?.switched === true ? 'Selected option changed.' : c.response?.switched === false ? 'Selected option stayed the same.' : 'No A/B switch comparison: skipped, neither, or unanswered.'} This is descriptive, not a causal effect.</p>
      <p>${escapeHtml(c.recommendation)}</p><p>Evidence: ${escapeHtml(c.evidence_refs.join(', '))}</p>
      <details><summary>Inspect exact condition task and recorded plan</summary><p>${escapeHtml(c.selection_reason)}</p><div class="choices">${interviewOptions(c.stimulus)}</div><p>Stimulus digest: ${escapeHtml(c.stimulus_sha256)}</p></details></article>`).join('') : '<p>No suitable A/B anchor; condition comparisons were not issued.</p>'}
    <h4>Behavioural interpretation and alternatives</h4><p>${escapeHtml(a.behavioural_interpretation.scope)}</p>
    <p>Consider: ${escapeHtml(a.behavioural_interpretation.lenses.join('; '))}.</p><p>Rivals: ${escapeHtml(a.behavioural_interpretation.rivals.join('; '))}.</p>
    <details><summary>Participant evidence and follow-up trail</summary>${a.exposure_ledger.map(e => `<article class="trace-entry"><strong>${escapeHtml(e.id)}</strong><p>${escapeHtml(e.question)}</p><blockquote>${escapeHtml(e.response || '[Skipped]')}</blockquote><p>Recorded branch reason: ${escapeHtml(e.reason)}</p></article>`).join('')}</details>
    <h4>Limits before action</h4><ul>${a.limitations.map(l => `<li>${escapeHtml(l)}</li>`).join('')}</ul></section>`;
}

function uxAggregateHtml(research) {
  if (!research?.completed_interviews) return '';
  return `<section class="brief-section"><h3>Integrated UX analysis</h3><p>${research.completed_interviews} completed interviews. ${escapeHtml(research.scope)}</p>
    <p>${research.collection_progress?.unfinished_interviews || 0} unfinished interviews. ${escapeHtml(research.collection_progress?.scope || '')}</p>
    <table class="ux-exposure-table"><caption>Questions issued among completed interviews</caption><thead><tr><th scope="col">Stage</th><th scope="col">Issued</th><th scope="col">Answered</th></tr></thead><tbody>${research.exposures.map(e => `<tr><th scope="row">${escapeHtml(({why:'Choice explanation',clarify:'Possible circumstances',check:'Interpretation check',reflection:'Final reflection',condition0:'First comparison',condition1:'Rival comparison'})[e.phase] || e.phase)}</th><td>${e.shown}</td><td>${e.answered}</td></tr>`).join('')}</tbody></table>
    <h4>Comparable conditions</h4><p>Each row contains only matching baseline facts and the same changed detail. Counts are conditional on adaptive assignment and do not estimate population effects.</p>
    ${(research.condition_groups || []).map(g => `<p>${escapeHtml(g.factor)}: ${escapeHtml(g.changed.before)} → ${escapeHtml(g.changed.after)}. ${g.switches}/${g.ab_responses} A/B responses switched; ${g.shown} issued, ${g.outside} neither, ${g.skipped} skipped.</p>`).join('')}
    ${research.cases.map((c, i) => `<details><summary>Case ${i + 1} · ${escapeHtml(c.analysis.participant_explanation.status)}</summary>${uxAnalysisHtml(c.analysis)}</details>`).join('')}</section>`;
}

function uxAggregateMarkdown(research) {
  const lines = ['## Integrated UX analysis', '', research.scope, '', '| Stage | Issued | Answered |', '|---|---:|---:|', ...research.exposures.map(e => `| ${e.phase} | ${e.shown} | ${e.answered} |`), '', `Unfinished interviews: ${research.collection_progress?.unfinished_interviews || 0}. ${research.collection_progress?.scope || ''}`, ''];
  research.cases.forEach((c, i) => {
    const a = c.analysis;
    lines.push(`### Case ${i + 1}`, '', `Participant interpretation (${a.participant_explanation.status}): ${a.participant_explanation.effective}`, '', a.alignment.interpretation, '');
    a.condition_tests.forEach(t => lines.push(`Condition ${t.id}: ${t.factor_label}; ${t.changed.before} → ${t.changed.after}.`, `Choice changed: ${t.response?.switched ?? 'not comparable'}. ${t.recommendation}`, `Evidence: ${t.evidence_refs.join(', ')}.`, ''));
    a.evidence.forEach(e => lines.push(`${e.id} (${e.kind}):`, `> ${e.text.replace(/\n/g, '\n> ') || '[Skipped]'}`, ''));
    lines.push('Behavioural lenses (candidates only): ' + a.behavioural_interpretation.lenses.join('; '), 'Rivals: ' + a.behavioural_interpretation.rivals.join('; '), '', ...a.limitations.map(l => `- ${l}`), '');
  });
  return lines.join('\n');
}

async function resumeInterview() {
  if (researcherMode || new URLSearchParams(location.search).has('mechanism')) return;
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem('choicegap-interview')); } catch (_) { return; }
  if (!saved || (saved.study || null) !== (new URLSearchParams(location.search).get('study') || null)) return;
  try {
    const data = await api('/api/explore/resume', {session_id: saved.session});
    state.sessionId = saved.session;
    if (data.done) {
      sessionStorage.removeItem('choicegap-interview');
      renderReport(data.report, data.narrative);
    } else renderInterview(data.interview);
  } catch (_) { showError('The saved follow-up could not be reopened. Refresh to retry, or ask the researcher for help.'); }
}
resumeInterview();
