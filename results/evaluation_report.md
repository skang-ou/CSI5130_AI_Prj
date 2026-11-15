# Evaluation results

Rubric: v1.0. Review date: November 18, 2026.

**Method:** AI-generated single-reviewer semantic ratings. No independent human validation, blinding, or inter-rater agreement measurement.

All 90 saved outputs received five authored semantic scores and criterion-specific
rationales. The evaluator validates those judgments and computes arithmetic; it
does not independently establish their correctness. No new API calls were made.

## Quantitative results

All strategies have 30/30 successful generation records and 30/30 scored cases.
Generation success is separate from the rubric scores below.

| Strategy | Mean total /10 | Full scores /30 | Minor unsupported additions | Material unsupported additions |
| --- | ---: | ---: | ---: | ---: |
| zero_shot | 9.7000 | 26 | 3 | 1 |
| structured | 10.0000 | 30 | 0 | 0 |
| few_shot | 9.8667 | 29 | 0 | 1 |

Full-score counts are descriptive rubric outcomes, not validated accuracy or pass rates.

### Mean criterion scores (0 to 2)

| Strategy | Preconditions | Trigger | Expected behavior | Conditions / boundaries | No unsupported behavior |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero_shot | 1.9667 | 1.9667 | 1.9333 | 2.0000 | 1.8333 |
| structured | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 |
| few_shot | 2.0000 | 2.0000 | 1.9333 | 2.0000 | 1.9333 |

### Difficulty breakdown (10 cases per cell)

| Strategy | Easy mean /10 | Medium mean /10 | Hard mean /10 |
| --- | ---: | ---: | ---: |
| zero_shot | 9.9000 | 9.6000 | 9.6000 |
| structured | 10.0000 | 10.0000 | 10.0000 |
| few_shot | 10.0000 | 10.0000 | 9.6000 |

Exact means, per-criterion 0/1/2 counts and total distributions are in
`evaluation_summary.json`. Every case score is in `evaluation_scores.csv`;
evidence snapshots and all 450 rationales are in `../evaluation/reviews.json`.

## Representative examples

### REQ-002 (zero_shot): Successful guarded threshold test

Requirement: When battery SOC falls below 10% while the vehicle is in Drive, the system shall display a low-battery warning.

- Given: The vehicle is in Drive and the battery SOC is at or above 10%.
- When: The battery SOC falls below 10%.
- Then: The system displays a low-battery warning.

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 2, 2, 2. Total: 10/10.

Then displays the low-battery warning.

Reference comparison: The manual reference is compatible; equivalent wording and minimal setup differences are accepted.

### REQ-013 (few_shot): Successful response-deadline test

Requirement: When a valid wake-up message is received while the controller is in Sleep mode, the controller shall enter Active mode within 100 ms.

- Given: The controller is in Sleep mode.
- When: A valid wake-up message is received.
- Then: The controller enters Active mode within 100 ms of receiving the message.

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 2, 2, 2. Total: 10/10.

Then enters Active within 100 ms of that message.

Reference comparison: The manual reference is compatible; equivalent wording and minimal setup differences are accepted.

### REQ-018 (zero_shot): Structural weakness requiring clarification

Requirement: When a charging request is received and the connector is locked successfully, the system shall enable charging.

- Given: A charging request has been received and the connector is locked successfully
- When: The system processes the charging request
- Then: The system enables charging

Scores in rubric order (Given, When, Then, coverage, unsupported): 1, 1, 2, 2, 1. Total: 7/10.

- Precondition Correctness: Given already states "A charging request has been received", moving the request event out of When; the scenario remains reconstructable.
- Trigger Correctness: When says only "The system processes the charging request", rather than a concrete request-receipt or locking event.
- Unsupported Behavior / Hallucination: The extra "processes the charging request" step is an incidental workflow assumption not specified by the requirement; no material extra response is asserted.

Reference comparison: The reference adds attached/valid connector details and uses a joint event. Request receipt with successful locking already established is also valid; the original text imposes no unique ordering.

### REQ-023 (zero_shot): Unsupported acceptance assertion

Requirement: The system shall accept a received command only if its checksum is valid and its message age is less than 100 ms.

- Given: A received command has a valid checksum and a message age of less than 100 ms
- When: The system evaluates the received command
- Then: The system accepts the command

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 0, 2, 0. Total: 6/10.

