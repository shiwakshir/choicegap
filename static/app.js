const $ = (selector) => document.querySelector(selector);
const state = {
  ratings: {},
  sessionId: null,
  studyId: null,
  experiment: null,
  answerToken: null,
  studyReady: !new URLSearchParams(window.location.search).has('study'),
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
  error.focus({ preventScroll: true });
  error.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

function clearError() {
  const error = $('#app-error');
  error.textContent = '';
  error.hidden = true;
}

function updateEligibility() {
  const understood = $('#comprehension').value === 'fee';
  $('#start').disabled = !(state.studyReady && $('#ratings-reviewed').checked && understood);
}

$('#ratings-reviewed').addEventListener('change', updateEligibility);

$('#researcher-toggle').addEventListener('click', () => {
  const url = new URL(window.location.href);
  url.searchParams.delete('mode');
  url.searchParams.delete('workspace');
  if (state.studyId) url.searchParams.set('study', state.studyId);
  window.location.href = url.href;
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
  try {
  const response = await fetch('/api/export');
  if (!response.ok) throw new Error('Could not export session data.');
  const data = await response.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'choicegap-deidentified-data.json';
  link.click();
  URL.revokeObjectURL(url);
  } catch (error) {
    showError(error.message);
  }
});

$('#refresh-results').addEventListener('click', async () => {
  clearError();
  try {
    const response = await fetch('/api/export');
    if (!response.ok) throw new Error('Could not load completed sessions.');
    const data = await response.json();
    const records = data.records.filter(record => !state.studyId || record.study_id === state.studyId);
    $('#completed-results').replaceChildren();
    if (!records.length) $('#completed-results').textContent = 'No completed sessions yet.';
    records.forEach((record, index) => {
      const button = document.createElement('button');
      button.className = 'secondary';
      button.textContent = `Session ${index + 1} · ${record.study_title} · ${record.evidence_quality} response quality`;
      button.addEventListener('click', () => {
        labels = Object.fromEntries(Object.entries(record.driver_labels).map(([id, copy]) => [id, copy.label]));
        renderReport(record.report, record.narrative);
      });
      $('#completed-results').append(button);
    });
  } catch (error) {
    showError(error.message);
  }
});

function applyStudy(data) {
  document.body.classList.add('configured-study');
  state.studyReady = true;
  state.studyId = data.study_id;
  state.decisionPrompt = data.study.decision_prompt;
  $('#scenario-title').textContent = data.study.title;
  $('#scenario-prompt').textContent = 'Consider the options in this study. Rate each factor before continuing.';
  $('#intention-label').textContent = '“When a lower-impact option is available in this context, I try to choose it.”';
  $('#statement').placeholder = 'What matters to you in this decision, and why?';
  labels = Object.fromEntries(data.study.drivers.map(driver => [driver.id, driver.label]));
  descriptions = Object.fromEntries(data.study.drivers.map(driver => [driver.id, driver.description]));
  renderRatingInputs();
  $('#ratings-reviewed').checked = false;
  updateEligibility();
}

async function loadLinkedStudy() {
  const studyId = new URLSearchParams(window.location.search).get('study');
  if (!studyId) return;
  $('#start').disabled = true;
  try {
    const response = await fetch(`/api/study?id=${encodeURIComponent(studyId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    applyStudy(data);
  } catch (error) {
    showError(error.message);
    $('#start').disabled = true;
    $('#ratings-reviewed').disabled = true;
  }
}

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
      updateEligibility();
    });
  });
}
renderRatingInputs();
loadLinkedStudy();

$('#design-study').addEventListener('click', async () => {
  const button = $('#design-study');
  clearError();
  button.disabled = true;
  button.textContent = 'Compiling study…';
  $('#design-result').textContent = '';
  try {
    const data = await api('/api/design', { context: $('#design-context').value });
    applyStudy(data);
    const researcherUrl = new URL(window.location.href);
    researcherUrl.searchParams.set('study', state.studyId);
    window.history.replaceState({}, '', researcherUrl);
    const participantUrl = new URL(window.location.href);
    participantUrl.searchParams.delete('mode');
    const passed = Object.values(data.audit.checks).filter(Boolean).length;
    const checks = Object.keys(data.audit.checks).length;
    $('#design-result').innerHTML = `
      <strong>Controlled-design audit passed ${passed}/${checks}</strong>
      <span>${data.audit.experiment_count} experiments · complete pairwise coverage · randomized sides</span>
      <a href="${escapeHtml(participantUrl.href)}" target="_blank" rel="noopener">Open participant study in a separate tab →</a>
      <span>Review the factor levels and realism before recruiting participants.</span>
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
    state.answerToken = data.answer_token;
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
  $('#progress-label').textContent = round === 'check' ? 'Final choice' : `Choice ${round} of 4`;
  $('#experiment-title').textContent = state.decisionPrompt;
  $('#experiment-rationale').textContent = experiment.rationale;
  $('#plan-reason').textContent = plan.reason;
  $('#agent-note strong').textContent = 'Computed experiment selection';
  const leadingLabel = labels[plan.leading_account] || plan.leading_account;
  const rivalLabel = labels[plan.rival_account] || plan.rival_account;
  $('#hypothesis-duel').innerHTML = `
    <span>${escapeHtml(leadingLabel)}</span>
    <b>vs</b>
    <span>${escapeHtml(rivalLabel)}</span>
  `;
  $('#falsification-rule').textContent = `Recorded challenge: ${plan.falsification_rule}`;
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
      answer_token: state.answerToken,
      choice,
    });
    renderPosterior(data.posterior);
    state.answerToken = data.answer_token;
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
  } else {
    $('#report-headline').textContent = report.headline;
  }
  $('#report-summary').textContent = narrative.summary;
  const stated = (report.stated_priorities || [report.stated_driver])
    .map(id => labels[id] || id).join(', ');
  const consistency = report.holdout_consistent === true
    ? 'consistent' : (report.holdout_consistent === false ? 'inconsistent' : 'unavailable');
  $('#report-context').textContent =
    `Highest stated priorities: ${stated}. ` +
    `${report.informative_choices}/4 informative choices. Repeated choice: ${consistency}. ` +
    'Percentages below are probabilities within the candidate model set.';
  $('#next-step').textContent = narrative.next_step;
  $('#limitations').innerHTML = report.limitations
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join('');
  renderPosterior(report.posterior, '#final-posterior');
  $('#decision-trace').innerHTML = (report.decision_trace || []).map(entry => {
    const plan = entry.plan_before_response;
    const predictions = Object.entries(entry.p_canonical_a_by_hypothesis)
      .map(([id, value]) => `${labels[id] || id}: ${Math.round(value * 100)}%`).join(' · ');
    return `
      <details class="trace-entry">
        <summary>${entry.holdout ? 'Consistency repeat' : `Choice ${entry.step}`}
          · ${escapeHtml(plan.source)} · ${entry.uncertainty_before_bits} → ${entry.uncertainty_after_bits} bits</summary>
        <p><strong>Plan before response:</strong> ${escapeHtml(plan.reason)}</p>
        <p><strong>Challenge:</strong> ${escapeHtml(plan.falsification_rule)}</p>
        <p><strong>Computed P(canonical A):</strong> ${escapeHtml(predictions || 'Held out of model updates')}</p>
        <div class="trace-options">
          <div><strong>Displayed A</strong><ul>${entry.stimulus.a.facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul></div>
          <div><strong>Displayed B</strong><ul>${entry.stimulus.b.facts.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul></div>
        </div>
        <p>Response: ${escapeHtml(entry.displayed_choice)} · Reversed sides: ${entry.stimulus.flipped ? 'yes' : 'no'}</p>
        <p class="trace-hash">Stimulus SHA-256: ${escapeHtml(entry.stimulus_sha256)}</p>
      </details>
    `;
  }).join('');
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value;
  return div.innerHTML;
}

