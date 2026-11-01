# Few-Shot Prompting experiment

Run date: November 18, 2026 (America/Detroit).

## Configuration

- Model argument: `gpt-5.6`, matching both earlier experiment labels.
- Task template: `FEW_SHOT_PROMPT` in `src/generator.py`.
- Demonstrations: `data/few_shot_examples.json`, in fixed EX-001 through EX-004 order.
- Shared system instruction: `SYSTEM_PROMPT`, unchanged from the earlier runs.
- API: `client.responses.create(model=..., instructions=..., input=...)`.
- Output: one JSON object with `given`, `when`, `then` per requirement.
- Sampling settings use SDK/API defaults. This run does not estimate repeated-trial variation.

Few-Shot prepends four independent demonstrations to the Zero-Shot task and JSON
format. It does not include Structured Prompting's seven-rule instruction block.
The same model argument, system instruction, parser, and CSV schema serve all
three strategies. Only the task prompt differs.

## Demonstration selection and answer isolation

The demonstrations are newly authored synthetic examples, not rows or reference
answers copied from the 30-requirement evaluation dataset:

| ID | Topic | Demonstrated feature |
| --- | --- | --- |
| EX-001 | Greenhouse ventilation | Strict humidity threshold |
| EX-002 | Packaging actuator emergency stop | Operating-state guard and 40 ms response deadline |
| EX-003 | Machining coolant flow | Active-state guard and continuous 750 ms duration |
| EX-004 | Irrigation reservoir | Inhibited request below an 8 L limit |

The same examples appear in every Few-Shot request, without selecting them based
on the target reference answer. No evaluation reference fields enter the prompt.
Before applying `--limit`, the loader checks all input requirements for overlap
with demonstrations after case and whitespace normalization. It also rejects
duplicate examples and missing/empty example fields. This catches normalized
text duplicates, not all semantic similarity. Shared test-design patterns are
intentional, while demonstration scenarios and numeric values remain separate.

## Sample before full run

Input: `experiments/few_shot_sample_requirements.csv`.
Output: `experiments/few_shot_sample_results.csv`.

The sample uses the same four requirements as the Structured check: REQ-002
(Easy), REQ-018 (Medium), REQ-021 and REQ-030 (Hard). All four API calls and
parsing steps succeeded, with nonempty outputs. No prompt or example changes
followed the sample. The four sample calls are preliminary checks, not four
additional unique evaluation requirements or a repeated-trial study.

```bash
python src/generator.py --strategy few_shot --input experiments/few_shot_sample_requirements.csv --output experiments/few_shot_sample_results.csv
python src/generator.py --strategy few_shot
```

Commands require the OpenAI package and a privately configured `OPENAI_API_KEY`.
New API calls can produce different wording and incur usage charges.

## Full-run verification

- 30 rows, 30 unique IDs, covering all source requirements.
- 30 success records, zero error records, no empty Given/When/Then fields.
- All strategy labels are `few_shot`; all model arguments are `gpt-5.6`.
- Requirement text, category, and difficulty match the source dataset.
- Earlier Zero-Shot and Structured results and the evaluation dataset are unchanged.
- Ten offline regression tests passed, including reference exclusion and overlap rejection.

All three strategies now have 30 saved outputs, for 90 unique requirement/strategy
pairs. A success flag confirms request/parsing completion, not semantic accuracy.
Some sample outputs add initial-state assumptions (such as a warning initially
being absent); assess these consistently under the common rubric. Quality
scoring, strategy comparisons, and generalization claims remain pending.

## Artifact fingerprints

- `data/requirements.csv` SHA-256: `a9ebe95ec0559ea41dbda73400e689f2266a618ad9ebc094005e80a430c159a2`
- `data/few_shot_examples.json` SHA-256: `60a11d38d5b47c8bf2ed3479cedc9481cb0e92dae8b835a77dbce015d2acced0`
- `experiments/few_shot_sample_requirements.csv` SHA-256: `2a584d17a185605ccf66c1d61732fea069997f8045699efe2468ee7707009d73`
- `experiments/few_shot_sample_results.csv` SHA-256: `d55050c19059c594d6d361afddd6fc3699ece2c7ce3d59e7ea1fbdc624527537`
- `results/few_shot_results.csv` SHA-256: `2d74c0633c07fad3aac877e414b0f356a62e2195c2955d18e660a86ea313918f`
- `results/zero_shot_results.csv` SHA-256: `dc7654a0facd1129ad7232808125c6f5f7321c42a6d2258856e273568050269e`
- `results/structured_results.csv` SHA-256: `0422a9c53769477ebe68736537b093f9a008f2d37932121d39373a2ddef8fc2c`
- Few-Shot template UTF-8 SHA-256: `03b7e1b83aa4accbb3f35d6579bcead2e7e331e000263e132534c84371a39d2c`
- System instruction UTF-8 SHA-256: `c4ec49f2e3728e3a578d0641d5e1304aee862415313b72065b25ec53cff0b89d`
