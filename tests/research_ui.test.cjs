// Exercise the actual editor serializer with distinct quote spans and source relations.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/research.js', 'utf8');
const start = source.indexOf('function readWorkspaceEditor()');
const end = source.indexOf("$('#prototype-image').addEventListener", start);
const spans = ['fees', 'emissions'];
const rows = spans.map((quote, index) => ({
  value: index ? 'challenges' : 'supports', dataset: { source: 'S1' },
  closest: () => ({ querySelector: () => ({ value: spans[index] }) }),
}));
const cards = ['a', 'b', 'c', 'd'].map(id => ({
  dataset: { account: id },
  querySelector: () => ({ value: 'Reviewed factor' }),
  querySelectorAll: () => id === 'a' ? rows : [],
}));
const context = vm.createContext({
  structuredClone,
  researchWorkspace: {
    blueprint: { attributes: ['a', 'b', 'c', 'd'].map(id => ({ id })) },
    sources: [{ id: 'S1', text: 'I compare fees and emissions.' }],
  },
  $: () => ({ value: 'Reviewed decision' }),
  document: { querySelectorAll: () => cards },
});
vm.runInContext(source.slice(start, end), context);
const result = vm.runInContext('readWorkspaceEditor()', context);
assert.deepEqual(Array.from(result.mapping.accounts[0].references, r => r.quote), ['fees', 'emissions']);
assert.deepEqual(Array.from(result.mapping.accounts[0].references, r => r.relation), ['supports', 'challenges']);
spans[0] = 'invented quotation';
assert.throws(() => vm.runInContext('readWorkspaceEditor()', context), /exact, contiguous/);
console.log('Quote preservation, distinct relationships, and quotation rejection passed.');
