'use strict';
// Test browser-deck navigation without requiring a graphical browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function element() {
  return {textContent: '', disabled: false, attrs: {}, children: [],
    clientWidth: 1280, clientHeight: 720,
    classList: {on: false, toggle(name, value) {this.on = value === undefined ? !this.on : value;return this.on;}},
    setAttribute(name, value) {this.attrs[name] = value;},
    replaceChildren() {this.children = [];}, append(child) {this.children.push(child);}};
}
function check(file) {
  const html = fs.readFileSync(file, 'utf8');
  assert.equal((html.match(/<section /g) || []).length, 14);
  assert.equal((html.match(/data:image\/png;base64,/g) || []).length, 2);
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const slides = Array.from({length: 14}, element);
  const elements = Object.fromEntries(['main', '#count', '#prev', '#next', '#note-text', '#note-time', '#sources', '#toggle', '#full', '#print', '#help'].map(k => [k, element()]));
  let keyboard;
  let scale;
  const context = vm.createContext({document: {
    querySelectorAll: () => slides, querySelector: k => elements[k],
    createElement: element, body: element(),
    documentElement: {style: {setProperty(name, value) {scale = value;}}},
    addEventListener(name, fn) {keyboard = fn;}
  }, window: {addEventListener() {}, print() {}}, history: {replaceState() {}}, location: {hash: ''}});
  vm.runInContext(script, context);
  assert.equal(elements['#count'].textContent, '1 / 14');
  assert.equal(elements['#prev'].disabled, true);
  assert.equal(scale, 1);
  elements['#next'].onclick();
  assert.equal(elements['#count'].textContent, '2 / 14');
  keyboard({key: 'End', preventDefault() {}});
  assert.equal(elements['#count'].textContent, '14 / 14');
  assert.equal(elements['#next'].disabled, true);
  keyboard({key: 'Home', preventDefault() {}});
  elements['#toggle'].onclick();
  assert.equal(elements['#toggle'].attrs['aria-expanded'], true);
  for (let i = 0; i < 14; i++) {
    vm.runInContext(`show(${i})`, context);
    assert.equal(slides.filter(s => s.classList.on).length, 1);
    assert.ok(elements['#note-text'].textContent.length > 30);
    assert.ok(elements['#sources'].children.length > 0);
  }
  console.log(path.basename(file) + ': 14 slides, notes, sources, scaling and keyboard controls passed.');
}
const root = path.join(__dirname, '..');
check(path.join(root, 'presentation/project_presentation.html'));
