# Evaluation rubric

Version: `1.0`. Finalized: November 18, 2026.

## Scope and common scoring scale

Use this rubric for every Zero-Shot, Structured, and Few-Shot output. Each strategy
has the same 30 requirements and the same five equally weighted criteria. Judge
meaning and testability, not word overlap, prompt length, or strategy name.

The authoritative specification is the original requirement. Manual reference
tests are comparison aids, not infallible answers. Accept logically valid
alternative scenarios and document reference discrepancies. Do not edit the
source requirements, references, or saved generations during evaluation.

For each criterion, assign an integer:

- **2: Fully satisfies the criterion** for the selected scenario.
- **1: Partially satisfies the criterion**; a local clarification or correction is needed.
- **0: Fails the criterion**; a material error, contradiction, or omission prevents satisfaction.

Higher is better for all five criteria, including unsupported behavior: **2 means
no unjustified behavior**. Do not reverse this criterion when computing totals.
There is no N/A score. A missing score remains `null` (unreviewed), not zero.

The rubric was finalized after generation and preliminary inspection of examples.
It is not a preregistered or independently validated instrument. Freeze this
version for the full comparison; any change requires a new version and consistent
rescoring of all affected outputs across every strategy.

## Criterion anchors

### 1. Precondition Correctness (`precondition_correctness`)

- **2:** Given states the operating mode and initial conditions needed to exercise
  the chosen scenario. The setup is compatible with the requirement and When.
- **1:** The setup is usable but incomplete or imprecise, or it places the main
  triggering event in Given while a reader can still reconstruct the scenario.
- **0:** Given contradicts an essential operating state, makes the trigger
  impossible, or provides no usable setup when one is necessary.

Score field placement here. If a required guard appears explicitly in When rather
than Given, retain credit for semantic coverage under criterion 4 but consider a
1 here when it describes a persistent precondition rather than a joint event.
An explicit, coherent joint event can legitimately belong entirely in When.

A stated initial value on the opposite side of a threshold can establish a
crossing. An inactive warning or unset fault can establish that a new activation
is observable. These are acceptable test setup choices, not automatic inventions.
Do not require the reference's exact initial value or every redundant setup detail.

### 2. Trigger Correctness (`trigger_correctness`)

- **2:** When identifies a concrete input, event, state transition, evaluation of
  an input, or elapsed condition that exercises the selected obligation. It
  preserves relevant ordering and duration. Equivalent triggers are acceptable.
- **1:** The trigger is recognizable but vague, partly misplaced in Given, or
  missing detail needed to reproduce it without changing the scenario's purpose.
- **0:** When is absent, unrelated, contradictory, or exercises a different logical
  or timing condition that cannot establish the selected obligation.

For example, receiving a charging request while locking is already successful can
be valid. "The system processes the request" is weaker when request receipt and
lock success appear only in Given. Do not require all qualifying conditions to
change at once or force the reference's event when another event is valid.

### 3. Expected Behavior Correctness (`expected_behavior_correctness`)

- **2:** Then states every observable response required for the selected scenario,
  with correct polarity, target outputs, and any response deadline.
- **1:** Then states the main response but omits part of a multi-action result,
  required data, or a response deadline, or uses an imprecise observable outcome.
- **0:** Then is absent, contradicts the required response, substitutes another
  action, or asserts an outcome the requirement does not entail for the scenario.

A correct statement of Then does not automatically receive zero because Given or
When has a separate structural defect. However, if the chosen scenario makes the
asserted response logically unsupported, that affects this criterion directly.

### 4. Condition / Boundary Coverage (`condition_boundary_coverage`)

- **2:** The complete test preserves all relevant guards, conjunctions, threshold
  comparisons, units, counts, and timing limits for the selected scenario.
- **1:** It preserves the main condition but leaves one relevant condition, bound,
  unit, or timing relationship implicit or ambiguous.
