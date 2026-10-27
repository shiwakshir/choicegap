const $ = (selector) => document.querySelector(selector);
const state = { driver: null, ratings: {}, sessionId: null, studyId: null, experiment: null, posterior: null, decisionPrompt: 'Which delivery option would you choose?' };
let labels = { impact: 'Environmental impact', price: 'Affordability', convenience: 'Convenience', trust: 'Claim credibility' };
let descriptions = { impact: 'A materially lower estimated footprint', price: 'A lower delivery fee', convenience: 'A precise delivery window', trust: 'Independent evidence behind the claim' };

function updateEligibility() {
  const values = Object.values(state.ratings);
  const differentiated = values.length > 0 && Math.max(...values) > Math.min(...values);
  const understood = $('#comprehension').value === 'held';
  $('#start').disabled = !(differentiated && understood);
}

$('#researcher-toggle').addEventListener('click', () => {
  const enabled = document.body.classList.toggle('researcher-mode');
  $('#researcher-toggle').textContent = enabled ? 'Participant view' : 'Researcher view';
});

$('#open-debrief').addEventListener('click', () => {
  document.body.classList.add('researcher-mode');
  $('#researcher-toggle').textContent = 'Participant view';
  window.scrollTo({top: 0, behavior: 'smooth'});
});

$('#comprehension').addEventListener('change', () => {
  const correct = $('#comprehension').value === 'held';
  $('#comprehension-feedback').textContent = correct ? 'Correct—the unchanged detail is controlled in that comparison.' : ($('#comprehension').value ? 'Not quite. Look for what changes and what stays the same.' : '');
  updateEligibility();
});

$('#export-data').addEventListener('click', async () => {
  const response = await fetch('/api/export');
  const data = await response.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = 'choicegap-deidentified-data.json'; link.click();
  URL.revokeObjectURL(url);
});

fetch('/api/health').catch(() => {});

function renderRatingInputs() {
  state.ratings = Object.fromEntries(Object.keys(labels).map(key => [key, 3]));
  $('#drivers').innerHTML = Object.entries(labels).map(([key, label]) => `<div class="rating-row"><div><strong>${escapeHtml(label)}</strong><small>${escapeHtml(descriptions[key] || '')}</small></div><input type="range" min="1" max="5" value="3" step="1" data-driver="${key}" aria-label="${escapeHtml(label)} importance"><output>3</output></div>`).join('');
  document.querySelectorAll('.rating-row input').forEach(input => input.addEventListener('input', () => {
    state.ratings[input.dataset.driver] = Number(input.value);
    input.nextElementSibling.value = input.value;
    const values = Object.values(state.ratings);
    const differentiated = Math.max(...values) > Math.min(...values);
    state.driver = Object.keys(state.ratings).reduce((best, key) => state.ratings[key] > state.ratings[best] ? key : best);
    updateEligibility();
    $('#rating-hint').textContent = differentiated ? 'Thanks. Your choices may support—or challenge—this profile.' : 'Move at least one importance rating away from the midpoint to continue.';
  }));
}
renderRatingInputs();

$('#design-study').addEventListener('click', async () => {
  const button = $('#design-study');
  button.disabled = true;
  button.innerHTML = 'Muse is forming rival explanations… <span>✦</span>';
  $('#design-result').textContent = '';
  try {
    const data = await api('/api/design', { context: $('#design-context').value });
    state.studyId = data.study_id; state.driver = null;
    $('#scenario-title').textContent = data.study.title;
    $('#scenario-prompt').textContent = 'Before seeing any options, rate how important each factor is to you.';
    labels = Object.fromEntries(data.study.drivers.map(driver => [driver.id, driver.label]));
    descriptions = Object.fromEntries(data.study.drivers.map(driver => [driver.id, driver.description]));
    state.decisionPrompt = data.study.decision_prompt;
    renderRatingInputs();
    $('#start').disabled = true;
    const passed = Object.values(data.audit.checks).filter(Boolean).length;
    $('#design-result').innerHTML = `<strong>Controlled-design audit passed ${passed}/${Object.keys(data.audit.checks).length}</strong><span>${data.audit.experiment_count} experiments · complete pairwise coverage · randomized sides</span><span>Switch to Participant view before handing over the study.</span>`;
    button.innerHTML = 'Recompile study <span>✦</span>';
  } catch (error) {
    $('#design-result').textContent = error.message;
    button.innerHTML = 'Compile study with Muse <span>✦</span>';
  } finally { button.disabled = false; }
});

