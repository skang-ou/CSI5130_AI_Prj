# Structured Prompting experiment

Run date: November 18, 2026 (America/Detroit).

## Configuration

- Model argument: `gpt-5.6`, matching the stored Zero-Shot baseline label.
- Prompt: `STRUCTURED_PROMPT` in `src/generator.py`.
- Shared system instruction: `SYSTEM_PROMPT`.
- API: `client.responses.create(model=..., instructions=..., input=...)`.
- Output: one JSON object with `given`, `when`, `then` per requirement.
- Generation excludes reference fields.
- Both strategies keep the same system instruction and API settings; only the task prompt differs.
- Model sampling settings use SDK/API defaults. No repeated-trial quality estimate is available.

## Sample before full run

Input: `experiments/structured_sample_requirements.csv`.
Output: `experiments/structured_sample_results.csv`.

REQ-002 (Easy), REQ-018 (Medium), REQ-021 and REQ-030 (Hard).
All four generated successfully with nonempty fields. The prompt stayed unchanged
between this sample and the full run. Sample outputs are separate preliminary
calls, not additional unique evaluation requirements or repeated-trial statistics.

```bash
python src/generator.py --strategy structured --input experiments/structured_sample_requirements.csv --output experiments/structured_sample_results.csv
python src/generator.py --strategy structured
```

## Full-run verification

- 30 rows, 30 unique IDs, matching all source requirements.
- 30 success records, zero error records.
- All Given/When/Then fields nonempty.
- All strategy labels are `structured`; all model arguments are `gpt-5.6`.
- Requirement text, category and difficulty match the source.
- Zero-Shot CSV SHA-256 unchanged.
- Five offline regression tests passed.

Success means the API request and parser completed. Semantic accuracy, comparative
quality, and boundary coverage still require the shared evaluation rubric.
REQ-023 generates a negative boundary case at exactly 100 ms. Compare semantic
validity against its only-if requirement rather than requiring literal agreement
with the positive manual reference.

## Artifact fingerprints

- Requirements CSV SHA-256: `a9ebe95ec0559ea41dbda73400e689f2266a618ad9ebc094005e80a430c159a2`
- Structured results SHA-256: `0422a9c53769477ebe68736537b093f9a008f2d37932121d39373a2ddef8fc2c`
- Zero-Shot results SHA-256: `dc7654a0facd1129ad7232808125c6f5f7321c42a6d2258856e273568050269e`
- Structured prompt UTF-8 SHA-256: `b88642f6aeb5254302cd1b9fa649a9b2022f608efa7ca0525fab4d0d0bcbf785`
- System instruction UTF-8 SHA-256: `c4ec49f2e3728e3a578d0641d5e1304aee862415313b72065b25ec53cff0b89d`
