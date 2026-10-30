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

const uxStageNames = {why:'Choice explanation', clarify:'Possible circumstances', check:'Interpretation check', reflection:'Final explanation', condition0:'First comparison', condition1:'Second comparison'};

function uxFactorName(a, id) {
  return a.factor_labels?.[id] || a.condition_tests.find(c => c.factor === id)?.factor_label || (typeof labels !== 'undefined' ? labels[id] : null) || id;
}

function uxChange(c) {
  // Older records include the factor name in both facts. Show it once, in the heading.
  const trim = value => value.startsWith(c.factor_label + ': ') ? value.slice(c.factor_label.length + 2) : value;
  return `${trim(c.changed.before)} → ${trim(c.changed.after)}`;
}

function uxOutcome(c) {
  if (c.response?.switched === true) return 'They switched to the other option.';
  if (c.response?.switched === false) return 'They chose the same option again.';
  if (c.response?.displayed_choice === 'outside') return 'They chose neither option, so we cannot compare two selected options.';
  return 'They skipped this comparison.';
}

function uxReadout(a) {
  const changed = a.condition_tests.filter(c => c.response?.switched === true);
  const unchanged = a.condition_tests.filter(c => c.response?.switched === false);
  const name = list => list.map(c => c.factor_label.toLowerCase()).join(' and ');
  const summary = changed.length
    ? `This participant chose differently after ${name(changed)} changed.${unchanged.length ? ` Changing ${name(unchanged)} did not change their selection.` : ''}`
    : unchanged.length ? 'The participant chose the same option in the answered follow-up comparisons.'
    : 'There are not enough follow-up answers to tell what would change this participant’s choice.';
  const next = changed.length
    ? `Retest the ${name(changed)} change with more participants. Check whether their explanations support the same product change.`
    : unchanged.length ? 'Explore a different change or a constraint the options did not cover. Repeating the same choice does not tell us that these details never matter.'
    : 'Collect the missing comparisons before recommending a product change.';
  const ratings = Object.values(a.survey.ratings);
  const priorities = new Set(ratings).size === 1
    ? `They gave all four factors the same importance rating (${ratings[0]}/5).`
    : `They rated ${a.stated_priorities.map(id => uxFactorName(a, id).toLowerCase()).join(' and ')} highest (${Math.max(...ratings)}/5).`;
  return {summary, next, priorities};
}

function uxChoiceDescription(a) {
  const anchor = a.alignment.anchor;
  if (!anchor) return 'No earlier choice was available to review.';
  if (anchor.displayed_choice === 'outside') return 'They chose neither of the available options.';
  const selected = anchor.stimulus[anchor.displayed_choice].facts;
  const other = anchor.stimulus[anchor.displayed_choice === 'a' ? 'b' : 'a'].facts;
  const differing = selected.map((fact, index) => index).filter(index => selected[index] !== other[index]);
  if (!differing.length) return `They selected Option ${anchor.displayed_choice.toUpperCase()}. Both options showed the same details.`;
  const names = [...Object.values(a.factor_labels || {}), ...a.condition_tests.map(c => c.factor_label), ...Object.values(typeof labels !== 'undefined' ? labels : {})];
  const wording = fact => {
    const prefix = names.find(name => fact.startsWith(name + ': '));
    const text = prefix ? fact.slice(prefix.length + 2) : fact;
    return text.charAt(0).toLowerCase() + text.slice(1);
  };
  return `They chose the option with ${differing.map(i => wording(selected[i])).join(' and ')}. The other option offered ${differing.map(i => wording(other[i])).join(' and ')}.`;
}

