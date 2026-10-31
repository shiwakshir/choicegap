(function(){
  'use strict';
  let clip=null,url='',review=null,stream=null,recorder=null,timer=null,version=0;
  function cleanup(){version++;clearTimeout(timer);if(recorder?.state==='recording'){recorder.onstop=null;recorder.stop();}recorder=null;stream?.getTracks().forEach(t=>t.stop());stream=null;if(url)URL.revokeObjectURL(url);url='';clip=null;review=null;}
  function render(){
    el('answer-control').innerHTML='<p class="hint">Use fictional information and show only the intended window. This records the screen, without microphone audio. You can preview it before sending it to Muse.</p><div class="actions"><button id="record-task" class="quiet">Record a window</button><button id="stop-task" class="quiet" hidden>Stop screen recording</button></div><label for="task-file">Or choose a WebM/MP4 task recording · up to 60 seconds / 12 MB</label><input id="task-file" type="file" accept="video/webm,video/mp4"><video id="task-preview" controls hidden></video><p id="task-status" class="hint" aria-live="polite"></p><button id="inspect-task" class="primary" hidden>Send clip to Muse for review</button><div id="task-review"></div>';
    el('record-task').onclick=record;el('stop-task').onclick=()=>recorder?.stop();
    el('task-file').onchange=()=>{const file=el('task-file').files[0];if(file)preview(file);};
    el('inspect-task').onclick=()=>run('Muse is reviewing the recording. Nothing is submitted as an answer yet…',async()=>{
      if(!clip)throw new Error('Record or choose a task clip first.');
      const selectedClip=clip,epoch=version,video=el('task-preview');let duration=selectedClip.seconds||video.duration;
      if(!Number.isFinite(duration)||duration<=0||duration>60)throw new Error('Choose a recording of up to 60 seconds with readable duration metadata.');
      const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(selectedClip.blob);});
      if(epoch!==version)throw new Error('The clip changed. Review the new clip before sending it.');
      const inspected=await api('inspect-clip',{id:session.id,nonce:session.nonce,video:data,mime:selectedClip.mime,duration});
      if(epoch!==version)return;
      review=inspected;
      el('task-review').innerHTML=`<h3>Does this match what happened?</h3><p class="hint">These are Muse's tentative descriptions, not verified click records. Confirm only events you recognise. You can reject them and explain instead.</p>${review.events.map(e=>`<label class="check"><input type="checkbox" data-task-event="${esc(e.id)}"><span><strong>${e.seconds}s</strong> · ${esc(e.description)}</span></label>`).join('')}<p class="hint">${esc(review.uncertainty)}</p><label for="task-correction">What should we correct or add?</label><textarea id="task-correction" rows="3" maxlength="6000"></textarea><label class="check"><input id="task-reviewed" type="checkbox"> I reviewed these descriptions against my recording.</label>`;
    });
  }
  function preview(blob,seconds){
    if(blob.size>12_000_000){error(new Error('Use a task recording up to 12 MB.'));return;}
    const mime=blob.type.startsWith('video/webm')?'video/webm':blob.type.startsWith('video/mp4')?'video/mp4':null;
    if(!mime){error(new Error('Choose a WebM or MP4 recording.'));return;}
    version++;if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(blob);clip={blob,mime,seconds};review=null;
    el('task-preview').src=url;el('task-preview').hidden=false;el('inspect-task').hidden=false;el('task-review').innerHTML='';
    el('task-status').textContent='Preview your recording. It stays in this browser until you choose to send it to Muse.';
  }
  async function record(){
    if(!navigator.mediaDevices?.getDisplayMedia||!window.MediaRecorder){error(new Error('Screen recording is unavailable here. You can upload a clip or skip this task.'));return;}
    const turn=version;
    try{
      const selected=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:5,width:{ideal:1280},height:{ideal:720}},audio:false});
      if(turn!==version){selected.getTracks().forEach(t=>t.stop());return;}stream=selected;
      const chunks=[],started=performance.now();recorder=new MediaRecorder(stream,{mimeType:'video/webm',videoBitsPerSecond:700000});
      const active=recorder;active.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      active.onstop=()=>{clearTimeout(timer);selected.getTracks().forEach(t=>t.stop());stream=null;recorder=null;if(turn!==version)return;el('stop-task').hidden=true;el('record-task').disabled=false;el('task-file').disabled=false;preview(new Blob(chunks,{type:'video/webm'}),Math.min(60,(performance.now()-started)/1000));};
      selected.getVideoTracks()[0].onended=()=>{if(active.state==='recording')active.stop();};
      active.start();el('stop-task').hidden=false;el('record-task').disabled=true;el('task-file').disabled=true;el('task-status').textContent='Recording the selected screen/window. Stop when the task is finished; maximum 60 seconds.';
      timer=setTimeout(()=>{if(active.state==='recording')active.stop();},60000);
    }catch{stream?.getTracks().forEach(t=>t.stop());stream=null;error(new Error('Screen recording was not started. Choose a clip or skip this task.'));}
  }
  window.taskCapture={render,cleanup,value(){if(recorder)throw new Error('Stop and review the screen recording first.');if(!review||!el('task-reviewed')?.checked)throw new Error('Review the recording descriptions, or skip this task.');return{review_id:review.id,confirmed_event_ids:[...document.querySelectorAll('[data-task-event]:checked')].map(e=>e.dataset.taskEvent),correction:el('task-correction').value};}};
  window.addEventListener('pagehide',cleanup);
})();
