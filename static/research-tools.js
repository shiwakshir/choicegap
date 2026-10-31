/* Researcher-only inputs. No generated draft is promoted without explicit selection/review. */
(function(){
  'use strict';
  let background=null,backgroundBrief='',conceptId=null,comparisons=null;
  function renderBackground(value){
    const unique=[...new Map(value.citations.map(c=>[c.url,c])).values()];
    el('background-result').innerHTML=`<p class="pill">Desk research · not participant evidence</p><p class="source-summary">${esc(value.summary)}</p><ol>${unique.map(c=>`<li><a href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">${esc(c.title)}</a></li>`).join('')}</ol>`;
    el('background-review-label').hidden=false;el('background-reviewed').checked=false;
  }
  el('research-brief').addEventListener('input',()=>{el('background-reviewed').checked=false;});
  el('search-background').onclick=()=>run('Muse is searching and preparing a cited background…',async()=>{
    const brief=el('research-brief').value;background=await api('background',{brief});backgroundBrief=brief.trim();renderBackground(background);
  });
  async function makeConcept(edit){
    if(edit&&!assetImage)throw new Error('Attach or select an image before asking Muse to edit it.');
    const candidate=await api('concept',{prompt:el('concept-instructions').value,reference:edit?assetImage:''});
    el('concept-result').innerHTML=`<div class="panel"><img class="concept-candidate" src="${esc(candidate.image)}" alt="Generated research concept draft"><p>${esc(candidate.warning)}</p><button id="use-generated-concept" class="quiet" type="button">Use this reviewed concept</button></div>`;
    el('use-generated-concept').onclick=()=>{assetImage=candidate.image;conceptId=candidate.id;
      el('stimulus-preview').innerHTML=`<p class="pill">Selected Muse Image draft</p><img src="${esc(assetImage)}" alt="Selected concept stimulus">`;el('concept-result').innerHTML='';};
  }
  el('generate-concept').onclick=()=>run('Muse Image is preparing a concept draft…',()=>makeConcept(false));
  el('edit-concept').onclick=()=>run('Muse Image is editing a new draft of the attached concept…',()=>makeConcept(true));
  function renderComparisons(){
    if(!comparisons){el('comparison-editor').innerHTML='';return;}
    const p=comparisons;
    el('comparison-editor').innerHTML=`<label>Scenario<textarea class="c-context" rows="2">${esc(p.context)}</textarea></label><label>Choice question<textarea class="c-prompt" rows="2">${esc(p.prompt)}</textarea></label><div class="two-columns"><label>First option title<input class="c-a-title" value="${esc(p.a_title)}"></label><label>Second option title<input class="c-b-title" value="${esc(p.b_title)}"></label></div><div class="table-scroll"><table><thead><tr><th>Detail held in the design</th><th>First option</th><th>Second option</th></tr></thead><tbody>${p.factors.map((f,i)=>`<tr data-factor="${i}"><td><input aria-label="Detail ${i+1} name" class="c-name" value="${esc(f.name)}"></td><td><input aria-label="Detail ${i+1}, first option" class="c-a" value="${esc(f.a)}"></td><td><input aria-label="Detail ${i+1}, second option" class="c-b" value="${esc(f.b)}"></td></tr>`).join('')}</tbody></table></div><h3>Approved alternatives Muse may select</h3>${p.changes.map((c,i)=>`<div class="panel" data-change="${i}"><label>Change this detail<select class="c-factor">${p.factors.map((f,j)=>`<option value="${j}" ${j===c.factor?'selected':''}>${esc(f.name)}</option>`).join('')}</select></label><label>In this option<select class="c-target"><option value="a" ${c.target==='a'?'selected':''}>First option</option><option value="b" ${c.target==='b'?'selected':''}>Second option</option></select></label><label>New value<input class="c-value" value="${esc(c.value)}"></label><label>Candidate explanation<textarea class="c-explanation" rows="2">${esc(c.explanation)}</textarea></label><label>Alternative explanation<textarea class="c-rival" rows="2">${esc(c.rival)}</textarea></label></div>`).join('')}<p class="hint">A baseline and one selected alternative are shown. Only the selected cell changes; all other values stay fixed. Presentation order and repeated choice can still influence answers.</p>`;
  }
  function readComparisons(){
    if(!comparisons||!el('use-comparisons').checked)return null;
    const root=el('comparison-editor'),p={...comparisons};
    p.context=root.querySelector('.c-context').value;p.prompt=root.querySelector('.c-prompt').value;
    p.a_title=root.querySelector('.c-a-title').value;p.b_title=root.querySelector('.c-b-title').value;
    p.factors=[...root.querySelectorAll('[data-factor]')].map(row=>({name:row.querySelector('.c-name').value,a:row.querySelector('.c-a').value,b:row.querySelector('.c-b').value}));
    p.changes=[...root.querySelectorAll('[data-change]')].map(row=>({factor:Number(row.querySelector('.c-factor').value),target:row.querySelector('.c-target').value,value:row.querySelector('.c-value').value,explanation:row.querySelector('.c-explanation').value,rival:row.querySelector('.c-rival').value}));
    comparisons=p;return p;
  }
  el('draft-comparisons').onclick=()=>run('Muse is drafting hypothetical comparisons for your review…',async()=>{
    readEditor();comparisons=await api('comparisons',{design:study.design});el('use-comparisons').checked=false;renderComparisons();el('approve-study').checked=false;
  });
  el('allow-recording').addEventListener('change',()=>{if(!el('allow-recording').checked)el('moderator-presentation').value='none';});
  window.researchTools={
    clearConcept(){conceptId=null;},
    briefOptions(){if(el('research-brief').value.trim()!==backgroundBrief)el('background-reviewed').checked=false;return {background_id:el('background-reviewed').checked?background?.id:null,background_reviewed:el('background-reviewed').checked,concept_id:conceptId};},
    render(value){comparisons=value.comparisons||null;el('use-comparisons').checked=!!comparisons;renderComparisons();el('task-instructions').value=value.task_prompt||'';el('use-task').checked=!!value.task_prompt;el('moderator-presentation').value=value.avatar||'none';el('voice-keywords').value=(value.voice_keywords||[]).join('\n');},
    read(){return {comparisons:readComparisons(),task_prompt:el('use-task').checked?el('task-instructions').value:'',avatar:el('moderator-presentation').value,voice_keywords:lines(el('voice-keywords').value)};}
  };
  api('capabilities').then(c=>{el('avatar-availability').textContent=`The 3D character runs locally, without another account. ${c.streaming_voice?'Streaming Muse Voice is ready.':'Install the project dependencies and restart to enable streaming voice; recorded answers remain available.'}`;}).catch(()=>{});
})();
