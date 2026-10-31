const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
for(const rate of [16000,24000,48000]){
  const frames=[];let Processor;
  const context=vm.createContext({sampleRate:rate,AudioWorkletProcessor:class{constructor(){this.port={postMessage:b=>frames.push(new Int16Array(b))};}},registerProcessor:(name,cls)=>{Processor=cls;},Int16Array});
  vm.runInContext(fs.readFileSync('static/pcm-worklet.js','utf8'),context);
  const processor=new Processor();
  for(let i=0;i<Math.ceil(rate*.5/128);i++)processor.process([[new Float32Array(128).fill(.5)]]);
  assert.ok(frames.length>=4&&frames.length<=5);
  for(const frame of frames){assert.equal(frame.length,1600);assert.ok([...frame].every(v=>v===16383));}
  assert.equal(processor.process([[]]),true);
}
console.log('PCM worklet sample-rate conversion, 100 ms framing and quiet-input checks passed.');
