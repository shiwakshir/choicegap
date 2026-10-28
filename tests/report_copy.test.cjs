// Exercise the shipped report renderer against old saved records and missing answers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/explore.js', 'utf8');
const escapeHtml = s => String(s ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const boilerplate = 'Statements and hypothetical choices measure different things. A discrepancy is a prompt to explore; agreement and mixed priorities are valid.';
const condition = (factor, label, outcome) => ({factor, factor_label: label, changed: {before:`${label}: £3`,after:`${label}: Free`}, response: {switched:outcome,displayed_choice: outcome === null ? 'skip' : 'a'}, evidence_refs:['interview.condition0'],selection_reason:'Recorded plan',stimulus:{a:{facts:['£3']},b:{facts:['Free']}}});
const analysis = {
  survey:{ratings:{a:5,b:4,c:3,d:2},statement:'<script>bad()</script>'},stated_priorities:['a'],
  alignment:{anchor:null,trigger:'Internal branch reason',interpretation:boilerplate},
  participant_explanation:{status:'corrected',effective:'The fee was my constraint.',source:'literal-local',original_model_interpretation:{summary:'An earlier description.'},correction:{text:'The fee was my constraint.'}},
  evidence:[{id:'interview.why',text:'I needed a lower fee.'}],
  condition_tests:[condition('b','Delivery cost',true),condition('d','Verification',false)],
  exposure_ledger:[],limitations:['Only a study exercise.'],
};
const context = vm.createContext({escapeHtml,labels:{a:'Environmental impact'},interviewOptions:()=>'<p>Recorded options</p>',analysis});
vm.runInContext(source.slice(source.indexOf('const uxStageNames'), source.indexOf('async function resumeInterview')), context);
const html = vm.runInContext('uxAnalysisHtml(analysis)', context);
assert.ok(html.includes('They switched to the other option.'));
assert.ok(html.includes('They chose the same option again.'));
assert.ok(html.includes('The fee was my constraint.'));
assert.ok(!html.includes(boilerplate));
assert.ok(!html.includes('<script>'));
assert.ok(html.includes('&lt;script&gt;'));
assert.ok(!vm.runInContext('uxChange(analysis.condition_tests[0])', context).includes('Delivery cost:'));
const readout = vm.runInContext('uxReadout(analysis)', context);
assert.ok(readout.summary.includes('delivery cost'));
assert.ok(readout.summary.includes('verification'));
context.choiceCase = {...analysis, alignment:{anchor:{displayed_choice:'b',stimulus:{a:{facts:['£3 delivery','Verified','Same window']},b:{facts:['Free delivery','Retailer claim','Same window']}}}}};
const choiceText = vm.runInContext('uxChoiceDescription(choiceCase)', context);
assert.ok(choiceText.includes('free delivery and retailer claim'));
assert.ok(!choiceText.includes('Same window'));
const skipped = structuredClone(analysis);
skipped.condition_tests = [condition('b','Delivery cost',null)];
skipped.participant_explanation.status = 'unresolved';
context.skipped = skipped;
const skippedHtml = vm.runInContext('uxAnalysisHtml(skipped)', context);
assert.ok(skippedHtml.includes('They skipped this comparison.'));
assert.ok(skippedHtml.includes('The participant did not confirm an explanation.'));
assert.ok(vm.runInContext('uxReadout(skipped).next',context).startsWith('Collect the missing'));
context.research = {completed_interviews:1,cases:[{analysis}],condition_groups:[],exposures:[],scope:'Completed sessions only.'};
const md = vm.runInContext('uxAggregateMarkdown(research)', context);
assert.ok(md.includes('What to do next'));
assert.ok(!md.includes(boilerplate));
console.log('Plain report findings, saved-record compatibility, correction visibility, skips and escaping passed.');
