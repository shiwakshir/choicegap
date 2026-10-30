const assert = require('node:assert/strict');
const SpokenTurn = require('../static/spoken-turn.js');

// Initial silence must never be mistaken for a completed spoken response.
let gate = new SpokenTurn();
for(let t=0;t<10000;t+=100)assert.equal(gate.observe(0,t),null);
// A brief click or cough is not sufficient to arm quiet-turn detection.
assert.equal(gate.observe(.1,10000),null);
for(let t=10100;t<15000;t+=100)assert.equal(gate.observe(0,t),null);
// A sustained answer followed by a pause stops capture, but does not submit text.
gate = new SpokenTurn();
for(let t=0;t<=1000;t+=100)assert.equal(gate.observe(.05,t),null);
for(let t=1100;t<3800;t+=100)assert.equal(gate.observe(0,t),null);
assert.equal(gate.observe(0,3800),'quiet');
assert.equal(gate.observe(.05,3900),null); // end is one-shot
// Background sound cannot keep the microphone running past its hard cap.
gate = new SpokenTurn({maxMs:4000});
for(let t=0;t<4000;t+=100)assert.equal(gate.observe(.04,t),null);
assert.equal(gate.observe(.04,4000),'limit');
// A short thinking pause during an answer does not end it.
gate = new SpokenTurn();
for(let t=0;t<=1000;t+=100)gate.observe(.04,t);
for(let t=1100;t<=3000;t+=100)assert.equal(gate.observe(0,t),null);
assert.equal(gate.observe(.04,3100),null);
assert.equal(gate.observe(0,5000),null);
assert.equal(gate.observe(0,6000),'quiet');
console.log('Spoken-turn silence, noise, pause and duration checks passed.');
