'use strict';

// All dynamic text uses textContent, so requirements and model output cannot become HTML.
const elements = Object.fromEntries(['form', 'mode', 'strategy', 'sample', 'requirement', 'model',
  'mode-help', 'model-help', 'submit', 'status', 'placeholder', 'result', 'result-meta',
  'result-requirement', 'given', 'when', 'then', 'download'].map(id => [id, document.getElementById(id)]));
const strategyNames = {zero_shot: 'Zero-Shot', structured: 'Structured', few_shot: 'Few-Shot'};
let catalog = null;
let busy = false;
let downloadURL = null;

function status(message, error = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle('error', error);
}

function invalidateResult() {
  elements.result.hidden = true;
  elements.placeholder.hidden = false;
  // Prevent a download for an old input from appearing to belong to a new selection.
  if (downloadURL) URL.revokeObjectURL(downloadURL);
  downloadURL = null;
  elements.download.removeAttribute('href');
}

function updateControls() {
  const live = elements.mode.value === 'live';
  elements.requirement.readOnly = !live;
  elements.model.readOnly = !live;
  elements.sample.options[0].disabled = !live;
  elements['mode-help'].textContent = live
    ? (catalog.live_available ? 'Generate a new test through the API. API usage can incur charges.'
      : 'Set OPENAI_API_KEY in the server environment and restart to enable live generation.')
    : 'Replay recorded outputs. No API call is made.';
  elements['model-help'].textContent = live
    ? 'Uses the existing generator and your configured model access.'
    : 'The saved result retains its original model label.';
  if (!live) elements.model.value = catalog.default_model;
  elements.submit.textContent = busy ? 'Working…' : live ? 'Generate test ↗' : 'Show saved test ↗';
  elements.submit.disabled = busy || !catalog || (live && !catalog.live_available);
  for (const id of ['mode', 'strategy', 'sample', 'requirement', 'model']) elements[id].disabled = busy;
  elements.result.setAttribute('aria-busy', String(busy));
}

function chooseSample() {
  const selected = catalog.requirements.find(r => r.requirement_id === elements.sample.value);
  elements.requirement.value = selected ? selected.requirement : '';
  invalidateResult();
  status('Ready. Choose a strategy and show or generate a test.');
}

function showResult(data) {
  elements['result-meta'].textContent = `${data.source} · ${strategyNames[data.strategy]} · ${data.model}`;
  elements['result-requirement'].textContent = `${data.requirement_id || 'Custom requirement'}: ${data.requirement}`;
  for (const key of ['given', 'when', 'then']) elements[key].textContent = data.test_case[key];
  downloadURL = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
  elements.download.href = downloadURL;
  elements.download.download = `${data.requirement_id || 'custom'}_${data.strategy}_demo.json`;
  elements.placeholder.hidden = true;
  elements.result.hidden = false;
}

elements.mode.addEventListener('change', () => {
  if (elements.mode.value === 'saved') {
    if (!elements.sample.value) elements.sample.value = 'REQ-002';
    chooseSample();
  } else invalidateResult();
  updateControls();
  status(elements.mode.value === 'live' && !catalog.live_available
    ? 'Live mode needs a server-side API key. Saved mode is ready to use.' : 'Ready.');
});
elements.sample.addEventListener('change', chooseSample);
elements.strategy.addEventListener('change', () => { invalidateResult(); status('Strategy changed. Run again to show its result.'); });
elements.requirement.addEventListener('input', () => {
  if (elements.mode.value === 'live') elements.sample.value = '';
  invalidateResult(); status('Requirement changed. Generate a new test.');
});
elements.model.addEventListener('input', () => { invalidateResult(); status('Model changed. Generate a new test.'); });

elements.form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !catalog) return;
  invalidateResult();
  busy = true;
  updateControls();
  status(elements.mode.value === 'saved' ? 'Loading the saved experiment output…' : 'Waiting for the model response…');
  try {
    const response = await fetch('/api/generate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mode: elements.mode.value, strategy: elements.strategy.value,
        requirement_id: elements.sample.value || null, requirement: elements.requirement.value,
        model: elements.model.value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
    showResult(data);
    status(elements.mode.value === 'saved' ? 'Saved output loaded. This is a recorded experiment result.' : 'New test generated. Review it against the requirement.');
  } catch (error) {
    status(error.message || 'Cannot reach the local demo. Check the server and try again.', true);
  } finally {
    busy = false;
    updateControls();
  }
});

async function start() {
  try {
    const response = await fetch('/api/catalog');
    if (!response.ok) throw new Error('Cannot load the dataset. Check the local server.');
    catalog = await response.json();
    elements.sample.replaceChildren();
    const custom = document.createElement('option');
    custom.value = ''; custom.textContent = 'Custom requirement (Live API)';
    elements.sample.append(custom);
    for (const r of catalog.requirements) {
      const option = document.createElement('option');
      option.value = r.requirement_id;
      option.textContent = `${r.requirement_id} · ${r.difficulty} · ${r.category}`;
      elements.sample.append(option);
    }
    elements.sample.value = 'REQ-002';
    elements.model.value = catalog.default_model;
    chooseSample();
    updateControls();
  } catch (error) {
    status(error.message || 'Cannot reach the local demo.', true);
  }
}
start();
