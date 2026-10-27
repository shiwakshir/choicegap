const $ = (selector) => document.querySelector(selector);
const state = {
  ratings: {},
  sessionId: null,
  studyId: null,
  experiment: null,
  decisionPrompt: 'Which delivery option would you choose?',
};
let labels = {
  impact: 'Environmental impact',
  price: 'Affordability',
  convenience: 'Convenience',
  trust: 'Claim credibility',
};
let descriptions = {
  impact: 'A materially lower estimated footprint',
  price: 'A lower delivery fee',
  convenience: 'A precise delivery window',
  trust: 'Independent evidence behind the claim',
};
const researcherMode = new URLSearchParams(window.location.search).get('mode') === 'researcher';
if (researcherMode) document.body.classList.add('researcher-mode');

function showError(message) {
  const error = $('#app-error');
  error.textContent = message;
  error.hidden = false;
}

function clearError() {
  const error = $('#app-error');
  error.textContent = '';
  error.hidden = true;
}

function updateEligibility() {
  const values = Object.values(state.ratings);
  const differentiated = values.length > 0 && Math.max(...values) > Math.min(...values);
  const understood = $('#comprehension').value === 'fee';
  $('#start').disabled = !(differentiated && understood);
}

$('#researcher-toggle').addEventListener('click', () => {
  window.location.href = window.location.pathname;
});

$('#restart-study').addEventListener('click', () => {
  window.location.reload();
});

$('#comprehension').addEventListener('change', () => {
  const correct = $('#comprehension').value === 'fee';
  const attempted = Boolean($('#comprehension').value);
  $('#comprehension-feedback').textContent = correct
    ? 'That’s right. You’re ready for the study choices.'
    : (attempted ? 'Take another look at the two example options.' : '');
  updateEligibility();
});

$('#export-data').addEventListener('click', async () => {
  const response = await fetch('/api/export');
  const data = await response.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'choicegap-deidentified-data.json';
  link.click();
  URL.revokeObjectURL(url);
});

function renderRatingInputs() {
  state.ratings = Object.fromEntries(Object.keys(labels).map(key => [key, 3]));
  $('#drivers').innerHTML = Object.entries(labels)
    .map(([key, label]) => `
      <div class="rating-row">
        <div>
          <strong>${escapeHtml(label)}</strong>
          <small>${escapeHtml(descriptions[key] || '')}</small>
        </div>
        <input type="range" min="1" max="5" value="3" step="1"
          data-driver="${key}" aria-label="${escapeHtml(label)} importance">
        <output>3</output>
      </div>
    `)
    .join('');
  document.querySelectorAll('.rating-row input').forEach(input => {
    input.addEventListener('input', () => {
      state.ratings[input.dataset.driver] = Number(input.value);
      input.nextElementSibling.value = input.value;
      const values = Object.values(state.ratings);
      const differentiated = Math.max(...values) > Math.min(...values);
      updateEligibility();
      $('#rating-hint').textContent = differentiated
        ? 'Thanks. Your choices may support—or challenge—this profile.'
        : 'Move at least one importance rating away from the midpoint to continue.';
    });
  });
}
renderRatingInputs();

$('#design-study').addEventListener('click', async () => {
  const button = $('#design-study');
  clearError();
  button.disabled = true;
  button.textContent = 'Compiling study…';
  $('#design-result').textContent = '';
  try {
    const data = await api('/api/design', { context: $('#design-context').value });
    state.studyId = data.study_id;
    $('#scenario-title').textContent = data.study.title;
    $('#scenario-prompt').textContent =
      'Before seeing any options, rate how important each factor is to you.';
    labels = Object.fromEntries(
      data.study.drivers.map(driver => [driver.id, driver.label]),
    );
    descriptions = Object.fromEntries(
      data.study.drivers.map(driver => [driver.id, driver.description]),
    );
    state.decisionPrompt = data.study.decision_prompt;
    renderRatingInputs();
    $('#start').disabled = true;
    const passed = Object.values(data.audit.checks).filter(Boolean).length;
    const checks = Object.keys(data.audit.checks).length;
    $('#design-result').innerHTML = `
      <strong>Controlled-design audit passed ${passed}/${checks}</strong>
      <span>${data.audit.experiment_count} experiments · complete pairwise coverage · randomized sides</span>
      <span>Exit researcher view before handing over the study.</span>
    `;
    button.textContent = 'Recompile study';
  } catch (error) {
    showError(error.message);
    button.textContent = 'Compile study with Muse';
  } finally {
    button.disabled = false;
  }
});

