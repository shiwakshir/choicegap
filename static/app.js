const $ = (selector) => document.querySelector(selector);
const state = { driver: null, sessionId: null, experiment: null, posterior: null };
const labels = { trust: 'Trust & proof', control: 'User control', price: 'Price sensitivity', risk: 'Risk avoidance' };

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

document.querySelectorAll('.driver').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.driver').forEach(item => item.classList.remove('selected'));
  button.classList.add('selected');
  state.driver = button.dataset.driver;
  $('#start').disabled = false;
}));

$('#start').addEventListener('click', async () => {
  $('#start').disabled = true;
  $('#start').innerHTML = 'Forming hypotheses… <span>✦</span>';
  try {
    const data = await api('/api/start', { driver: state.driver, statement: $('#statement').value });
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
  $('#agent-note strong').textContent = plan.source?.startsWith('muse') ? 'Muse selected this test' : 'Evidence engine selected this test';
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

