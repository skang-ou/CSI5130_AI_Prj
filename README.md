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

## Repository Structure

``` text
requirement-test-generator/
├── README.md
├── data/
│   └── requirements.csv
├── src/
│   ├── generator.py
│   └── evaluator.py          # Planned
├── experiments/
├── results/
│   ├── zero_shot_results.csv
│   ├── structured_results.csv    # Planned
│   └── few_shot_results.csv      # Planned
├── demo/
└── report/
```

## Project Status

**Current Phase: Prompt Strategy Experiments**

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

### Next Steps

1.  **Implement Structured Prompting**
    -   Add explicit instructions for separating preconditions,
        triggers, and expected behavior.
    -   Test on a small number of requirements.
    -   Run all 30 requirements.
    -   Save to `results/structured_results.csv`.
2.  **Implement Few-Shot Prompting**
    -   Select representative example requirement/test-case pairs.
    -   Do not expose the reference answer for the requirement currently
        being tested.
    -   Test on sample requirements and then all 30.
    -   Save to `results/few_shot_results.csv`.
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