function uxAnalysisHtml(a) {
  const explanation = a.participant_explanation;
  const readout = uxReadout(a);
  const anchor = a.alignment.anchor;
  const why = a.evidence.find(e => e.id === 'interview.why')?.text;
  const reflection = a.evidence.find(e => e.id === 'interview.reflection')?.text;
  const checked = explanation.status === 'corrected' ? 'The participant corrected the description:' : explanation.status === 'confirmed' ? 'The participant accepted this description:' : 'The participant did not confirm an explanation.';
  return `<section class="brief-section"><h3>What we learned</h3><p class="lede">${escapeHtml(readout.summary)}</p>
    <h4>What they said mattered</h4><p>${escapeHtml(readout.priorities)}</p>
    ${a.survey.statement ? `<blockquote>${escapeHtml(a.survey.statement)}</blockquote>` : ''}
    <h4>What they chose</h4>
    <p>${escapeHtml(uxChoiceDescription(a))}</p>
    ${anchor ? `<details><summary>See the options they compared</summary><div class="choices">${interviewOptions(anchor.stimulus)}</div></details>` : ''}
    <h4>Why they chose it</h4>${why ? `<blockquote>${escapeHtml(why)}</blockquote>` : '<p>They did not explain this choice.</p>'}
    <p>${escapeHtml(checked)}</p>${explanation.status !== 'unresolved' ? `<blockquote>${escapeHtml(explanation.effective)}</blockquote>` : ''}
    ${a.untested_participant_factor ? `<p>They also mentioned ${escapeHtml(uxFactorName(a, a.untested_participant_factor).toLowerCase())}. We did not test a change to that detail.</p>` : ''}
    <h4>What happened when we changed a detail</h4>
    ${a.condition_tests.length ? a.condition_tests.map(c => `<article class="trace-entry"><h4>${escapeHtml(c.factor_label)}</h4>
      <p>${escapeHtml(uxChange(c))}</p><p><strong>${escapeHtml(uxOutcome(c))}</strong></p>
      <details><summary>See this comparison and its evidence</summary><p>Only this detail changed from the earlier task; all other option facts stayed the same.</p>
      <div class="choices">${interviewOptions(c.stimulus)}</div><p>${escapeHtml(c.selection_reason)}</p><p>Evidence: ${escapeHtml(c.evidence_refs.join(', '))}</p></details></article>`).join('') : '<p>There was no earlier selection of A or B to use for these comparisons.</p>'}
    ${reflection ? `<h4>How they explained the follow-up choices</h4><blockquote>${escapeHtml(reflection)}</blockquote>` : ''}
    ${uxMuseReadingHtml(a)}
    <h4>What to do next</h4><p>${escapeHtml(readout.next)}</p>
    <p class="microcopy">These were study choices, not purchases. Check whether the finding holds with other participants and in real use.</p>
    <details><summary>Study details and other possible explanations</summary>
      <p>The order of tasks, seeing similar options again, or something missing from the options could also explain a change. This session cannot establish the cause.</p>
      <p>Behavioural science can guide further questions about practical constraints, cost and trust. No psychological cause has been established here.</p>
      <p>Interpretation source: ${escapeHtml(explanation.source)}.</p><p>Original description: ${escapeHtml(explanation.original_model_interpretation.summary)}</p><p>Participant correction: ${escapeHtml(explanation.correction.text || 'None supplied.')}</p>
      ${a.exposure_ledger.map(e => `<article class="trace-entry"><strong>${escapeHtml(uxStageNames[e.phase] || e.phase)}</strong><p>${escapeHtml(e.question)}</p><blockquote>${escapeHtml(e.response || '[Skipped]')}</blockquote><p>Record: ${escapeHtml(e.id)}. ${escapeHtml(e.reason)}</p></article>`).join('')}
      <ul>${a.limitations.map(l => `<li>${escapeHtml(l)}</li>`).join('')}</ul></details></section>`;
}