$('#start').addEventListener('click', async () => {
  clearError();
  $('#start').disabled = true;
  $('#start').textContent = 'Preparing choices…';
  try {
    const data = await api('/api/start', {
      ratings: state.ratings,
      intention_score: Number($('#intention-score').value),
      statement: $('#statement').value,
      study_id: state.studyId,
    });
    state.sessionId = data.session_id;
    show('study');
    renderExperiment(data.experiment, data.plan, 1);
    renderPosterior(data.posterior);
  } catch (error) {
    showError(error.message);
    $('#start').disabled = false;
    $('#start').textContent = 'Continue to choices →';
  }
});

async function api(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function show(id) {
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  $(`#${id}`).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderExperiment(experiment, plan, round) {
  state.experiment = experiment;
  $('#round').textContent = round === 'check' ? 'quality check' : round;
  $('#experiment-title').textContent = state.decisionPrompt;
  $('#experiment-rationale').textContent = experiment.rationale;
  $('#plan-reason').textContent = plan.reason;
  $('#agent-note strong').textContent = plan.source?.startsWith('muse')
    ? 'Muse experiment selection'
    : 'Local experiment selection';
  const leadingLabel = labels[plan.leading_account] || plan.leading_account;
  const rivalLabel = labels[plan.rival_account] || plan.rival_account;
  $('#hypothesis-duel').innerHTML = `
    <span>${escapeHtml(leadingLabel)}</span>
    <b>vs</b>
    <span>${escapeHtml(rivalLabel)}</span>
  `;
  $('#falsification-rule').textContent = `Pre-registered challenge: ${plan.falsification_rule}`;
  const choices = ['a', 'b'].map((key, index) => {
    const option = experiment[key];
    const optionLabel = index ? 'B' : 'A';
    const facts = option.facts.map(fact => `<li>${escapeHtml(fact)}</li>`).join('');
    return `
      <button class="choice" data-choice="${key}">
        <span class="option">Option ${optionLabel}</span>
        <h2>Option ${optionLabel}</h2>
        <ul>${facts}</ul>
        <span class="select">Choose →</span>
      </button>
    `;
  }).join('');
  const outsideChoice = `
    <button class="outside" data-choice="outside">
      Neither option — keep my usual choice
    </button>
  `;
  $('#choices').innerHTML = choices + outsideChoice;
  document.querySelectorAll('[data-choice]').forEach(button => {
    button.addEventListener('click', () => answer(button.dataset.choice));
  });
}

async function answer(choice) {
  clearError();
  document.querySelectorAll('[data-choice]').forEach(button => button.disabled = true);
  try {
    const data = await api('/api/answer', {
      session_id: state.sessionId,
      experiment_id: state.experiment.id,
      flipped: state.experiment.flipped,
      holdout: Boolean(state.experiment.holdout),
      choice,
    });
    renderPosterior(data.posterior);
    if (data.done) {
      renderReport(data.report, data.narrative);
    } else {
      const nextRound = data.holdout ? 'check' : data.rounds + 1;
      setTimeout(() => renderExperiment(data.experiment, data.plan, nextRound), 300);
    }
  } catch (error) {
    showError(error.message);
    document.querySelectorAll('[data-choice]').forEach(button => button.disabled = false);
  }
}

function renderPosterior(posterior, target = '#posterior') {
  const entropy = -Object.values(posterior).reduce(
    (sum, probability) => sum + (probability ? probability * Math.log2(probability) : 0),
    0,
  );
  $('#uncertainty-bar').style.width = `${Math.min(100, (entropy / 2) * 100)}%`;
  $(target).innerHTML = Object.entries(posterior)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => `
      <div class="posterior-row">
        <span>${escapeHtml(labels[key] || key)}</span>
        <div class="posterior-track"><i style="width:${value * 100}%"></i></div>
        <strong>${Math.round(value * 100)}%</strong>
      </div>
    `)
    .join('');
}

function renderReport(report, narrative) {
  show('report');
  if (report.evidence_quality === 'low') {
    $('#report-headline').textContent = 'The result is inconclusive.';
  } else if (report.gap_detected) {
    $('#report-headline').textContent =
      'The trade-off pattern differs from the stated priority.';
  } else {
    $('#report-headline').textContent = 'Stated and observed signals broadly align.';
  }
  $('#report-summary').textContent = narrative.summary;
  $('#next-step').textContent = narrative.next_step;
  $('#limitations').innerHTML = report.limitations
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join('');
  renderPosterior(report.posterior, '#final-posterior');
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value;
  return div.innerHTML;
}

