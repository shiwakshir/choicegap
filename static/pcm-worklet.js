/* Downsample the microphone to 16 kHz mono PCM, posting paced 100 ms frames. */
class MusePCM extends AudioWorkletProcessor {
  constructor(){super();this.ratio=sampleRate/16000;this.position=0;this.pending=[];this.frame=new Int16Array(1600);this.index=0;}
  process(inputs){
    const input=inputs[0]?.[0];if(!input)return true;
    for(let i=0;i<input.length;i++)this.pending.push(input[i]);
    while(this.position+1<this.pending.length){
      const left=Math.floor(this.position),weight=this.position-left;
      const value=this.pending[left]*(1-weight)+this.pending[left+1]*weight;
      this.frame[this.index++]=Math.max(-1,Math.min(1,value))*(value<0?32768:32767);this.position+=this.ratio;
      if(this.index===1600){this.port.postMessage(this.frame.buffer,[this.frame.buffer]);this.frame=new Int16Array(1600);this.index=0;}
    }
    const consumed=Math.floor(this.position);this.pending=this.pending.slice(consumed);this.position-=consumed;
    return true;
  }
}
registerProcessor('muse-pcm',MusePCM);
