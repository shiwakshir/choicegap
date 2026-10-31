(function(){
  'use strict';
  class MuseStream {
    constructor({onPartial,onFinal,onError}){Object.assign(this,{onPartial,onFinal,onError});this.transcript='';this.closed=false;this.final=new Promise(resolve=>this.resolveFinal=resolve);}
    async start(stream,state){
      const response=await fetch('/api/studio/voice-ticket',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:state.id,nonce:state.nonce})});
      const ticket=await response.json();if(!response.ok)throw new Error(ticket.error||'Streaming unavailable');
      const url=new URL(ticket.url);if(url.protocol!=='ws:'||url.hostname!=='127.0.0.1')throw new Error('Invalid local voice relay');
      this.socket=new WebSocket(url.href);
      await new Promise((resolve,reject)=>{
        const timeout=setTimeout(()=>reject(new Error('Voice stream timed out')),20000);
        this.socket.onmessage=event=>{
          let value;try{value=JSON.parse(event.data);}catch{return;}
          if(value.type==='ready'){clearTimeout(timeout);resolve();}
          if(value.type==='error'){clearTimeout(timeout);reject(new Error(value.message));this.onError?.();this.resolveFinal('');}
          if(value.type==='transcript')this.onPartial?.(value.transcript||'');
          if(value.type==='speechComplete'){this.transcript=value.transcript||'';this.resolveFinal(this.transcript);this.onFinal?.(this.transcript);}
        };
        this.socket.onerror=()=>{clearTimeout(timeout);reject(new Error('Voice stream unavailable'));this.resolveFinal('');this.onError?.();};
        this.socket.onclose=()=>{clearTimeout(timeout);if(!this.transcript&&!this.closed){reject(new Error('Voice stream closed'));this.resolveFinal('');this.onError?.();}};
      });
      if(this.closed)throw new Error('Voice stream cancelled');
      this.context=new AudioContext();await this.context.audioWorklet.addModule('/pcm-worklet.js');await this.context.resume();
      if(this.closed){await this.context.close();throw new Error('Voice stream cancelled');}
      if(this.context.state!=='running')throw new Error('Audio processing unavailable');
      this.source=this.context.createMediaStreamSource(stream);this.processor=new AudioWorkletNode(this.context,'muse-pcm');
      const silent=this.context.createGain();silent.gain.value=0;this.source.connect(this.processor);this.processor.connect(silent);silent.connect(this.context.destination);
      this.processor.port.onmessage=event=>{if(this.socket.readyState===WebSocket.OPEN&&this.socket.bufferedAmount<64000)this.socket.send(event.data);};
    }
    async finish(){this.source?.disconnect();this.processor?.disconnect();if(this.transcript)return this.transcript;if(this.socket?.readyState===WebSocket.OPEN)this.socket.send(JSON.stringify({type:'endStream'}));return await Promise.race([this.final,new Promise(resolve=>setTimeout(()=>resolve(''),6000))]);}
    close(){this.closed=true;this.source?.disconnect();this.processor?.disconnect();if(this.context&&this.context.state!=='closed')this.context.close().catch(()=>{});if(this.socket&&this.socket.readyState<2)this.socket.close();this.resolveFinal('');}
  }
  window.MuseStream=MuseStream;
})();
