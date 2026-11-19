'use strict';
// Exercise UI state transitions with a small DOM substitute; no browser or API is used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function element() {
  return {value: '', textContent: '', hidden: false, disabled: false, readOnly: false,
    options: [], listeners: {}, attrs: {},
    classList: {toggle() {}},
    addEventListener(name, callback) { this.listeners[name] = callback; },
    append(child) { this.options.push(child); },
    replaceChildren() { this.options = []; },
    setAttribute(key, value) { this.attrs[key] = value; },
    removeAttribute(key) { delete this[key]; }};
}

async function main() {
  const nodes = {};
  const get = id => nodes[id] ||= element();
  get('mode').value = 'saved';
  get('strategy').value = 'zero_shot';
  get('placeholder').hidden = false;
  get('result').hidden = true;
  const requirement = 'When the test input changes, the output shall activate.';
  let available = false;
  let fail = false;
  let lastPayload;
  let revoked = 0;
  const context = vm.createContext({
    document: {getElementById: get, createElement: element},
    Blob,
    URL: {createObjectURL: () => 'blob:test-result', revokeObjectURL: () => { revoked++; }},
    fetch: async (url, options) => {
      if (url === '/api/catalog') return {ok: true, json: async () => ({
        requirements: [{requirement_id: 'REQ-002', requirement, difficulty: 'Easy', category: 'Test'}],
        default_model: 'test-model', live_available: available
      })};
      lastPayload = JSON.parse(options.body);
      return {ok: !fail, json: async () => fail ? {error: 'Simulated request failure'} : ({
        ...lastPayload, model: 'test-model', source: lastPayload.mode === 'saved' ? 'Saved experiment output' : 'New API generation',
        test_case: {given: '<script>this is displayed as text</script>', when: 'Input changes', then: 'Output activates'}
      })};
    }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../demo/app.js'), 'utf8'), context);
  await new Promise(setImmediate);
  assert.equal(get('requirement').value, requirement);
  assert.equal(get('requirement').readOnly, true);
  assert.equal(get('submit').disabled, false);
  await get('form').listeners.submit({preventDefault() {}});
  assert.equal(get('result').hidden, false);
  assert.equal(get('given').textContent, '<script>this is displayed as text</script>');
  assert.equal(get('download').href, 'blob:test-result');
  assert.equal(lastPayload.mode, 'saved');
  get('strategy').value = 'few_shot';
  get('strategy').listeners.change();
  assert.equal(get('result').hidden, true);
  assert.equal(revoked, 1);
  get('mode').value = 'live';
  get('mode').listeners.change();
  assert.equal(get('submit').disabled, true);
  assert.match(get('status').textContent, /server-side API key/);
  // Simulate a catalog reporting configured credentials; no credential enters the UI.
  vm.runInContext('catalog.live_available = true', context);
  get('mode').listeners.change();
  assert.equal(get('requirement').readOnly, false);
  assert.equal(get('model').readOnly, false);
  get('requirement').value = 'A new custom requirement';
  get('requirement').listeners.input();
  assert.equal(get('sample').value, '');
  await get('form').listeners.submit({preventDefault() {}});
  assert.equal(lastPayload.requirement_id, null);
  assert.equal(lastPayload.strategy, 'few_shot');
  assert.equal(get('result').hidden, false);
  fail = true;
  await get('form').listeners.submit({preventDefault() {}});
  assert.equal(get('result').hidden, true);
  assert.match(get('status').textContent, /Simulated request failure/);
  assert.equal(get('submit').disabled, false);
  get('mode').value = 'saved';
  get('mode').listeners.change();
  assert.equal(get('sample').value, 'REQ-002');
  assert.equal(get('requirement').value, requirement);
  assert.equal(get('model').readOnly, true);
  console.log('UI checks passed: saved/live state, strategy changes, custom input, JSON download, stale-result reset and errors.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