- Expected Behavior Correctness: Then says "The system accepts the command" for a valid/young command. Only-if establishes necessary conditions, so this guaranteed acceptance is not entailed.
- Unsupported Behavior / Hallucination: The positive acceptance assertion introduces a sufficient-condition assumption absent from the requirement.

Reference comparison: The reference guarantees acceptance when checksum is valid and age <100 ms. This reverses the only-if implication. The requirement supports rejection for an invalid checksum or age >=100 ms; agreement with the positive reference does not establish correctness.

### REQ-023 (few_shot): Same logical error despite reference agreement

Requirement: The system shall accept a received command only if its checksum is valid and its message age is less than 100 ms.

- Given: A command has a valid checksum and a message age of less than 100 ms.
- When: The command is received by the system.
- Then: The system accepts the command.

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 0, 2, 0. Total: 6/10.

- Expected Behavior Correctness: Then says "The system accepts the command" when both necessary conditions hold; their conjunction alone does not guarantee acceptance.
- Unsupported Behavior / Hallucination: The positive acceptance assertion invents sufficiency, repeating the manual reference's unsupported assumption.

Reference comparison: The reference guarantees acceptance when checksum is valid and age <100 ms. This reverses the only-if implication. The requirement supports rejection for an invalid checksum or age >=100 ms; agreement with the positive reference does not establish correctness.

### REQ-023 (structured): Valid negative boundary despite reference disagreement

Requirement: The system shall accept a received command only if its checksum is valid and its message age is less than 100 ms.

- Given: No additional preconditions are specified.
- When: The system receives a command with a valid checksum and a message age of exactly 100 ms.
- Then: The system shall not accept the command.

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 2, 2, 2. Total: 10/10.

Then rejects the command at 100 ms, which follows from acceptance requiring age strictly less than 100 ms.

Reference comparison: The reference guarantees acceptance when checksum is valid and age <100 ms. This reverses the only-if implication. The requirement supports rejection for an invalid checksum or age >=100 ms; agreement with the positive reference does not establish correctness.

### REQ-010 (zero_shot): Minor unnecessary setup restriction

Requirement: When the driver presses the hazard switch, all turn indicator lamps shall flash.

- Given: The embedded system is operational and the hazard switch is not pressed
- When: The driver presses the hazard switch
- Then: All turn indicator lamps flash

Scores in rubric order (Given, When, Then, coverage, unsupported): 2, 2, 2, 2, 1. Total: 9/10.

- Unsupported Behavior / Hallucination: Given adds "the embedded system is operational", a minor unnecessary restriction explicitly covered by the rubric's score-1 example.

Reference comparison: The manual reference is compatible; equivalent wording and minimal setup differences are accepted.

## Interpretation and limitations

- Structured receives full credit throughout this particular review. This is a ceiling
  effect under the stated single-scenario rubric, not evidence of exhaustive coverage.
- Most outputs share similar wording and valid scenarios. A small number of judgments
  drive the score differences; do not infer broad superiority from these means.
- REQ-023 explains both material unsupported additions. The issue is a necessary versus
  sufficient condition, not a malformed response or API failure.
- The minor setup ratings in Zero-Shot REQ-010 and REQ-019 follow the rubric's
  unnecessary-restriction anchor. Compatible observable-output setup is allowed:
  for example, an initially clear fault or available freeze-frame signals.
- The three low scores for Zero-Shot REQ-018 have separate rationales: misplaced
  request receipt, vague When, and an unsupported incidental processing step.
- Ratings come from one unblinded AI reviewer that also assisted with the project.
  There is no independent human validation or inter-rater reliability estimate.
- The rubric followed generation and preliminary inspection. It is not preregistered,
  and 30 synthetic requirements with one output per pair limit generalization.
- A full score does not require a test suite, executable hardware tests, or every
  positive/negative branch. It means this one scenario satisfies rubric v1.0.
- Charts, paired comparisons and sensitivity checks are available in
  [the analysis report](analysis/analysis_report.md).

## Reproduction

From the repository root:

```bash
python src/evaluator.py
python -m unittest discover -s tests -v
```

These commands need no API key or network for evaluation. The full test suite
also imports the generator and therefore requires its installed OpenAI package.

The review plan preserves source fingerprints. A display-label repair to
`rubric.json` is recorded in its metadata; scoring anchors, IDs, weights and
the rubric document were unchanged. Evaluation artifacts contain the same
five criterion IDs and rubric version for all three strategies.