function uxMuseReadingHtml(a) {
  const reasoning = a.muse_reasoning;
  if (!reasoning || (!reasoning.plan && !reasoning.reviews?.length)) return '';
  const reviews = (reasoning.reviews || []).filter(r => r.status === 'ok');
  const plan = reasoning.plan?.status === 'accepted' ? reasoning.plan.tool_call.arguments : null;
  return `<h4>How Muse’s reading changed</h4>
    ${reasoning.initial?.factor && reasoning.initial.factor !== 'unresolved' ? `<p><strong>Initial possibility, before the participant’s check:</strong> ${escapeHtml(uxFactorName(a, reasoning.initial.factor).toLowerCase())}.</p>` : ''}
    ${plan ? `<p><strong>Before the follow-up:</strong> ${escapeHtml(plan.leading_explanation)}</p><p><strong>Another possibility:</strong> ${escapeHtml(plan.alternative_explanation)}</p><p><strong>Why this comparison came first:</strong> ${escapeHtml(plan.reason)}</p>` : ''}
    ${reviews.map(r => `<p><strong>${r.stage === 'after_first_comparison' ? 'After the first comparison' : 'After the final response'}:</strong> ${escapeHtml(r.summary)}</p><p>${escapeHtml(uxMuseUpdate(a, r))}</p><p>${escapeHtml(r.what_changed)}</p>`).join('')}
    ${(reasoning.reviews || []).filter(r => r.status !== 'ok').map(r => `<p>${r.stage === 'after_first_comparison' ? 'After the first comparison' : 'After the final response'}: ${escapeHtml(r.summary)}</p>`).join('')}
    ${reviews.length ? `<p><strong>Still unanswered:</strong> ${escapeHtml(reviews[reviews.length - 1].remaining_uncertainty)}</p>` : '<p>Muse could not provide a checked update. The recorded choices and participant explanation remain available above.</p>'}
    <p class="microcopy">These are Muse’s interpretations for researcher review, separate from the participant’s own explanation.</p>
    <details><summary>Check Muse’s evidence and recorded predictions</summary>
      ${plan ? `<p>If the choice changed: ${escapeHtml(plan.if_switch)}</p><p>If it stayed the same: ${escapeHtml(plan.if_same)}</p>` : ''}
      ${reviews.map(r => `<p>${escapeHtml(r.source)} · ${escapeHtml(r.update)}</p>${r.evidence_refs.map(ref => `<p>${escapeHtml(ref.source_id)}</p>${ref.quote ? `<blockquote>${escapeHtml(ref.quote)}</blockquote>` : ''}`).join('')}`).join('')}
    </details>`;
}

function uxMuseUpdate(a, review) {
  if (review.factor === 'unresolved') return 'Muse did not settle on one explanation.';
  if (review.factor_changed === true) return `The leading possibility changed from ${uxFactorName(a, review.previous_factor).toLowerCase()} to ${uxFactorName(a, review.factor).toLowerCase()}.`;
  if (review.factor_changed === false && review.update === 'strengthened') return 'The same explanation gained support.';
  if (review.factor_changed === false && review.update === 'weakened') return 'The same explanation lost support.';
  return review.update === 'unchanged' ? 'The reading stayed the same.' : 'The evidence still leaves more than one explanation open.';
}

