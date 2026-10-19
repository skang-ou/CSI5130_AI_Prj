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
The project will focus on generating test cases in **Given-When-Then**
format and evaluating the quality of the generated results using
different prompting strategies.

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

A secondary question is whether different prompting strategies improve
the quality and consistency of generated test cases.

## Proposed Method

The project will develop a Python-based prototype that accepts a
natural-language software requirement and uses an LLM to generate one or
more structured test cases.

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

### Prompting Strategies

The project will compare several prompting strategies:

1.  **Basic / Zero-Shot Prompt** --- directly ask the LLM to generate a
    test case.
2.  **Structured Prompt** --- explicitly ask the LLM to identify
    preconditions, triggers, expected results, and boundary conditions.
3.  **Few-Shot Prompt** --- provide example requirements and
    corresponding test cases before asking the model to process a new
    requirement.

Generated test cases will be compared with manually prepared reference
test cases.

### Evaluation Criteria

The evaluation may include:

-   Correct identification of preconditions
-   Correct identification of triggering conditions
-   Correct expected system behavior
-   Coverage of relevant boundary or negative cases
-   Clarity and testability of the generated test
-   Presence of unsupported or hallucinated behavior

The experimental results will be used to compare prompting approaches
and identify strengths and limitations of LLM-generated test cases.

## Data Sources

The project will primarily use a **synthetic dataset of embedded-system
software requirements** created specifically for this project.

The initial dataset contains 50 synthetic requirements covering
representative embedded-system behaviors such as:

-   System states and state transitions
-   Sensor values and thresholds
-   Warning and notification behavior
-   Timing conditions
-   Input/output behavior
-   Charging and energy management
-   Thermal management
-   Diagnostics and communication

Each requirement includes a manually created reference test case in
Given-When-Then format for use as a baseline during evaluation.

The project will **not use proprietary, confidential, or
company-specific software requirements or source code**.

If publicly available requirements, research papers, open-source
datasets, libraries, or models are used later, they will be documented
and properly cited in the repository and final report.

## Expected Outcome

The expected outcome is a working prototype that demonstrates how an LLM
can assist with converting software requirements into structured test
cases.

The project will also provide an experimental comparison of prompting
strategies and identify situations in which LLM-generated test cases are
useful, incomplete, or potentially unreliable.

A simple interactive demonstration may be developed so a user can enter
a requirement and view generated Given-When-Then test cases.

## Planned Technologies

-   Python
-   Large Language Model API
-   Jupyter Notebook and/or Python scripts
-   Pandas for experiment and evaluation data
-   GitHub for source control and project documentation
-   Optional lightweight UI framework for the final demo

## Repository Structure

``` text
requirement-test-generator/
├── README.md
├── data/
│   └── requirements.csv
├── src/
├── experiments/
├── results/
├── demo/
└── report/
```

## Project Status

**Current Phase:** Initial project definition and dataset preparation.

### Planned Next Steps

1.  Review and refine the synthetic requirements dataset.
2.  Define the final reference test-case format.
3.  Implement the baseline LLM test-case generator.
4.  Implement structured and few-shot prompting strategies.
5.  Finalize the evaluation rubric.
6.  Run experiments and analyze results.
7.  Develop a demonstration interface.
8.  Prepare the final report and presentation.

## Citations and Acknowledgements

References to external models, libraries, research papers, datasets, and
other resources used in this project will be documented here as the
project develops.