$('#start').addEventListener('click', async () => {
  $('#start').disabled = true;
  $('#start').innerHTML = 'Forming hypotheses… <span>✦</span>';
  try {
    const data = await api('/api/start', { driver: state.driver, ratings: state.ratings, intention_score: Number($('#intention-score').value), statement: $('#statement').value, study_id: state.studyId });
    state.sessionId = data.session_id; state.posterior = data.posterior;
    show('study'); renderExperiment(data.experiment, data.plan, 1); renderPosterior(data.posterior);
  } catch (error) { alert(error.message); $('#start').disabled = false; $('#start').textContent = 'Begin adaptive study →'; }
});

async function api(url, body) {
  const response = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function show(id) {
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  $(`#${id}`).classList.add('active'); window.scrollTo({top: 0, behavior: 'smooth'});
}

function renderExperiment(experiment, plan, round) {
  state.experiment = experiment;
  $('#round').textContent = round === 'check' ? 'quality check' : round;
  $('#experiment-title').textContent = state.decisionPrompt;
  $('#experiment-rationale').textContent = experiment.rationale;
  $('#plan-reason').textContent = plan.reason;
  $('#agent-note strong').textContent = plan.source?.startsWith('muse') ? 'Muse falsification loop' : 'Local falsification loop';
  $('#hypothesis-duel').innerHTML = `<span>${labels[plan.leading_account] || plan.leading_account}</span><b>vs</b><span>${labels[plan.rival_account] || plan.rival_account}</span>`;
  $('#falsification-rule').textContent = `Pre-registered challenge: ${plan.falsification_rule}`;
  $('#choices').innerHTML = ['a','b'].map((key, index) => {
    const option = experiment[key];
    return `<button class="choice" data-choice="${key}"><span class="option">Option ${index ? 'B' : 'A'}</span><h2>Option ${index ? 'B' : 'A'}</h2><ul>${option.facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul><span class="select">Choose →</span></button>`;
  }).join('') + `<button class="outside" data-choice="outside">Neither option — keep my usual choice</button>`;
  document.querySelectorAll('[data-choice]').forEach(button => button.addEventListener('click', () => answer(button.dataset.choice)));
}

async function answer(choice) {
  document.querySelectorAll('[data-choice]').forEach(button => button.disabled = true);
  try {
    const data = await api('/api/answer', { session_id: state.sessionId, experiment_id: state.experiment.id, flipped: state.experiment.flipped, holdout: Boolean(state.experiment.holdout), choice });
    state.posterior = data.posterior; renderPosterior(data.posterior);
    if (data.done) renderReport(data.report, data.narrative);
    else setTimeout(() => renderExperiment(data.experiment, data.plan, data.holdout ? 'check' : data.rounds + 1), 300);
  } catch (error) { alert(error.message); document.querySelectorAll('[data-choice]').forEach(button => button.disabled = false); }
}

function renderPosterior(posterior, target = '#posterior') {
  const entropy = -Object.values(posterior).reduce((sum,p) => sum + (p ? p*Math.log2(p) : 0), 0);
  if ($('#uncertainty-bar')) $('#uncertainty-bar').style.width = `${Math.min(100, entropy/2*100)}%`;
  $(target).innerHTML = Object.entries(posterior).sort((a,b) => b[1]-a[1]).map(([key,value]) => `<div class="posterior-row"><span>${labels[key]}</span><div class="posterior-track"><i style="width:${value*100}%"></i></div><strong>${Math.round(value*100)}%</strong></div>`).join('');
}

function renderReport(report, narrative) {
  show('report');
  $('#report-headline').textContent = report.gap_detected ? 'The trade-off pattern differs from the stated priority.' : 'Stated and observed signals broadly align.';
  $('#report-summary').textContent = narrative.summary;
  $('#next-step').textContent = narrative.next_step;
  $('#limitations').innerHTML = report.limitations.map(item => `<li>${escapeHtml(item)}</li>`).join('');
  renderPosterior(report.posterior, '#final-posterior');
}

function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value; return div.innerHTML; }