- **0:** It omits an essential combination of conditions or uses a wrong bound,
  polarity, count, unit, or duration that changes which behavior is required.

This measures **condition and boundary fidelity within one generated scenario**,
not exhaustive test-suite coverage. All prompts request one test case. Do not
penalize an otherwise complete case solely for lacking additional positive,
negative, or exact-boundary tests. A symbolic inequality can earn full credit;
a concrete boundary value is not mandatory. If the requirement has no numeric
boundary, assess its logical and state conditions. Do not infer the inverse of
a one-way implication merely to create an additional negative case.

Read conditions across all three fields. A correctly stated guard in the wrong
field can retain coverage credit while losing precondition/trigger structure
credit. Correct use of one negative boundary under an "only if" requirement can
also earn full credit for that scenario; record other untested branches separately.

### 5. Unsupported Behavior / Hallucination (`unsupported_behavior`)

- **2:** The test adds no unjustified behavior or substantive domain assumption.
  Minimal, compatible setup choices needed to observe the response are acceptable.
- **1:** It adds an unnecessary but noncontradictory setup restriction, or a vague
  incidental assumption, without materially changing the required behavior.
- **0:** It invents a material output, recovery rule, response time, numeric limit,
  prerequisite definition, or sufficient condition, or adds a contradictory setup.

For example, "system is operational" can be a minor unnecessary restriction (1).
A response deadline absent from the requirement or an invented contactor
prerequisite list is material (0). Omission alone is not hallucination; score it
under the affected correctness/coverage criterion. A 2 here does not mean the
case is otherwise complete or correct.

## Shared interpretation rules

1. Preserve comparisons exactly: `below` is `<`, `exceeds` is `>`, and `at least`
   is `>=`. "Before 500 ms" excludes 500 ms. A response "within 50 ms" includes
   the 50 ms deadline. Continuous durations and response deadlines are different.
2. Resolve necessary versus sufficient conditions from the requirement's logic.
   "Accept only if A and B" means acceptance requires both. It supports rejection
   when either fails, but does not alone guarantee acceptance when both hold.
3. Accept paraphrases, synonymous state names, equivalent units, and valid
   alternative transitions. A shorter setup is acceptable when its omitted detail
   is logically implied and no essential guard is lost.
4. Treat field separation and semantic coverage as distinct measurements. The same
   error may affect more than one criterion, but justify each affected score
   independently. Do not mechanically apply a single defect to every criterion.
5. Mark consequential ambiguity or reference problems in `reference_notes` and
   explain the chosen reading. Use that reading for all three outputs of that
   requirement. Review the original text before using cross-requirement context;
   do not silently import a neighboring requirement's assumptions.
6. A generation/parse failure or unusable empty output receives five zeros and
   retains its place in the 30-case denominator. Distinguish these failed cases
   from unreviewed cases, whose scores remain null. No such generation failures
   appear in the currently saved 90 rows.

## Dataset-specific reference cautions

These notes apply equally to every strategy and do not assign scores to outputs.

