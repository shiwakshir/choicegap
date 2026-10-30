/* Local turn timing only. Silence never submits a research answer. */
(function(root) {
  'use strict';
  class SpokenTurn {
    constructor({maxMs=90000,quietMs=2800,minSpeechMs=500,minTurnMs=3000,threshold=.018}={}) {
      Object.assign(this,{maxMs,quietMs,minSpeechMs,minTurnMs,threshold});
      this.started=null;this.previous=null;this.lastSound=null;this.speechMs=0;this.ended=false;
    }
    observe(rms,now) {
      if(this.ended)return null;
      if(this.started===null)this.started=now;
      const delta=this.previous===null?0:Math.max(0,Math.min(now-this.previous,250));
      this.previous=now;
      if(Number.isFinite(rms)&&rms>=this.threshold){this.speechMs+=delta;this.lastSound=now;}
      let reason=null;
      if(now-this.started>=this.maxMs)reason='limit';
      else if(this.speechMs>=this.minSpeechMs&&now-this.started>=this.minTurnMs&&now-this.lastSound>=this.quietMs)reason='quiet';
      if(reason)this.ended=true;
      return reason;
    }
  }
  if(typeof module!=='undefined'&&module.exports)module.exports=SpokenTurn;
  else root.SpokenTurn=SpokenTurn;
})(typeof window!=='undefined'?window:globalThis);
