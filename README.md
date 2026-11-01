# LLM-Based Software Requirement-to-Test-Case Generator for Embedded Systems

## Project Overview

Software requirements are commonly written in natural language, while
software engineers must translate those requirements into detailed and
testable test cases. This process can require significant manual effort
and may result in missed conditions, boundary cases, or inconsistent
test coverage.

This project investigates whether Large Language Models (LLMs) can
assist software engineers by automatically converting natural-language
software requirements into structured test cases for embedded systems.

The project focuses on generating test cases in **Given-When-Then**
format and experimentally comparing different prompting strategies.

## Problem Statement

Creating software test cases from requirements is an important but
time-consuming part of software development. Engineers must understand
each requirement, identify preconditions and triggering conditions,
determine the expected system behavior, and consider relevant boundary
or negative cases.

Embedded-system requirements often describe behavior that depends on
system states, sensor values, thresholds, timing conditions, and
interactions between components. Missing or incorrectly interpreting one
of these conditions can lead to incomplete test coverage.

The main research question is:

> **How effectively can Large Language Models generate structured and
> accurate test cases from natural-language software requirements for
> embedded systems?**

A secondary research question is:

> **Do structured and few-shot prompting strategies improve the quality
> and consistency of generated test cases compared with a basic
> zero-shot prompt?**

## Proposed Method

The project uses a Python-based prototype that accepts natural-language
software requirements and uses an LLM to generate structured test cases.

### Workflow

**Software Requirement → LLM Prompt → Test Case Generation → Structured
Given-When-Then Output → Evaluation**

Example input:

> When the battery state of charge (SOC) falls below 10% while the
> vehicle is in Drive, the system shall display a low-battery warning.

Example expected output:

-   **Given:** The vehicle is in Drive and battery SOC is at or above
    10%.
-   **When:** Battery SOC falls below 10%.
-   **Then:** The system displays the low-battery warning.

## Prompting Strategies

The experiment compares three prompting strategies while keeping the
requirement dataset, model, and output format consistent.

### 1. Zero-Shot Prompt

The LLM is directly asked to generate a Given-When-Then test case
without receiving example test cases.

This strategy provides the experimental baseline.

### 2. Structured Prompt

The LLM receives additional instructions for identifying:

-   Required initial states and preconditions
-   Specific triggering events or transitions
-   Expected system behavior
-   Threshold and timing conditions
-   Unsupported assumptions or behaviors that should not be introduced

The goal is to determine whether explicit reasoning structure improves
the generated test cases.

### 3. Few-Shot Prompt

The LLM is provided with several example requirement-to-test-case pairs
before processing a new requirement.

The goal is to determine whether examples improve the consistency and
quality of the generated Given-When-Then structure.

## Dataset

The project uses a **synthetic dataset of 30 embedded-system software
requirements** created specifically for this experiment.

The dataset is balanced by difficulty:

  Difficulty     Requirements
  ------------ --------------
  Easy                     10
  Medium                   10
  Hard                     10
  **Total**            **30**

The requirements cover representative embedded-system behaviors
including system states and transitions, thresholds, warnings, timing,
I/O, charging, energy management, thermal management, diagnostics,
communication, safety interlocks, and sensor plausibility.

Each requirement contains a manually prepared reference test case
consisting of `reference_given`, `reference_when`, and `reference_then`.
These references are not provided to the LLM during generation and are
used only for evaluation.

The project does **not use proprietary, confidential, or
company-specific software requirements or source code**.

## Experimental Design

The same 30 requirements will be processed using each of the three
prompting strategies.

``` text
                         30 Requirements
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
          Zero-Shot        Structured       Few-Shot
          30 Tests          30 Tests         30 Tests
              |                |                |
              +----------------+----------------+
                               |
                               v
                       90 Generated Tests
                               |
                               v
                           Evaluation
```

## Evaluation Criteria

Generated test cases will be compared with the manually prepared
reference test cases using:

1.  **Precondition Correctness**
2.  **Trigger Correctness**
3.  **Expected Behavior Correctness**
4.  **Condition / Boundary Coverage**
5.  **Unsupported Behavior / Hallucination**

