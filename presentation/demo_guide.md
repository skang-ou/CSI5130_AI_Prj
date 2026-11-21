# Final demonstration runbook

Presenter: Sangkook Kang. Target: two minutes during slide 10 of the final deck.
The audience should see requirement input, strategy selection and Given/When/Then
output. Clearly distinguish replay from newly generated API output.

## Before presenting

1. Close credential files and unrelated windows before screen sharing or recording.
2. Start `python demo/app.py` from a Python environment with `requirements.txt` installed.
3. Open `http://127.0.0.1:8765` in a separate browser tab. Leave it ready before the talk.
4. Keep **Saved experiment** selected for the reliable core walkthrough.
5. Open `presentation/project_presentation.html` or its PDF and rehearse the switch
   from slide 10 to the demo, then back to slide 11.

Use the English deck for the course presentation.

## Two-minute walkthrough

| Time | Action | Talking point |
| --- | --- | --- |
| 0:00–0:30 | REQ-002, Zero-Shot, Show saved test | Drive is the guard, SOC crossing is the event, warning is the response. |
| 0:30–1:10 | REQ-018, run each strategy | Zero-Shot uses vague processing; other prompts expose a concrete event. |
| 1:10–1:40 | REQ-023, Structured | Exactly 100 ms fails the strict age condition, so rejection is supported. |
| 1:40–2:00 | Download JSON, then return to slide 11 | Download is separate from frozen experiments. Explain reviewer limitations. |

The page label **Saved experiment output** must remain visible. This is a
working replay interface, not evidence of a new live model call. The saved
Zero-Shot/Few-Shot REQ-023 tests agree with a flawed manual reference; explain
why the original requirement governs the evaluation.

## Optional new generation

Only add this if the allotted time and API setup permit. Configure `OPENAI_API_KEY`
privately in the server environment before startup, then restart the server.
Select **Live API**, choose a strategy, and enter a new synthetic requirement:

> When the control input changes from LOW to HIGH, the controller shall activate the status LED.

Select **Generate test** once and explain the resulting fields. The page labels
it **New API generation**. A call may incur charges and its output may differ
from previous examples. Do not show the API key or silently switch the model.
If it fails, say that the live call is unavailable and return to saved mode.
The core two-minute walkthrough does not depend on this optional request.

## Server-free fallback and preflight

```bash
python demo/rehearse.py
```

This runs the same saved-result service for REQ-002, REQ-018 and REQ-023 under all
three strategies. It prints nine existing cases with their source labels, makes
no API calls, and does not change experimental data. It is a terminal fallback,
not a new LLM generation. Use `--output /tmp/demo_rehearsal.json` to save an
optional rehearsal record outside the repository.

For an HTTP check while the local server is running:

```bash
python tests/smoke_demo_http.py
```

If no server or terminal is available, use slides 2, 7 and 8, which already show
the representative outputs. Explain that this fallback displays recorded cases.

## Likely questions

**Which strategy is best?** Structured has the highest recorded mean in this
review. It differs from Few-Shot on only REQ-023. This does not establish a
statistically significant or independently validated general advantage.

**Why does Structured have 10/10?** The rubric covers a single scenario, and the
small synthetic dataset has a ceiling. It does not measure exhaustive branches,
executable code coverage, or hardware correctness.

**Who assigned the ratings?** One unblinded OpenAI assistant that also helped
with the project. All 450 criterion rationales are available; there is no
independent human validation or inter-rater agreement measurement.

**Why can a reference-matching answer be wrong?** The reference for REQ-023
reverses an only-if implication. The original requirement is authoritative.

**Are these executable tests?** No. They are textual Given/When/Then drafts.
Executing them against a controller requires further implementation and review.
