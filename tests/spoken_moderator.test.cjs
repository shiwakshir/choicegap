// Exercise the actual participant controller with fake device/media adapters.
// No browser permissions, microphone capture, network calls or speech playback.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SpokenTurn=require('../static/spoken-turn.js');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{id,hidden:false,disabled:false,value:'',textContent:'',dataset:{},style:{},isConnected:true,
  replaceChildren(){},append(){},focus(){},pause(){},addEventListener(){},querySelectorAll(){return[];},classList:{toggle(){}}});return elements.get(id);}
let requested=0,stopped=0,utterance=null,recorders=[],calls=[];
class Recorder{constructor(){this.state='inactive';this.mimeType='audio/webm';recorders.push(this);}start(){this.state='recording';}stop(){this.state='inactive';this.stopped=this.onstop?.();}}
const stream=()=>({getTracks:()=>[{stop(){stopped++;}}]});
const speech={cancel(){},getVoices:()=>[],speak(u){utterance=u;}};
const window={speechSynthesis:speech,SpeechSynthesisUtterance:class{},MediaRecorder:Recorder,scrollTo(){},addEventListener(){}};
const context=vm.createContext({console,window,document:{getElementById:element,querySelectorAll:()=>[],addEventListener(){},createTextNode:text=>({textContent:text}),createElement:()=>element('dynamic')},
  navigator:{mediaDevices:{async getUserMedia(){requested++;return stream();}}},location:{search:'',origin:'http://example.test'},
  fetch:async(path,options)=>{calls.push({path,body:options?JSON.parse(options.body):null});return{ok:true,json:async()=>path==='/api/health'?{meta_enabled:true}:{transcript:'I used the familiar search tool for that task.'}};},
  URLSearchParams,URL,Blob,MediaRecorder:Recorder,SpeechSynthesisUtterance:window.SpeechSynthesisUtterance,
  AudioContext:class{constructor(){throw new Error('No audio device in controller test');}},
  SpokenTurn,setTimeout,clearTimeout,setInterval,clearInterval,performance,localStorage:{getItem(){return null;},removeItem(){}},
});
vm.runInContext(fs.readFileSync('static/studio.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await tick();calls=[];
  run(`session={id:'session-test',nonce:'issued-turn',recording:true,recording_seconds:90,spoken_moderator:true,status:'active',question:{type:'open',phase:'interview',prompt:'Tell me about your last AI task.',options:[]}};spokenMode=true;wavBase64=async()=> 'fictional-audio';speakCurrentQuestion();`);
  assert.equal(requested,0,'microphone must remain off while moderator speaks');
  assert.equal(element('spoken-moderator').dataset.state,'speaking');
  utterance.onend();await tick();
  assert.equal(requested,1);assert.equal(recorders.length,1);
  assert.equal(recorders[0].state,'recording');
  assert.equal(element('spoken-moderator').dataset.state,'listening');
  recorders[0].stop();await recorders[0].stopped;await tick();
  assert.ok(stopped>0,'microphone tracks must stop before transcription');
  assert.equal(element('open-answer').value,'I used the familiar search tool for that task.');
  assert.equal(element('spoken-moderator').dataset.state,'review');
  assert.equal(run('inputMode'),'confirmed_transcript');
  assert.equal(calls.filter(c=>c.path.endsWith('/transcribe')).length,1);
  assert.equal(calls.filter(c=>c.path.endsWith('/answer')).length,0,'transcription must never auto-submit an answer');
  // A stale speech callback after pause cannot turn the microphone back on.
  run('speakCurrentQuestion()');const stale=utterance;await element('pause-spoken').onclick();stale.onend();await tick();
  assert.equal(requested,1);assert.equal(run('spokenMode'),false);
  // Cancelling while permission is pending closes the eventually returned stream.
  let permission;context.navigator.mediaDevices.getUserMedia=()=>{requested++;return new Promise(resolve=>permission=resolve);};
  run('spokenMode=true;speakCurrentQuestion()');utterance.onend();await tick();
  await element('pause-spoken').onclick();const before=stopped;permission(stream());await tick();
  assert.equal(recorders.length,1);assert.ok(stopped>before);
  // Permission resolving during answer processing must not open capture.
  run('spokenMode=true;speakCurrentQuestion()');utterance.onend();await tick();
  run('busy=true');permission(stream());await tick();
  assert.equal(recorders.length,1);run('busy=false');
  // Denial falls back to text and leaves no active recording.
  context.navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Permission denied');};
  run('spokenMode=true;speakCurrentQuestion()');utterance.onend();await tick();
  assert.equal(run('recording'),null);assert.equal(run('spokenMode'),false);
  assert.match(element('errors').textContent,/Microphone unavailable/);
  run('stopMedia()');
  console.log('Spoken controller speaking/listening/transcription/review, pause, stale callback and microphone-denial checks passed.');
})().catch(err=>{run('stopMedia()');console.error(err);process.exitCode=1;});