The same evaluation criteria will be applied to all prompting
strategies. Quantitative results will be supplemented with qualitative
analysis of representative successful and unsuccessful generations.

## Current Experimental Results

### Zero-Shot Baseline

The initial Zero-Shot experiment has been completed using **GPT-5.6**.

**30 of 30 requirements were successfully processed.**

Initial review indicates that most generated tests correctly identify
the precondition, trigger, and expected behavior. Some multi-condition
requirements produced valid tests but placed triggering conditions in
the Given statement rather than clearly identifying the primary
transition in the When statement.

These cases will be compared with Structured and Few-Shot results to
determine whether additional prompting guidance improves test-case
structure.

No final performance conclusions will be made until all three strategies
have been evaluated using the same rubric.

### Structured Prompting

Structured Prompting has been implemented and run on the same 30 requirements
using `gpt-5.6`, the same system instruction, and the same JSON output format.
The prompt explicitly separates preconditions, triggering events, and expected
behavior, while preserving guards, thresholds, timing, and logical conditions.

- **Sample check: 4 of 4 successful** across Easy, Medium, and Hard requirements.
- **Full run: 30 of 30 successful**, saved to `results/structured_results.csv`.
- All 30 IDs match the dataset; generated fields are nonempty.
- The Zero-Shot baseline file remains unchanged.
- These checks confirm generation completion, not measured accuracy.

See `experiments/structured_run.md` for the sample selection, execution settings,
and verification record.

### Few-Shot Prompting

Few-Shot Prompting has been implemented using four independently authored
requirement/test-case demonstrations in `data/few_shot_examples.json`. They
cover threshold crossing, a guarded event with a response deadline, a sustained
condition, and an inhibited request. They are separate from the 30 evaluation
requirements and do not use their reference answers.

- **Sample check: 4 of 4 successful**, using the same sample IDs as Structured.
- **Full run: 30 of 30 successful**, saved to `results/few_shot_results.csv`.
- Same model argument (`gpt-5.6`), system instruction, API settings, and output format.
- All 30 IDs match the dataset; generated fields are nonempty.
- Both earlier result files and the evaluation dataset remain unchanged.
- Ten offline regression tests pass, including reference-answer exclusion and
  normalized overlap rejection before applying a sample limit.

**All 90 planned requirement/strategy outputs are now saved.** This confirms
generation completion, not measured accuracy. Common-rubric evaluation and
comparative analysis remain. See `experiments/few_shot_run.md` for details.

## Expected Outcome

The expected outcome is a working prototype demonstrating how an LLM can
assist with converting software requirements into structured test cases.

The project will compare Zero-Shot, Structured, and Few-Shot prompting
and identify situations in which generated test cases are accurate and
useful, as well as cases where they may be incomplete, poorly
structured, or introduce unsupported assumptions.

A simple interactive demonstration may also allow a user to enter a
requirement, select a prompting strategy, and view the generated
Given-When-Then test case.

## Technologies

-   Python
-   OpenAI LLM API
-   GPT-5.6
-   CSV-based experiment datasets
-   Python scripts for generation and evaluation
-   Git and GitHub
-   Optional Streamlit interface for the final demonstration

## Running the Generator

Run commands from the repository root using a Python environment with the
`openai` package installed. Set `OPENAI_API_KEY` privately in that environment.
Do not commit or display the key.

```bash
python src/generator.py --strategy zero_shot
python src/generator.py --strategy structured
python src/generator.py --strategy few_shot
```

The default model remains `gpt-5.6`. All three strategies use the same system
instruction, API call, JSON format, and requirement dataset. Only the task
prompt changes. Evaluation reference fields are excluded from all prompts. Few-Shot adds four
independently authored demonstrations from `data/few_shot_examples.json`; they
are separate from the 30 evaluation requirements. The loader rejects duplicate
examples and case/whitespace-normalized overlap with the full input dataset,
including rows outside `--limit`. This is a text-overlap safeguard, not a general
semantic similarity detector.

Without `--output`, results go to `results/<strategy>_results.csv`
according to the selected strategy.
Omitting `--strategy` preserves the Zero-Shot default. A run replaces its
output file, so use a separate path for sample runs:

