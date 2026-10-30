'use strict';
const el = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const typeLabels = {open:'Open ended',single:'Single select',multi:'Multi select',ranking:'Ranking',scale:'Rating scale (1–5)',number:'Number',choice:'Hypothetical choice'};
const kindLabels = {stated_priority:'Stated priority',reported_behaviour:'Reported past behaviour',hypothetical_choice:'Hypothetical choice',context:'Context',explanation:'Explanation'};
let study = null, results = null, session = null, rank = [], inputMode = 'typed', busy = false, assetImage = '', recording = null, mediaStream = null, audioUrl = '', audioVersion = 0;
let spokenMode=false, speechEpoch=0, moderatorState='ready', turnTimer=null, levelTimer=null, levelContext=null;
const params = new URLSearchParams(location.search);
const participantId = params.get('study');

async function api(path, data) {
  const response = await fetch(`/api/studio/${path}`, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Something went wrong. Please try again.');
  return value;
}
function message(value = '') { el('notice').textContent = value; }
function error(err) { el('errors').textContent = err.message || String(err); el('errors').hidden = false; el('errors').focus(); }
async function run(label, task) {
  if (busy) return;
  busy = true; el('errors').hidden = true; message(label);
  const disabled = [...document.querySelectorAll('button')].map(b => [b,b.disabled]);
  disabled.forEach(([b]) => {if(b.id!=='pause-spoken')b.disabled = true;});
  try { await task(); message(''); } catch(err) { message(''); error(err); }
  finally { disabled.forEach(([b,v]) => { if (b.isConnected) b.disabled = v; }); busy = false; updateNav();
    if(results)el('analyse-results').disabled=!results.completed;
    el('download-results').disabled=!(results?.reports?.length);
    syncSpokenControls();
  }
}
function view(name) {
  document.querySelectorAll('.view').forEach(v => v.hidden = v.id !== name);
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('current', b.dataset.view === name));
  window.scrollTo({top:0,behavior:'instant'});
}
function updateNav() {
  document.querySelectorAll('nav button').forEach(b => {
    b.disabled = busy || (b.dataset.view === 'review' && (!study || study.status !== 'draft')) ||
      (['collect','findings'].includes(b.dataset.view) && (!study || study.status !== 'approved'));
  });
}
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => {
  if (study?.status === 'draft' && !el('review').hidden) readEditor();
  if (b.dataset.view === 'findings') run('Loading responses…', loadResults);
  else view(b.dataset.view);
}));
const examples = {
  ai: {brief:'We are exploring a new AI assistant concept for people who have tried tools such as Gemini or ChatGPT but do not use an assistant regularly. We need to decide which onboarding or product changes are worth testing. Understand their recent real examples of using or avoiding AI, what they say matters, and the trade-offs in a hypothetical choice. Recruit adults who have tried an AI assistant. Keep brand comparisons neutral and do not assume facts about any existing product.',hypotheses:'People may value accuracy but choose a familiar tool because switching takes effort. Privacy concerns, lack of a clear use case and difficulty checking answers may also matter.'},
  green: {brief:'A grocery retailer wants to understand why shoppers who care about sustainability sometimes choose conventional delivery. We need to decide whether to test price, convenient delivery slots or clearer evidence behind environmental claims. Study adults who shop for groceries online. Ask about a recent order, priorities and practical constraints, then offer a clearly hypothetical delivery choice. Do not assume shoppers are inconsistent or that one answer explains all their behaviour.',hypotheses:'Cost and delivery timing may outweigh environmental preferences in a particular situation. Some people may distrust vague green claims. Others may already make choices that fit their priorities.'}
};
for (const key of Object.keys(examples)) el(`example-${key}`).onclick = () => {
  el('research-brief').value = examples[key].brief; el('research-hypotheses').value = examples[key].hypotheses;
};
el('stimulus-file').onchange = async () => {
  const file = el('stimulus-file').files[0]; assetImage = ''; el('stimulus-preview').replaceChildren();
  if (!file) return;
  if (file.size > 1_000_000 || !['image/png','image/jpeg','image/webp'].includes(file.type)) { error(new Error('Choose a PNG, JPEG or WebP image up to 1 MB.')); el('stimulus-file').value=''; return; }
  assetImage = await new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); });
  const img = document.createElement('img'); img.src = assetImage; img.alt = 'Concept stimulus preview'; el('stimulus-preview').append(img);
};
el('brief-form').onsubmit = event => { event.preventDefault(); run('Muse is drafting your study. This may take a minute…', async () => {
  study = await api('generate',{brief:el('research-brief').value,hypotheses:el('research-hypotheses').value,stimulus:{text:el('stimulus-text').value,image:assetImage}});
  results = null; renderEditor(); view('review');
}); };
function optionsHtml(values, labels, chosen) { return values.map(v => `<option value="${esc(v)}" ${chosen===v?'selected':''}>${esc(labels[v] || v)}</option>`).join(''); }
function renderEditor() {
  const d = study.design;
  el('study-method').value=study.method||'combined';el('allow-recording').checked=study.recording===true;
  el('review-source-brief').textContent=study.brief;
  el('review-stimulus').replaceChildren();
  const description=document.createElement('p');description.textContent=study.stimulus.text||'No concept text attached.';el('review-stimulus').append(description);
  if(study.stimulus.image){const img=document.createElement('img');img.src=study.stimulus.image;img.alt=study.stimulus.text||'Attached concept';img.style.maxWidth='100%';el('review-stimulus').append(img);}
  for (const [id,key] of [['study-title','title'],['study-intro','participant_intro'],['study-objective','objective']]) el(id).value=d[key];
  el('study-hypotheses').value=d.hypotheses.join('\n'); el('study-topics').value=d.followup_topics.join('\n');
  for (const key of ['questions','interview_questions']) renderQuestions(key);
  el('approve-study').checked=false;
}
function renderQuestions(key) {
  const target = el(key === 'questions' ? 'survey-editor' : 'interview-editor');
  target.innerHTML = study.design[key].map((q,i) => `<article class="question-card" data-key="${key}" data-index="${i}">
    <div class="question-top"><strong>${key==='questions'?'Question':'Interview'} ${i+1}</strong><select aria-label="Question ${i+1} type" class="q-type">${optionsHtml(key==='questions'?Object.keys(typeLabels):['open'],typeLabels,q.type)}</select>
    <div class="card-tools"><button class="quiet" data-action="up" aria-label="Move question ${i+1} up" ${i===0?'disabled':''}>↑</button><button class="quiet" data-action="down" aria-label="Move question ${i+1} down" ${i===study.design[key].length-1?'disabled':''}>↓</button><button class="quiet" data-action="remove" ${study.design[key].length===1?'disabled':''}>Remove</button></div></div>
    <label>Question text<textarea class="q-prompt" rows="2">${esc(q.prompt)}</textarea></label>
    <label class="q-options-label" ${['open','number'].includes(q.type)?'hidden':''}>${q.type==='scale'?'Scale endpoints · one per line':'Answer options · one per line'}<textarea class="q-options" rows="3">${esc(q.options.join('\n'))}</textarea></label>
    <details><summary>Question purpose & evidence</summary><label>What this question explores<textarea class="q-purpose" rows="2">${esc(q.purpose)}</textarea></label><label>How to interpret the answer<select class="q-kind">${optionsHtml(Object.keys(kindLabels),kindLabels,q.evidence_kind)}</select></label><label class="check"><input class="q-stimulus" type="checkbox" ${q.show_stimulus?'checked':''}> Show the approved stimulus with this question</label></details></article>`).join('');
  target.querySelectorAll('.q-type').forEach(input => input.onchange = () => {
    readEditor(); const i=Number(input.closest('article').dataset.index); const q=study.design[key][i];
    if (q.type==='choice') q.evidence_kind='hypothetical_choice';
    if (!['open','number'].includes(q.type) && q.options.length<2) q.options=q.type==='scale'?['Not at all','Very much']:['Option 1','Option 2'];
    renderQuestions(key); el('approve-study').checked=false;
  });
  target.querySelectorAll('[data-action]').forEach(button => button.onclick = () => {
    readEditor(); const i=Number(button.closest('article').dataset.index), list=study.design[key];
    if (button.dataset.action==='remove') list.splice(i,1);
    else { const j=i+(button.dataset.action==='up'?-1:1); [list[i],list[j]]=[list[j],list[i]]; }
    renderQuestions(key); el('approve-study').checked=false;
  });
}
function lines(value) { return value.split('\n').map(v=>v.trim()).filter(Boolean); }
function readEditor() {
  const d=study.design;
  d.title=el('study-title').value; d.participant_intro=el('study-intro').value; d.objective=el('study-objective').value;
  d.hypotheses=lines(el('study-hypotheses').value); d.followup_topics=lines(el('study-topics').value);
  document.querySelectorAll('.question-card').forEach(card => {
    const q=d[card.dataset.key][Number(card.dataset.index)];
    q.type=card.querySelector('.q-type').value; q.prompt=card.querySelector('.q-prompt').value;
    q.options=lines(card.querySelector('.q-options').value); q.purpose=card.querySelector('.q-purpose').value;
    q.evidence_kind=card.querySelector('.q-kind').value; q.show_stimulus=card.querySelector('.q-stimulus').checked;
  });
}
for (const [id,key] of [['add-survey','questions'],['add-interview','interview_questions']]) el(id).onclick=()=>{
  readEditor(); if(study.design[key].length>=18) return error(new Error('Use up to 18 questions per guide.'));
  study.design[key].push({type:'open',prompt:'',options:[],purpose:'',evidence_kind:'explanation',show_stimulus:false}); renderQuestions(key); el('approve-study').checked=false;
};
el('review').addEventListener('input', event => { if(event.target.id!=='approve-study') el('approve-study').checked=false; });
function draftPayload(){return {id:study.id,design:study.design,method:el('study-method').value,recording:el('allow-recording').checked};}
el('save-draft').onclick=()=>run('Saving your draft…',async()=>{readEditor();study=await api('save',draftPayload());});
el('publish-study').onclick=()=>run('Publishing the approved study…',async()=>{
  readEditor(); study=await api('approve',{id:study.id,design:study.design,method:el('study-method').value,recording:el('allow-recording').checked,confirmed:el('approve-study').checked}); renderCollection(); view('collect');
});
function renderCollection(){
  el('collection-title').textContent=study.design.title;
  const url=new URL('/studio.html',location.origin);url.searchParams.set('study',study.id);
  el('participant-link').value=url.href;el('open-participant').href=url.href;
}
el('copy-link').onclick=()=>run('Copying…',async()=>{await navigator.clipboard.writeText(el('participant-link').value);el('copy-link').textContent='Link copied';});
el('go-results').onclick=el('refresh-results').onclick=()=>run('Loading responses…',loadResults);
el('analyse-results').onclick=()=>run('Muse is reading the completed sessions and their corrections…',async()=>{
  const report=await api('analyse',{id:study.id}); await loadResults(); renderReport(report);
});
async function loadResults(){
  results=await api(`results?id=${encodeURIComponent(study.id)}`);
  el('response-count').textContent=`${results.completed} completed ${results.completed===1?'session':'sessions'} · ${results.started-results.completed} unfinished`;
  el('analyse-results').disabled=!results.completed;
  el('raw-responses').innerHTML=results.sessions.map((s,i)=>`<details><summary>${esc(s.id)} · ${esc(s.status)}</summary>${s.responses.map(r=>evidenceHtml(r,`raw-${i}-${r.id}`)).join('')}<details><summary>Moderator decisions</summary>${s.decisions.map(d=>`<p>${esc(d.question||d.reason)}<br><span class="hint">${esc(d.topic||'')} · ${esc(d.reason||'')} ${d.rival_explanation?`Alternative: ${esc(d.rival_explanation)}`:''}</span></p>`).join('')}</details></details>`).join('')||'<p>No responses yet. Try the participant link first.</p>';
  el('findings-content').innerHTML='';el('download-results').disabled=true;
  if(results.reports.length) renderReport(results.reports[0]);
  view('findings');
}
function displayAnswer(r){return r.skipped?'Skipped':Array.isArray(r.answer)?r.answer.map((v,i)=>r.evidence_kind==='context'?v:`${i+1}. ${v}`).join('\n'):String(r.answer??'');}
function evidenceHtml(r,id){return `<div class="evidence-line" id="${esc(id)}"><span class="pill">${esc(r.id)}</span> <span class="hint">${esc(kindLabels[r.evidence_kind]||r.evidence_kind)}${r.phase==='correction'?' · Participant correction':''}</span><p><strong>${esc(r.question)}</strong></p><blockquote>${esc(displayAnswer(r))}</blockquote></div>`;}
function renderReport(report){
  const a=report.analysis;const byId=Object.fromEntries(report.evidence.map(r=>[r.id,r]));
  el('findings-content').innerHTML=`<div class="panel"><p class="eyebrow">Researcher review required</p><h2>What the responses suggest</h2><p>${esc(a.overview)}</p><p class="hint">Includes ${report.included} of ${report.completed_total} completed sessions at the time of analysis. ${report.incomplete} were unfinished. Generated by ${esc(report.model)}.</p></div>`+
    a.findings.map(f=>`<article class="panel finding"><h3>${esc(f.finding)}</h3>${f.behavioural_interpretation?`<p><strong>Possible explanation:</strong> ${esc(f.behavioural_interpretation)}</p>`:''}<p><strong>Another explanation:</strong> ${esc(f.alternative_explanation)}</p><p><strong>What to test:</strong> ${esc(f.recommendation)}</p><p class="hint">${esc(f.limitation)}</p><details><summary>Read the supporting responses (${f.evidence_ids.length})</summary>${f.evidence_ids.map(id=>evidenceHtml(byId[id],`evidence-${id}`)).join('')}</details></article>`).join('')+
    `<div class="panel"><h2>What to research next</h2><ul>${a.next_research.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><details><summary>Limits of these findings</summary><ul>${report.limitations.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></details></div>`;
  el('download-results').disabled=false;
  el('download-results').onclick=()=>download({study,report,responses:results.sessions},'choicegap-study-report.json');
}
function download(data,name){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
el('library').onclick=()=>run('Opening your studies…',async()=>{
  if(study?.status==='draft'&&!el('review').hidden) {readEditor();study=await api('save',draftPayload());}
  const list=await api('studies');
  el('saved-list').innerHTML=list.studies.reverse().map(s=>`<div class="panel"><h2>${esc(s.title)}</h2><p class="hint">${esc(s.status==='approved'?'Published study':'Editable draft')} · ${esc(new Date(s.created_at).toLocaleDateString())}</p><button class="quiet" data-study="${esc(s.id)}">Open study</button></div>`).join('')||'<p>Your drafts and published studies will appear here.</p>';
  el('saved-list').querySelectorAll('[data-study]').forEach(b=>b.onclick=()=>run('Opening study…',async()=>{
    study=await api(`study?id=${encodeURIComponent(b.dataset.study)}`); results=null;
    if(study.status==='draft'){renderEditor();view('review');}else{renderCollection();view('collect');}
  }));view('saved');
});
el('new-study').onclick=()=>{study=null;results=null;view('brief');updateNav();};

// Participant: one issued question at a time; responses are committed before the next is shown.
async function initParticipant(){
  el('researcher').hidden=true;el('library').hidden=true;el('participant').hidden=false;
  const info=await api(`participant?id=${encodeURIComponent(participantId)}`);
  el('participant-title').textContent=info.title;el('participant-intro').textContent=info.intro;
  el('participant-format').textContent=`${info.method==='combined'?'Survey followed by an interview':info.method==='interview'?'AI-moderated interview':'Survey'} · ${info.base_questions} planned questions, with a few possible follow-ups. All questions are optional.`;
  el('recording-notice').hidden=!info.recording;
  el('recording-notice').textContent=info.spoken_moderator?
    `Voice is optional. In spoken interview mode your device reads the questions, then your microphone listens for up to ${info.recording_seconds} seconds per answer. A quiet pause can end a recording and send it to Meta's Muse Voice for transcription. Review or correct the text before sending your answer. Pause voice mode whenever you wish. This app stores submitted text, not the audio.`:
    `Voice answers are optional. With your microphone permission, a recording of up to ${info.recording_seconds} seconds can go to Meta for transcription. You can correct the transcript before submitting. This app stores your submitted text, not the recording.`;
  el('participant-resume').hidden=!localStorage.getItem(`choicegap-studio-${participantId}`);
}
el('participant-start').onclick=()=>run('Starting your study…',async()=>{
  session=await api('start',{study_id:participantId,consent:el('participant-consent').checked});
  localStorage.setItem(`choicegap-studio-${participantId}`,session.id);renderParticipant();
});
el('participant-resume').onclick=()=>run('Resuming…',async()=>{
  if(!el('participant-consent').checked)throw new Error('Please acknowledge how your responses are used before continuing.');
  session=await api('resume',{id:localStorage.getItem(`choicegap-studio-${participantId}`)});renderParticipant();
});
function renderParticipant(){
  stopMedia();inputMode='typed';el('participant-welcome').hidden=true;
  el('participant-question').hidden=session.status==='completed';el('participant-done').hidden=session.status!=='completed';
  if(session.status==='completed'){spokenMode=false;localStorage.removeItem(`choicegap-studio-${participantId}`);return;}
  const q=session.question;el('question-prompt').textContent=q.prompt;
  el('question-phase').textContent=q.phase==='correction'?'Before we finish':q.phase==='interview'?'Interview':'Survey';
  el('question-progress').textContent=`${session.answered} answered · ${session.remaining} planned remaining`;
  const stimulus=el('question-stimulus');stimulus.replaceChildren();
  if(session.stimulus){if(session.stimulus.text){const p=document.createElement('p');p.textContent=session.stimulus.text;stimulus.append(p);}if(session.stimulus.image){const img=document.createElement('img');img.src=session.stimulus.image;img.alt=session.stimulus.text||'Study concept';stimulus.append(img);}}
  const control=el('answer-control');
  if(q.type==='open')control.innerHTML='<label for="open-answer">Your answer</label><textarea id="open-answer" rows="5" maxlength="6000" placeholder="Tell us in your own words…"></textarea>';
  if(q.type==='number')control.innerHTML='<label for="number-answer">Your answer</label><input id="number-answer" type="number" step="any">';
  if(['single','multi','choice'].includes(q.type))control.innerHTML=`<p class="hint">${q.type==='multi'?'Select all that apply.':q.type==='choice'?'Imagine this situation; no real purchase or action is made. Select one option.':'Select one.'}</p>`+q.options.map((v,i)=>`<label class="answer-option"><input type="${q.type==='multi'?'checkbox':'radio'}" name="answer" value="${i}" aria-label="${esc(v)}"><span>${esc(v)}</span></label>`).join('');
  if(q.type==='scale')control.innerHTML=`<p class="hint">1 = ${esc(q.options[0])} · 5 = ${esc(q.options[q.options.length-1])}</p>`+[1,2,3,4,5].map(v=>`<label class="answer-option"><input type="radio" name="answer" value="${v}">${v}</label>`).join('');
  if(q.type==='ranking'){rank=[...q.options];renderRank();}
  el('voice-controls').hidden=!session.recording;
  el('spoken-moderator').hidden=!(session.spoken_moderator && q.type==='open' && q.phase!=='survey');
  el('voice-status').textContent='';el('recording-playback').hidden=true;el('record-answer').textContent='Record an answer';
  el('question-prompt').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});
  setModerator('ready',spokenMode?'Preparing your next question…':'Ready when you are. You can speak or type.');
  if(spokenMode && !el('spoken-moderator').hidden)speakCurrentQuestion();
}
function renderRank(){el('answer-control').innerHTML='<p class="hint">Put the most important item first. Use the arrows to change the order, then confirm your ranking.</p>'+rank.map((v,i)=>`<div class="rank-row"><strong>${i+1}</strong><span>${esc(v)}</span><button class="quiet" data-rank="${i}" data-direction="-1" aria-label="Move ${esc(v)} up" ${i===0?'disabled':''}>↑</button><button class="quiet" data-rank="${i}" data-direction="1" aria-label="Move ${esc(v)} down" ${i===rank.length-1?'disabled':''}>↓</button></div>`).join('')+'<label class="check"><input id="confirm-ranking" type="checkbox"> This order reflects my ranking.</label>';el('answer-control').querySelectorAll('[data-rank]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.rank),j=i+Number(b.dataset.direction);[rank[i],rank[j]]=[rank[j],rank[i]];renderRank();});}
function getAnswer(){const q=session.question;
  if(q.type==='open')return el('open-answer').value;
  if(q.type==='number')return el('number-answer').value.trim()===''?null:Number(el('number-answer').value);
  if(q.type==='ranking'){if(!el('confirm-ranking').checked)throw new Error('Confirm that the order reflects your ranking, or skip the question.');return rank;}
  const checked=[...el('answer-control').querySelectorAll('input:checked')];
  if(q.type==='scale')return checked.length?Number(checked[0].value):null;
  const values=checked.map(c=>q.options[Number(c.value)]);return q.type==='multi'?values:values[0]??null;
}
function submit(skip){run('Saving your answer and preparing the next question…',async()=>{
  if(recording)throw new Error('Stop the recording and review your transcript before continuing.');
  const answer=skip?null:getAnswer();
  if(spokenMode){speechEpoch++;window.speechSynthesis?.cancel();setModerator('thinking','Muse is choosing the next question…');}
  try{const next=await api('answer',{id:session.id,nonce:session.nonce,answer,skip,input_mode:inputMode});session=next;renderParticipant();}
  catch(err){setModerator('review','Your answer has not advanced. Check the message above and try again.');throw err;}
});}
el('submit-answer').onclick=()=>submit(false);el('skip-answer').onclick=()=>submit(true);

// Audio stays in browser memory until explicitly sent for transcription. No third-party speech service.
function stopTurnMonitor(){clearTimeout(turnTimer);clearInterval(levelTimer);turnTimer=null;levelTimer=null;levelContext?.close().catch(()=>{});levelContext=null;}
function stopMedia(){audioVersion++;speechEpoch++;stopTurnMonitor();if(recording && recording.state!=='inactive'){recording.onstop=null;recording.stop();}recording=null;mediaStream?.getTracks().forEach(t=>t.stop());mediaStream=null;el('recording-playback').pause();if(audioUrl){URL.revokeObjectURL(audioUrl);audioUrl='';}window.speechSynthesis?.cancel();}
function setModerator(state,label){moderatorState=state;el('spoken-moderator').dataset.state=state;el('moderator-status').textContent=label;syncSpokenControls();}
function syncSpokenControls(){
  el('start-spoken').hidden=spokenMode;el('pause-spoken').hidden=!spokenMode;
  el('start-spoken').disabled=busy||!!recording;
  el('record-answer').disabled=busy||moderatorState==='speaking';
  el('read-question').disabled=busy||!!recording||moderatorState==='speaking';
}
function speakCurrentQuestion(){
  if(!window.speechSynthesis || !window.SpeechSynthesisUtterance){spokenMode=false;setModerator('ready','This browser cannot read questions aloud. You can record or type an answer.');return;}
  const epoch=++speechEpoch,nonce=session.nonce;
  el('recording-playback').pause();
  window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(session.question.prompt);
  const voices=window.speechSynthesis.getVoices();
  const voice=voices.find(v=>/^en[-_]/i.test(v.lang)&&/natural|online/i.test(v.name))||voices.find(v=>/^en[-_]/i.test(v.lang));
  if(voice){utterance.voice=voice;utterance.lang=voice.lang;}utterance.rate=.96;
  setModerator('speaking','Asking the question… Your microphone is off.');
  utterance.onend=()=>{if(epoch===speechEpoch&&spokenMode&&session.nonce===nonce)beginRecording(true);};
  utterance.onerror=()=>{if(epoch===speechEpoch){spokenMode=false;setModerator('ready','Voice playback stopped. Read the question, then record or type your answer.');}};
  window.speechSynthesis.speak(utterance);
}
el('start-spoken').onclick=()=>{if(busy)return;spokenMode=true;speakCurrentQuestion();};
el('pause-spoken').onclick=()=>{spokenMode=false;speechEpoch++;window.speechSynthesis?.cancel();if(recording?.state==='recording')recording.stop();else{audioVersion++;mediaStream?.getTracks().forEach(t=>t.stop());mediaStream=null;}stopTurnMonitor();setModerator('ready','Voice mode paused. You can review, record or type your answer.');};
async function wavBase64(blob){
  const context=new AudioContext();let decoded;
  try{decoded=await context.decodeAudioData(await blob.arrayBuffer());}finally{await context.close();}
  const offline=new OfflineAudioContext(1,Math.min(Math.ceil(decoded.duration*16000),(session.recording_seconds||30)*16000),16000);
  const source=offline.createBufferSource();source.buffer=decoded;source.connect(offline.destination);source.start();
  const buffer=await offline.startRendering(), samples=buffer.getChannelData(0), raw=new ArrayBuffer(44+samples.length*2), view=new DataView(raw);
  function str(offset,s){for(let i=0;i<s.length;i++)view.setUint8(offset+i,s.charCodeAt(i));}
  str(0,'RIFF');view.setUint32(4,36+samples.length*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++)view.setInt16(44+i*2,Math.max(-1,Math.min(1,samples[i]))*(samples[i]<0?32768:32767),true);
  return await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(new Blob([raw],{type:'audio/wav'}));});
}
async function transcribeRecording(blob,version){
  return run('Muse is transcribing. You can correct the text before sending your answer…',async()=>{
    setModerator('transcribing','Turning your answer into text… Your microphone is off.');
    try{
      const audio=await wavBase64(blob);const response=await api('transcribe',{id:session.id,nonce:session.nonce,audio});
      if(version!==audioVersion)return;
      el('open-answer').value=response.transcript;inputMode='confirmed_transcript';
      el('voice-status').textContent='Check and correct the transcript above, then send your answer. Your microphone is off.';
      setModerator('review','Does this capture your answer? Edit the text, send it, or record again.');el('open-answer').focus({preventScroll:true});
    }catch(err){setModerator('review','Transcription did not complete. Your answer has not been submitted. Try again or type instead.');throw err;}
  });
}
async function beginRecording(automatic=false){
  if(busy)return;
  if(recording){recording.stop();return;}
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder){spokenMode=false;setModerator('ready','This browser cannot record audio. You can type your answer.');return error(new Error('This browser cannot record audio. You can type your answer.'));}
  const version=++audioVersion,nonce=session.nonce;
  try{
    window.speechSynthesis?.cancel();setModerator('listening','Waiting for microphone permission…');
    const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
    if(version!==audioVersion||session.nonce!==nonce||busy||(automatic&&!spokenMode)){stream.getTracks().forEach(t=>t.stop());return;}
    mediaStream=stream;
    el('recording-playback').pause();
    if(audioUrl){URL.revokeObjectURL(audioUrl);audioUrl='';}el('recording-playback').hidden=true;
    const chunks=[],recorder=new MediaRecorder(mediaStream);recording=recorder;recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onstop=async()=>{
      const mime=recorder.mimeType;recording=null;stopTurnMonitor();stream.getTracks().forEach(t=>t.stop());mediaStream=null;
      el('record-answer').textContent='Record again';
      if(version!==audioVersion)return;
      const blob=new Blob(chunks,{type:mime});audioUrl=URL.createObjectURL(blob);el('recording-playback').src=audioUrl;el('recording-playback').hidden=false;
      setModerator('review','Recording stopped. Review it or transcribe it when ready.');
      const control=el('voice-status');control.replaceChildren(document.createTextNode('Listen to your recording, then send it to Muse to transcribe. '));
      const send=document.createElement('button');send.className='quiet';send.textContent='Transcribe this recording';control.append(send);
      send.onclick=()=>transcribeRecording(blob,version);
      if(automatic&&spokenMode)await transcribeRecording(blob,version);
    };
    recorder.onerror=()=>{stopMedia();spokenMode=false;setModerator('ready','Recording failed. Please type your answer or try recording again.');};
    recorder.start();el('record-answer').textContent='Stop recording';
    const seconds=session.recording_seconds||30;
    el('voice-status').textContent=`Recording… up to ${seconds} seconds. ${automatic?'A quiet pause can stop the recording early. You can also press Stop recording.':''}`;
    setModerator('listening','Listening to your answer…');
    turnTimer=setTimeout(()=>{if(version===audioVersion&&recorder.state==='recording')recorder.stop();},seconds*1000);
    if(automatic){
      try{
        const context=new AudioContext();levelContext=context;await context.resume();
        if(version!==audioVersion||recorder.state!=='recording'){await context.close();return;}
        const input=context.createMediaStreamSource(stream),analyser=context.createAnalyser();analyser.fftSize=2048;input.connect(analyser);
        const samples=new Float32Array(analyser.fftSize),gate=new SpokenTurn({maxMs:seconds*1000});
        levelTimer=setInterval(()=>{if(version!==audioVersion||recorder.state!=='recording')return;analyser.getFloatTimeDomainData(samples);const rms=Math.sqrt(samples.reduce((sum,v)=>sum+v*v,0)/samples.length);if(gate.observe(rms,performance.now()))recorder.stop();},100);
      }catch{el('voice-status').textContent=`Recording… press Stop recording when finished. Maximum ${seconds} seconds.`;}
    }
  }catch(err){stopMedia();spokenMode=false;setModerator('ready','Microphone unavailable. You can type your answer.');error(new Error('Microphone unavailable. Check browser permission, or type your answer.'));}
}
el('record-answer').onclick=()=>beginRecording(spokenMode);
el('read-question').onclick=()=>{if(!window.speechSynthesis)return error(new Error('Read aloud is unavailable in this browser.'));window.speechSynthesis.cancel();window.speechSynthesis.speak(new SpeechSynthesisUtterance(session.question.prompt));el('voice-status').textContent='Reading with your device’s voice. Muse chooses the question; this is not an avatar.';};
window.addEventListener('pagehide',()=>{spokenMode=false;stopMedia();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&spokenMode)el('pause-spoken').click();});
if(participantId)run('Opening your study…',initParticipant);
else {updateNav();fetch('/api/health').then(r=>r.json()).then(h=>{if(!h.meta_enabled)message('Muse is not connected. Configure your local API key and restart the app before generating a study.');}).catch(()=>message('Could not reach the local server.'));}
