# Interactive demonstration

A local browser interface for entering a requirement, selecting Zero-Shot,
Structured, or Few-Shot prompting, and reviewing Given/When/Then output.

## Start

From the repository root, use a Python environment with the project dependencies:

```bash
python -m pip install -r requirements.txt
python demo/app.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Stop the server with Ctrl+C.
For another local port, run `python demo/app.py --port 8766`.

The server listens only on the local computer. It serves only the demo assets
and its two JSON endpoints, not the repository directory.

## Saved experiment mode

This is the default and requires no API key or internet connection once the
Python dependencies are installed.

1. Select a sample requirement and a prompting strategy.
2. Select **Show saved test**.
3. Review the three output fields and the original model label.
4. Change the strategy and run again to compare the saved wording.
5. Select **Download JSON** to save the displayed case in the browser.

All 30 requirements and all three strategies are available. The text is read-only
in this mode because the output is a replay of an existing experiment, not a new
answer to edited input. The page labels recorded outputs **Saved experiment output**.

## Live API mode

Set `OPENAI_API_KEY` privately in the server process environment before starting
the app. Never put the key in the browser, a screenshot, or a committed file.
The app reads this environment variable; it does not automatically read `.env`
or the local `.OpenaiApikey` file. Restart after changing the environment.

1. Start the server with the environment variable configured.
2. Select **Live API** and a strategy.
3. Edit a sample or choose **Custom requirement (Live API)** and enter new text.
4. Keep the default model (`gpt-5.6`) or enter a model available to your account.
5. Select **Generate test**, then inspect Given, When, and Then.

Live generation makes a new API call and can incur charges. New wording can
differ from the saved baseline. The model must be accessible to the configured
account. No model is silently substituted. Without a key, live generation is
disabled and the page explains how to enable it.

The live route reuses `src/generator.py`, including its prompts, JSON parser,
and the four independent Few-Shot examples. It excludes evaluation reference
answers. The full dataset and the submitted requirement are checked for overlap
with Few-Shot demonstrations before making a call. One live request is allowed
at a time, with a 60-second SDK timeout and no automatic retries.

## Suggested class demonstration (2 minutes)

- **REQ-002:** show the Drive guard, the 10% crossing, and the warning.
- **REQ-018:** compare the Zero-Shot trigger with Structured and Few-Shot.
- **REQ-023:** contrast positive acceptance with Structured's negative 100 ms case.
  Explain why the original only-if statement does not guarantee acceptance, even
  though the manual reference suggests it does.
- Optionally switch to Live API and submit a new synthetic requirement.

Use the saved workflow if the API is unavailable. A generated test is a draft;
review against the original requirement rather than treating it as an executable
hardware test or evidence of complete coverage.

## Preservation and verification

The app reads experiment CSVs but never writes to them. Downloaded JSON is a
separate browser download, not a new experimental result. Review scores, analysis
artifacts, source requirements, and prompts are unchanged by demo requests.

Verification performed during implementation:

- 28 Python tests pass, including exact replay of all 90 saved outputs, live-path
  tests using a mocked API, input/overlap rejection, and safe HTTP error handling.
- `node tests/test_demo_ui.js` checks UI state transitions, custom input, strategy
  changes, JSON download, stale-result clearing, and failure handling using a DOM
  substitute. It does not verify browser rendering.
- `python tests/smoke_demo_http.py` checks a running server's assets, sample catalog,
  and saved endpoints for all three strategies; it makes no API calls.
- Browser preview was unavailable in the authoring environment. Visual layout
  and browser-specific behavior still need a user-side check.
- No new paid API call was made for the demo verification. Live behavior was
  tested with mocked responses; the shared generator has the earlier real runs.

```bash
python -m unittest discover -s tests -v
node tests/test_demo_ui.js
# With the local app running:
python tests/smoke_demo_http.py
```
