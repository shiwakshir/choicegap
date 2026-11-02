'use strict';
(() => {
  const SCENES = [
    {
      title: 'Scene 1 / 5 · Brief, Web Grounding & Muse Image',
      caption: 'ChoiceGap turns a UX research brief into a verifiable study. Muse Spark 1.3 runs native web_search grounding for cited sources, Muse Image 1.0 generates and edits concept stimuli, and Muse Spark drafts an editable survey, interview guide, and single-cell comparison matrix.',
      speech: 'Static surveys tell you what users click, but not why—while human UX interviews do not scale, and unguarded chatbots hallucinate findings. ChoiceGap is a brief-led adaptive survey and verifiable AI-moderated research studio built with Meta Muse. Starting from a sustainability brief, Muse Spark 1.3 runs native web search grounding for cited desk research, and Muse Image 1.0 generates our checkout concept stimulus. Muse Spark then drafts the editable survey, interview guide, and single-detail comparison table.',
      fill() {
        const brief = document.getElementById('research-brief');
        if (brief && !brief.value.trim()) document.getElementById('example-green')?.click();
        const conceptPrompt = document.getElementById('concept-instructions');
        if (conceptPrompt && !conceptPrompt.value.trim()) {
          conceptPrompt.value = 'A clean fictional mobile checkout card comparing Eco-Van Delivery (Tue 8am-12pm, $0) and Standard 1-Hour Delivery (Tue 5pm-6pm, $3.99)';
        }
        const allowRec = document.getElementById('allow-recording');
        if (allowRec) allowRec.checked = true;
        const avatarSel = document.getElementById('moderator-presentation');
        if (avatarSel) avatarSel.value = '3d';
        const approveBox = document.getElementById('approve-study');
        if (approveBox) approveBox.checked = true;
      }
    },
    {
      title: 'Scene 2 / 5 · Participant Blinding & Survey',
      caption: 'In Participant View, data disclosures are explicit and the session remains completely blind to researcher hypotheses. We start the study and answer the baseline survey question.',
      speech: 'Switching into Participant View, users see clear data disclosures while our researcher hypotheses stay completely blind. Let us start the session and answer the baseline survey question.',
      fill() {
        const consent = document.getElementById('participant-consent');
        if (consent && !consent.checked) consent.checked = true;
        const radio = document.querySelector('#answer-control input[type="radio"]:last-of-type, #answer-control input[type="checkbox"]:first-of-type');
        if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change', { bubbles: true })); }
        const openBox = document.getElementById('open-answer');
        if (openBox && !openBox.value.trim()) {
          openBox.value = 'Environmental impact matters to me, alongside practical delivery timing (fictional demo response).';
        }
      }
    },
    {
      title: 'Scene 3 / 5 · 3D AI Moderator & Muse Voice Transcribe',
      caption: 'Our local Three.js 3D AI Moderator reads the question aloud. Using the spoken audio clip (or live mic), Muse Voice Transcribe 1.0 returns an editable transcript before Muse Spark dynamically inserts a bounded follow-up probe.',
      speech: 'Here, our local Three.js 3D AI Moderator conducts the interview. Using our spoken answer audio, Muse Voice Transcribe 1.0 returns an editable transcript so the participant stays in control before submitting. Then, Muse Spark 1.3 dynamically asks a bounded follow-up probe within our approved topics.',
      fill() {
        const sampleBtn = document.getElementById('sample-voice-answer');
        const openBox = document.getElementById('open-answer');
        if (sampleBtn && !sampleBtn.closest('[hidden]') && openBox && !openBox.value.trim()) {
          sampleBtn.click();
        } else if (openBox && !openBox.value.trim()) {
          openBox.value = 'A narrower 1-hour evening slot after 5 PM would solve my weekday work schedule constraint in this fictional example.';
        }
      }
    },
    {
      title: 'Scene 4 / 5 · Muse Spark Native Tool Call & Member Check',
      caption: 'After the baseline choice, Muse Spark calls the native tool select_approved_condition to test one approved single-cell change while code holds every other cell fixed. Finally, the participant reviews and corrects Muse’s tentative summary.',
      speech: 'Next is the controlled comparison. After my baseline choice, Muse Spark invokes a native tool call—select approved condition—to pick the one approved single-cell variant that tests my scheduling barrier, while Python code verifies every other cell stayed identical. Finally, before finishing, Muse shares its tentative summary so the participant can confirm or correct it.',
      fill() {
        const phase = document.getElementById('question-phase')?.textContent || '';
        const openBox = document.getElementById('open-answer');
        if (openBox) {
          openBox.value = phase.includes('Before we finish')
            ? 'Accurate summary—please note this is fictional demonstration data, not a real purchase.'
            : 'The narrower evening delivery window removed my weekday scheduling barrier in this fictional scenario.';
        } else {
          const radios = [...document.querySelectorAll('#answer-control input[type="radio"]')];
          if (radios.length) {
            const pick = radios[0];
            pick.checked = true;
            pick.dispatchEvent(new Event('change', { bubbles: true }));
          }
        }
      }
    },
    {
      title: 'Scene 5 / 5 · Evidence-Linked Findings & Citations',
      caption: 'In Researcher Findings, Muse Spark synthesizes completed sessions under strict schema validation—citing exact non-skipped response IDs, preserving participant corrections, and reporting baseline-vs-variant switches.',
      speech: 'With one click, we return to Researcher Findings and run Muse Spark synthesis. Every finding is schema-validated: it tracks the exact single-cell comparison switch, preserves the participant correction, and links every claim directly to exact response IDs and the moderator tool-call rationale. That is ChoiceGap: verifiable, multimodal AI research built with Meta Muse.',
      fill() {
        const returnBtn = document.getElementById('return-findings');
        if (returnBtn && !returnBtn.closest('[hidden]')) {
          returnBtn.click();
          return;
        }
        document.querySelectorAll('#findings details').forEach(d => { d.open = true; });
      }
    }
  ];

  let index = 0;
  let bar = null;

  function pickVoice() {
    const voices = window.speechSynthesis?.getVoices?.() || [];
    return (
      voices.find(v => /^en[-_]/i.test(v.lang) && /aria|jenny|guy|natural|online/i.test(v.name)) ||
      voices.find(v => /^en[-_]/i.test(v.lang))
    );
  }

  function render() {
    if (!bar) return;
    const scene = SCENES[index];
    bar.querySelector('#demo-scene-title').textContent = scene.title;
    bar.querySelector('#demo-scene-caption').textContent = scene.caption;
    bar.querySelector('#demo-prev').disabled = index === 0;
    bar.querySelector('#demo-next').disabled = index === SCENES.length - 1;
  }

  function speakScene() {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(SCENES[index].speech);
    const v = pickVoice();
    if (v) { u.voice = v; u.lang = v.lang; }
    u.rate = 1.0;
    window.speechSynthesis.speak(u);
  }

  function createBar() {
    if (bar) {
      bar.hidden = !bar.hidden;
      if (bar.hidden) window.speechSynthesis?.cancel();
      return;
    }
    bar = document.createElement('aside');
    bar.id = 'demo-bar';
    bar.className = 'demo-bar';
    bar.setAttribute('aria-label', 'Demo narration and captions');
    bar.innerHTML = `
      <div class="demo-bar-top">
        <strong id="demo-scene-title"></strong>
        <div class="demo-bar-actions">
          <button id="demo-prev" class="quiet" type="button">◀ Prev</button>
          <button id="demo-speak" class="primary" type="button">🔊 Speak voiceover</button>
          <button id="demo-stop" class="quiet" type="button">⏹ Stop voice</button>
          <button id="demo-fill" class="quiet" type="button">⚡ Fill sample input</button>
          <button id="demo-next" class="quiet" type="button">Next ▶</button>
          <button id="demo-close" class="quiet" type="button" aria-label="Hide demo bar">✕</button>
        </div>
      </div>
      <p id="demo-scene-caption" class="demo-bar-caption"></p>
    `;
    document.body.append(bar);
    bar.querySelector('#demo-prev').onclick = () => { if (index > 0) { index--; render(); } };
    bar.querySelector('#demo-next').onclick = () => { if (index < SCENES.length - 1) { index++; render(); } };
    bar.querySelector('#demo-speak').onclick = speakScene;
    bar.querySelector('#demo-stop').onclick = () => window.speechSynthesis?.cancel();
    bar.querySelector('#demo-fill').onclick = () => SCENES[index].fill();
    bar.querySelector('#demo-close').onclick = () => { bar.hidden = true; window.speechSynthesis?.cancel(); };
    render();
  }

  window.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('demo-guide');
    if (btn) btn.onclick = createBar;
    if (new URLSearchParams(location.search).get('demo') === '1') createBar();
  });
})();
