const $ = (selector) => document.querySelector(selector);
const state = { driver: null, sessionId: null, studyId: null, experiment: null, posterior: null };
let labels = { trust: 'Trust & proof', control: 'User control', price: 'Price sensitivity', risk: 'Risk avoidance' };

$('#researcher-toggle').addEventListener('click', () => {
  const enabled = document.body.classList.toggle('researcher-mode');
  $('#researcher-toggle').textContent = enabled ? 'Participant view' : 'Researcher view';
});

$('#open-debrief').addEventListener('click', () => {
  document.body.classList.add('researcher-mode');
  $('#researcher-toggle').textContent = 'Participant view';
  window.scrollTo({top: 0, behavior: 'smooth'});
});

fetch('/api/health').catch(() => {});

function bindDrivers() {
  document.querySelectorAll('.driver').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.driver').forEach(item => item.classList.remove('selected'));
    button.classList.add('selected');
    state.driver = button.dataset.driver;
    $('#start').disabled = false;
  }));
}
bindDrivers();

$('#design-study').addEventListener('click', async () => {
  const button = $('#design-study');
  button.disabled = true;
  button.innerHTML = 'Muse is forming rival explanations… <span>✦</span>';
  $('#design-result').textContent = '';
  try {
    const data = await api('/api/design', { context: $('#design-context').value });
    state.studyId = data.study_id; state.driver = null;
    $('#scenario-title').textContent = data.study.title;
    $('#scenario-prompt').textContent = data.study.decision_prompt;
    labels = Object.fromEntries(data.study.drivers.map(driver => [driver.id, driver.label]));
    $('#drivers').innerHTML = data.study.drivers.map((driver, index) => `<button class="driver" data-driver="${driver.id}"><span>0${index + 1}</span><strong>${escapeHtml(driver.label)}</strong><small>${escapeHtml(driver.description)}</small></button>`).join('');
    bindDrivers();
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
    const data = await api('/api/start', { driver: state.driver, statement: $('#statement').value, study_id: state.studyId });
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
  $('#round').textContent = round;
  $('#experiment-title').textContent = experiment.title;
  $('#experiment-rationale').textContent = experiment.rationale;
  $('#plan-reason').textContent = plan.reason;
  $('#agent-note strong').textContent = plan.source?.startsWith('muse') ? 'Muse falsification loop' : 'Local falsification loop';
  $('#hypothesis-duel').innerHTML = `<span>${labels[plan.leading_account] || plan.leading_account}</span><b>vs</b><span>${labels[plan.rival_account] || plan.rival_account}</span>`;
  $('#falsification-rule').textContent = `Pre-registered challenge: ${plan.falsification_rule}`;
  $('#choices').innerHTML = ['a','b'].map((key, index) => {
    const option = experiment[key];
    return `<button class="choice" data-choice="${key}"><span class="option">Option ${index ? 'B' : 'A'}</span><h2>${escapeHtml(option.name)}</h2><ul>${option.facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul><span class="select">Choose →</span></button>`;
  }).join('');
  document.querySelectorAll('.choice').forEach(button => button.addEventListener('click', () => answer(button.dataset.choice)));
}

async function answer(choice) {
  document.querySelectorAll('.choice').forEach(button => button.disabled = true);
  try {
    const data = await api('/api/answer', { session_id: state.sessionId, experiment_id: state.experiment.id, flipped: state.experiment.flipped, choice });
    state.posterior = data.posterior; renderPosterior(data.posterior);
    if (data.done) renderReport(data.report, data.narrative);
    else setTimeout(() => renderExperiment(data.experiment, data.plan, data.rounds + 1), 300);
  } catch (error) { alert(error.message); document.querySelectorAll('.choice').forEach(button => button.disabled = false); }
}

function renderPosterior(posterior, target = '#posterior') {
  const entropy = -Object.values(posterior).reduce((sum,p) => sum + (p ? p*Math.log2(p) : 0), 0);
  if ($('#uncertainty-bar')) $('#uncertainty-bar').style.width = `${Math.min(100, entropy/2*100)}%`;
  $(target).innerHTML = Object.entries(posterior).sort((a,b) => b[1]-a[1]).map(([key,value]) => `<div class="posterior-row"><span>${labels[key]}</span><div class="posterior-track"><i style="width:${value*100}%"></i></div><strong>${Math.round(value*100)}%</strong></div>`).join('');
}

function renderReport(report, narrative) {
  show('report');
  $('#report-headline').textContent = report.gap_detected ? 'There’s a meaningful gap.' : 'Stated and observed signals broadly align.';
  $('#report-summary').textContent = narrative.summary;
  $('#next-step').textContent = narrative.next_step;
  $('#limitations').innerHTML = report.limitations.map(item => `<li>${escapeHtml(item)}</li>`).join('');
  renderPosterior(report.posterior, '#final-posterior');
}

function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value; return div.innerHTML; }