| Requirement | Consistent interpretation |
| --- | --- |
| REQ-014 | Preserve a continuously out-of-range signal for more than 2 s. Do not invent a numerical sensor range. |
| REQ-015 | Three consecutive missed CAN messages are sufficient; a third-miss event after two misses is an equivalent setup/trigger. |
| REQ-018 | Request receipt and successful locking must both hold. The text does not impose a single locking/request order. Do not force the reference's extra connector details. |
| REQ-020 | Occupied seat, unlatched belt, and speed above 10 km/h must coincide. Unlatching at qualifying speed or crossing the speed threshold while unlatched can both be valid. |
| REQ-021 | HV active is required; voltage is strictly below 300 V for at least 500 ms. |
| REQ-022 | Return to at least 300 V must occur before 500 ms. The reference adds HV active, which this requirement alone does not specify; do not require that extra guard. |
| REQ-023 | `accept => valid checksum AND age < 100 ms`. Rejection at age exactly 100 ms is supported. The manual reference's guaranteed acceptance for a valid/young command needs a sufficiency assumption; do not treat that assertion as authoritative. |
| REQ-024 | Then must include both disabling propulsion and requesting HV shutdown. |
| REQ-025 | Below -20 C is strict. The requested DC fast charging remains inhibited; do not assert behavior at exactly -20 C. |
| REQ-026 | Disabling the output must occur within 50 ms after the valid request; do not turn this into a 50 ms debounce. |
| REQ-027 | Both difference greater than 10% and persistence longer than 100 ms are strict. Do not require the reference's extra claim that both sensors are otherwise valid. |
| REQ-028 | SOC below 15%, unplugged state, and the preconditioning request must all appear. |
| REQ-029 | The active/confirmed diagnostic context and all four freeze-frame signals matter. Capture time is fault confirmation time; do not invent periodic or repeated storage behavior. |
| REQ-030 | A closing sequence is in progress, closure is unconfirmed, and any prerequisite becomes invalid. The reference invents specific prerequisite examples; use the requirement's abstract prerequisite unless an independent specification supplies them. |

## Uniform application procedure

1. Use `evaluation/review_plan.json` to enumerate all 90 requirement/strategy pairs
   under the single configuration `evaluation/rubric.json`, version `1.0`.
2. Evaluate one requirement's three outputs with the same interpretation notes.
   When feasible, conceal strategy labels and shuffle display order while retaining
   a separate mapping. Do not describe the evaluation as blinded unless it was.
3. Read the requirement first, then the generated fields, then the reference as a
   comparison aid. Never score by exact string matching alone.
4. For each pair, record the five integer scores, a rationale for each criterion,
   `reference_notes`, reviewer identity/type, review date, and rubric version.
   Quote or identify the relevant wording, especially for scores below 2.
5. Calibration examples or pilot ratings may expose inconsistent interpretations.
   Resolve them before full scoring, record changes, and rescore affected pairs
   uniformly. Record whether scores come from a human or an AI-assisted review.
6. If multiple reviewers participate, score independently first, retain original
   ratings, and record disagreements and adjudication. A single reviewer is
   permitted but must not imply inter-rater reliability has been measured.
7. Keep generation files unchanged. Store scores separately during task #4. The
   review plan assigns this rubric but deliberately contains **no quality scores**.

## Aggregation and reporting contract

The five criterion weights are all 1. For a fully scored case:

- `total_score = sum(five criterion scores)`, range 0 to 10.
- `normalized_score = total_score / 10`, range 0 to 1.
- `unsupported_behavior == 2` means no unjustified behavior. A hallucination
  indicator, if reported, is `unsupported_behavior < 2`; distinguish minor (1)
  from material (0) additions rather than treating them as equally severe.

For each strategy report the mean of each criterion (0 to 2), mean total (0 to
10), and counts at 0/1/2. Stratify by Easy/Medium/Hard, with 10 cases per stratum.
Report generation success separately. Show the number scored out of 30 and do
not publish a final complete-case average until all 30 have ratings. Nulls must
never silently become zeros or disappear from the reported completion count.

The equal-weight total is a descriptive comparison, not a validated pass/fail
threshold. Report criterion-level results and examples alongside it. For paired
strategy differences, compare scores for the same requirement IDs. Broader
claims must acknowledge the 30 synthetic requirements, one generation per pair,
and reviewer/interpretation limitations.

## Machine-readable files and next task

`rubric.json` defines the criterion IDs, weights, anchors, score direction, and
shared aggregation rules. `review_plan.json` pins source-file hashes and assigns
that same rubric to all 90 pairs, initially `pending`. These artifacts implement
the common evaluation policy; they do not assert that scoring is complete.

Task #3 is the finalized rubric and uniform review assignment. Task #4 remains
the actual semantic scoring of all 90 cases and computation of results.