```bash
python src/generator.py --strategy structured --limit 3 --output experiments/structured_quick_check.csv
python src/generator.py --strategy structured --input experiments/structured_sample_requirements.csv --output experiments/structured_sample_results.csv
python src/generator.py --strategy few_shot --input experiments/few_shot_sample_requirements.csv --output experiments/few_shot_sample_results.csv
```

The second and third commands reproduce the four-requirement sample selection
(REQ-002, REQ-018, REQ-021, REQ-030), covering all difficulty levels.
New API calls may produce different wording. API usage may incur charges.

Offline regression checks:

```bash
python -m unittest discover -s tests -v
```

## Repository Structure

``` text
requirement-test-generator/
├── README.md
├── data/
│   ├── requirements.csv
│   └── few_shot_examples.json
├── src/
│   ├── generator.py
│   └── evaluator.py          # Planned
├── experiments/
│   ├── structured_sample_requirements.csv
│   ├── structured_sample_results.csv
│   ├── structured_run.md
│   ├── few_shot_sample_requirements.csv
│   ├── few_shot_sample_results.csv
│   └── few_shot_run.md
├── results/
│   ├── zero_shot_results.csv
│   ├── structured_results.csv
│   └── few_shot_results.csv
├── demo/
└── report/
```

## Project Status

**Current Phase: Evaluation Rubric and Test-Case Evaluation**

Numbered tasks keep their original numbers when moved from Next Steps to Completed.

### Completed

-   [x] Defined the project problem and research questions
-   [x] Created the initial GitHub repository and README
-   [x] Created the synthetic embedded-system requirements dataset
-   [x] Reduced the experimental dataset to 30 requirements
-   [x] Balanced the dataset across Easy, Medium, and Hard requirements
-   [x] Created manual Given-When-Then reference test cases
-   [x] Implemented the Python LLM test-case generator
-   [x] Implemented the Zero-Shot prompting baseline
-   [x] Validated the generator using initial sample requirements
-   [x] Completed Zero-Shot generation for all 30 requirements
-   [x] Saved Zero-Shot experimental results

1.  **Implement Structured Prompting** — Completed
    -   [x] Added explicit instructions for separating preconditions,
        triggers, and expected behavior.
    -   [x] Tested on four requirements across all difficulty levels.
    -   [x] Ran all 30 requirements successfully.
    -   [x] Saved and checked `results/structured_results.csv`.
    -   [x] Passed five offline regression tests for strategy selection and prompt isolation.

2.  **Implement Few-Shot Prompting** — Completed
    -   [x] Created four independent example requirement/test-case pairs.
    -   [x] Excluded evaluation reference answers and checked demonstration overlap.
    -   [x] Tested on four sample requirements across all difficulty levels.
    -   [x] Ran all 30 requirements successfully.
    -   [x] Saved and checked `results/few_shot_results.csv`.
    -   [x] Passed ten offline regression tests across all strategies.

### Next Steps

3.  **Finalize the Evaluation Rubric**
    -   Define consistent scoring rules for all five evaluation
        criteria.
    -   Apply the same rubric to all strategies.
4.  **Evaluate the 90 Generated Test Cases**
    -   Compare generated tests with reference tests.
    -   Calculate quantitative results.
    -   Identify representative successful and unsuccessful examples.
5.  **Analyze and Visualize Results**
    -   Compare average quality scores.
    -   Analyze trigger and expected-behavior correctness.
    -   Analyze boundary/condition coverage and hallucination.
    -   Create tables and charts.
6.  **Develop the Demonstration**
    -   Create a lightweight interface for requirement input.
    -   Allow prompting-strategy selection.
    -   Display generated Given-When-Then output.
7.  **Prepare the Final Report**
    -   Document data, methods, experiments, results, limitations, and
        conclusions.
    -   Include quantitative and qualitative analysis.
8.  **Prepare the Final Presentation and Demo**
    -   Present the problem, solution, prompting strategies, results,
        and limitations.
    -   Demonstrate the working generator.

## Citations and Acknowledgements

References to external models, libraries, research papers, datasets, and
other resources used in this project will be documented here as the
project develops.

OpenAI models and APIs are used for LLM-based test-case generation.
Additional libraries, tools, and research references will be added as
they are incorporated into the project.