function uxAggregateHtml(research) {
  if (!research?.completed_interviews) return '';
  return `<section class="brief-section"><h3>What we learned</h3><p>${research.completed_interviews} completed study sessions${research.collection_progress?.unfinished_interviews ? `; ${research.collection_progress.unfinished_interviews} interviews still unfinished` : ''}.</p>
    ${(research.condition_groups || []).map(g => `<article class="trace-entry"><h4>${escapeHtml(g.factor)}</h4><p>${escapeHtml(uxChange({...g, factor_label:g.factor}))}</p>
      <p>${g.ab_responses ? `${g.switches} of ${g.ab_responses} answered comparisons ended with a switch to the other option.` : 'No one selected A or B in this follow-up, so there is no choice change to compare.'}</p>
      <p>${g.shown} sessions received this comparison; ${g.outside} chose neither option and ${g.skipped} skipped it.</p></article>`).join('')}
    <p>These counts cover the sessions that received each exact comparison. They do not tell us how common the preference is among all users.</p>
    <h4>Read each participant’s account</h4>
    ${research.cases.map((c, i) => `<details><summary>Session ${i + 1} · ${escapeHtml(uxReadout(c.analysis).summary)}</summary>${uxAnalysisHtml(c.analysis)}</details>`).join('')}
    <details><summary>Question counts and study details</summary>
    <p>${escapeHtml(research.scope)} ${escapeHtml(research.collection_progress?.scope || '')}</p>
    <table class="ux-exposure-table"><caption>Questions sent in completed sessions</caption><thead><tr><th scope="col">Question</th><th scope="col">Sent</th><th scope="col">Answered</th></tr></thead><tbody>${research.exposures.map(e => `<tr><th scope="row">${escapeHtml(uxStageNames[e.phase] || e.phase)}</th><td>${e.shown}</td><td>${e.answered}</td></tr>`).join('')}</tbody></table></details></section>`;
}

function uxAggregateMarkdown(research) {
  const lines = ['## What we learned', '', `${research.completed_interviews} completed study sessions.`, ''];
  (research.condition_groups || []).forEach(g => lines.push(`### ${g.factor}`, '', uxChange({...g, factor_label:g.factor}), '',
    g.ab_responses ? `${g.switches} of ${g.ab_responses} sessions with an A/B answer switched to the other option.` : 'No A/B answers to compare.',
    `${g.shown} sessions received this comparison; ${g.outside} chose neither; ${g.skipped} skipped.`, ''));
  research.cases.forEach((c, i) => {
    const a = c.analysis; const readout = uxReadout(a);
    lines.push(`### Session ${i + 1}`, '', readout.summary, '', '#### What they said mattered', '', readout.priorities, '');
    lines.push('#### What they chose', '', uxChoiceDescription(a), '');
    a.evidence.filter(e => e.id === 'survey.statement' || e.id === 'interview.why').forEach(e => lines.push(`> ${e.text.replace(/\n/g, '\n> ') || '[No answer]'}`, ''));
    lines.push('#### Their checked explanation', '', a.participant_explanation.status === 'unresolved' ? 'The participant did not confirm an explanation.' : a.participant_explanation.effective, '');
    a.condition_tests.forEach(t => lines.push(`#### ${t.factor_label}`, '', uxChange(t), '', uxOutcome(t), '', `Evidence: ${t.evidence_refs.join(', ')}.`, ''));
    lines.push('#### What to do next', '', readout.next, '', 'These were study choices, not purchases. Check whether the finding holds with other participants and in real use.', '', '#### Full participant responses', '');
    if (a.muse_reasoning) {
      const plan = a.muse_reasoning.plan;
      if (plan?.status === 'accepted') lines.push('#### Muse before the follow-up', '', plan.tool_call.arguments.leading_explanation, '', 'Another possibility: ' + plan.tool_call.arguments.alternative_explanation, '', 'Why this comparison: ' + plan.tool_call.arguments.reason, '');
      (a.muse_reasoning.reviews || []).filter(r => r.status === 'ok').forEach(r => lines.push('#### Muse ' + (r.stage === 'after_first_comparison' ? 'after the first comparison' : 'after the final response'), '', r.summary, '', r.what_changed, '', 'Still unanswered: ' + r.remaining_uncertainty, '', 'Evidence: ' + r.evidence_refs.map(ref => ref.source_id).join(', '), ''));
    }
    a.evidence.forEach(e => lines.push(`${e.id}:`, `> ${e.text.replace(/\n/g, '\n> ') || '[No answer]'}`, ''));
  });
  lines.push('### Question counts and study details', '', '| Question | Sent | Answered |', '|---|---:|---:|', ...research.exposures.map(e => `| ${uxStageNames[e.phase] || e.phase} | ${e.shown} | ${e.answered} |`), '', research.scope, '', research.collection_progress?.scope || '');
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
