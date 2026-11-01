#!/usr/bin/env python3
"""
LLM Test-Case Generator
Project: LLM-Based Software Requirement-to-Test-Case Generator for Embedded Systems

Reads synthetic requirements from data/requirements.csv and generates Given/When/Then
tests using zero-shot, structured, or few-shot prompting. Few-Shot adds independent
demonstrations from data/few_shot_examples.json. Results use strategy-specific CSVs.

Reference test-case columns are intentionally NOT included in the prompt.
They remain independent ground truth for later evaluation.
"""

import argparse  # Parse command-line options such as the model and input file.
import csv  # Read requirement CSV files and write result CSV files.
import json  # Decode the JSON text returned by the model.
import os  # Read the API key from the process environment.
import time  # Pause between requests when a delay is requested.
from pathlib import Path  # Represent filesystem paths and create output directories.

from openai import OpenAI  # Import the OpenAI API client.


DEFAULT_MODEL = "gpt-5.6"  # Set the default model identifier; --model can override it.
DEFAULT_INPUT = Path("data/requirements.csv")  # Use this input path relative to the current working directory.
DEFAULT_OUTPUT = Path("results/zero_shot_results.csv")  # Use this output path relative to the current working directory.
# Resolve demonstration data relative to this source file rather than the shell's directory.
DEFAULT_EXAMPLES = Path(__file__).resolve().parents[1] / "data/few_shot_examples.json"

# The next three literal lines set the role, restrict input to the requirement,
# and prohibit unsupported behavior. Comments stay outside the model instructions.
SYSTEM_PROMPT = """You are a software test engineer specializing in embedded systems.
Generate a test case only from the requirement provided by the user.
Do not invent behavior that is not supported by the requirement."""

# This template requests one structured test case without worked examples (zero-shot).
# Its opening lines specify the task; Requirement: labels the {requirement} placeholder.
# Return JSON only requests machine-readable output; doubled braces escape literal
# JSON braces for str.format(). The given, when, and then lines describe each field.
# Blank lines organize the prompt, and the final triple quote ends the literal.
ZERO_SHOT_PROMPT = """Convert the following embedded-system software requirement into one
structured Given-When-Then test case.

Requirement:
{requirement}

Return JSON only, using exactly this format:
{{
  "given": "precondition(s) before the trigger occurs",
  "when": "trigger or event being tested",
  "then": "expected system behavior"
}}
"""


# Add explicit field-separation and condition-preservation rules without worked
# examples. Keep the JSON format identical to Zero-Shot for later comparison.
# These comments sit outside the string and are not sent to the model.
STRUCTURED_PROMPT = """Convert the following embedded-system software requirement into one
structured Given-When-Then test case.

Requirement:
{requirement}

Use these rules to separate the test-case fields:
1. Given: describe the initial system state and required preconditions before
   the event under test. Keep persistent guards, such as an operating mode,
   distinct from the event that triggers the required response.
2. When: describe the specific input, event, state transition, or elapsed-time
   condition under test. Do not move that event into Given and replace it
   with a vague statement such as "the system processes the request".
   If multiple events are required, preserve their relationship and ordering
   only as specified by the requirement.
3. Then: describe the observable required behavior, including every required
   output or action and any response deadline.
4. Preserve all relevant guards, logical operators, thresholds, units, and
   timing conditions. Distinguish strict from inclusive bounds, continuous
   durations from response deadlines, and necessary from sufficient conditions.
5. For an inhibition or negative requirement, exercise the prohibited request
   or event and state the required absence of the behavior. Do not infer
   behavior for other conditions that the requirement does not specify.
6. Use only supported setup conditions. Do not invent thresholds, delays,
   prerequisite lists, recovery behavior, or additional system functionality.
   Do not turn an "only if" necessary condition into a sufficient condition.
7. Return one test case, not a suite. Check that its Given, When, and Then
   describe a coherent scenario without contradicting the requirement.

Return JSON only, using exactly this format:
{{
  "given": "precondition(s) before the trigger occurs",
  "when": "trigger or event being tested",
  "then": "expected system behavior"
}}
"""

# Few-Shot adds independent demonstrations to the baseline task and JSON format.
# Unlike Structured, it does not add the explicit seven-rule instruction block.
FEW_SHOT_PROMPT = """Use the following independent examples as demonstrations of the output format.
Generate an answer only for the target requirement after the examples.
The examples are not additional requirements to test.

{examples}

Target task:
""" + ZERO_SHOT_PROMPT

# Map CLI strategy names to prompt templates; reuse the same API call and parser.
PROMPT_TEMPLATES = {
    "zero_shot": ZERO_SHOT_PROMPT,
    "structured": STRUCTURED_PROMPT,
    "few_shot": FEW_SHOT_PROMPT,
}


def parse_args():  # Define the command-line interface and return the selected options.
    parser = argparse.ArgumentParser(  # Create the parser that also supplies automatic --help output.
        description="Generate Given-When-Then tests with zero-shot, structured, or few-shot prompting."
    )  # Finish this function call.
    parser.add_argument(  # Register the following command-line option.
        "--input",  # Name the command-line option being registered.
        type=Path,  # Convert the option value to this Python type.
        default=DEFAULT_INPUT,  # Use this value when the option is omitted.
        help="Input CSV file (default: data/requirements.csv)",  # Describe this option in --help output.
    )  # Finish this function call.
    parser.add_argument(  # Register the following command-line option.
        "--output",  # Name the command-line option being registered.
        type=Path,  # Convert the option value to this Python type.
        default=None,  # Resolve the default path after the strategy is known.
        help="Output CSV (default: results/<strategy>_results.csv).",
    )  # Finish this function call.
    parser.add_argument(  # Register the following command-line option.
        "--model",  # Name the command-line option being registered.
        default=DEFAULT_MODEL,  # Use this value when the option is omitted.
        help=f"OpenAI model name (default: {DEFAULT_MODEL})",  # Describe this option in --help output.
    )  # Finish this function call.
    parser.add_argument(  # Register the following command-line option.
        "--limit",  # Name the command-line option being registered.
        type=int,  # Convert the option value to this Python type.
        default=None,  # Use this value when the option is omitted.
        help="Optional number of requirements to process for testing.",  # Describe this option in --help output.
    )  # Finish this function call.
    parser.add_argument(  # Register the following command-line option.
        "--delay",  # Name the command-line option being registered.
        type=float,  # Convert the option value to this Python type.
        default=0.0,  # Use this value when the option is omitted.
        help="Optional delay in seconds between API calls.",  # Describe this option in --help output.
    )  # Finish this function call.
    # Restrict selection to implemented strategies and preserve the baseline default.
    parser.add_argument(
        "--strategy",
        choices=tuple(PROMPT_TEMPLATES),
        default="zero_shot",
        help="Prompting strategy (default: zero_shot).",
    )
    args = parser.parse_args()
    # Reject invalid sample sizes and delays before making any API calls.
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.delay < 0:
        parser.error("--delay must not be negative")
    # Separate default result files keep strategy runs from replacing each other.
    # An explicit --output path takes precedence, including for small sample runs.
    if args.output is None:
        args.output = (
            DEFAULT_OUTPUT if args.strategy == "zero_shot"
            else Path(f"results/{args.strategy}_results.csv")
        )
    return args


def load_requirements(csv_path: Path):  # Read requirement rows and validate the required CSV columns.
    if not csv_path.exists():  # Reject a missing input file before trying to open it.
        raise FileNotFoundError(f"Input file not found: {csv_path}")  # Report which input path could not be found.

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:  # Open the CSV, accepting a UTF-8 BOM and letting csv handle newlines.
        rows = list(csv.DictReader(f))  # Load rows as dictionaries keyed by the header names.

    if not rows:  # Check whether the input contains any data rows.
        raise ValueError("Input CSV contains no requirements.")  # Stop when there are no requirements to process.

    required_columns = {"requirement_id", "requirement"}  # Specify the two mandatory input column names.
    missing = required_columns - set(rows[0].keys())  # Find mandatory column names absent from the CSV header.
    if missing:  # Reject input whose header lacks mandatory columns.
        raise ValueError(  # Raise a validation error using the message below.
            "Input CSV is missing required column(s): " + ", ".join(sorted(missing))  # Build a readable, consistently ordered list of missing columns.
        )  # Finish this function call.

    return rows  # Return the validated list of requirement dictionaries.


def extract_json(text: str):  # Decode model output and normalize the three test-case fields.
    """Parse JSON output, with a small fallback for accidental code fences."""
    cleaned = text.strip()  # Remove surrounding whitespace from the response.

    if cleaned.startswith("```"):  # Detect an accidental Markdown code fence.
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()  # Remove JSON fence markers and trim the remaining text.

    try:  # Attempt the following operations and handle failures below.
        data = json.loads(cleaned)  # Attempt to decode the entire cleaned response as JSON.
    except json.JSONDecodeError:  # Try extracting a JSON object if whole-response decoding fails.
        start = cleaned.find("{")  # Locate the first opening object brace.
        end = cleaned.rfind("}")  # Locate the last closing object brace.
        if start == -1 or end == -1:  # Check whether either object boundary is missing.
            raise ValueError(f"Model did not return valid JSON:\n{text}")  # Report the original response when no object can be located.
        data = json.loads(cleaned[start : end + 1])  # Decode the brace-delimited substring, including the closing brace.

    for field in ("given", "when", "then"):  # Check each required test-case field.
        if field not in data:  # Detect a missing required field.
            raise ValueError(f"Model JSON is missing '{field}': {data}")  # Report the missing field and the decoded response.

    return {  # Return only the normalized test-case fields.
        "given": str(data["given"]).strip(),  # Convert preconditions to text and remove surrounding whitespace.
        "when": str(data["when"]).strip(),  # Convert the trigger to text and remove surrounding whitespace.
        "then": str(data["then"]).strip(),  # Convert the expected behavior to text and remove surrounding whitespace.
    }  # Finish this dictionary.


def load_few_shot_examples(path: Path = DEFAULT_EXAMPLES, evaluated_requirements=()):
    """Load separate demonstrations and reject exact normalized dataset overlap."""
    # Read independently authored examples, never evaluation CSV reference columns.
    examples = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(examples, list) or not examples:
        raise ValueError("Few-Shot examples must be a nonempty JSON list.")

    # Case and whitespace changes must not bypass the answer-leakage check.
    normalize = lambda text: " ".join(text.casefold().split())
    excluded = {normalize(text) for text in evaluated_requirements}
    seen = set()  # Track demonstration requirements already encountered in this file.
    for example in examples:
        if not isinstance(example, dict):
            raise ValueError("Each Few-Shot example must be a JSON object.")
        # Validate both the example input and all three answer fields before formatting.
        for field in ("requirement", "given", "when", "then"):
            if not isinstance(example.get(field), str) or not example[field].strip():
                raise ValueError(f"Few-Shot example needs nonempty text for '{field}'.")
        normalized = normalize(example["requirement"])
        # Exact normalized overlap is rejected; this does not detect semantic paraphrases.
        if normalized in excluded:
            raise ValueError("Few-Shot examples overlap with evaluation requirements.")
        if normalized in seen:
            raise ValueError("Few-Shot examples contain duplicate requirements.")
        seen.add(normalized)
    return examples


def generate_test_case(client: OpenAI, model: str, requirement: str, strategy: str = "zero_shot", examples=None):
    # Existing callers that omit strategy continue using the original Zero-Shot prompt.
    # Only target text and, for Few-Shot, independent demonstrations enter the prompt.
    # Evaluation reference columns never enter any prompt.
    if strategy == "few_shot":
        # main() validates the fixed examples against the entire input dataset first.
        # Direct callers still get an overlap check against their target requirement.
        if examples is None:
            examples = load_few_shot_examples(evaluated_requirements=[requirement])
        if any(" ".join(e["requirement"].casefold().split()) == " ".join(requirement.casefold().split()) for e in examples):
            raise ValueError("Few-Shot examples overlap with the target requirement.")
        # Preserve file order so every target receives the same demonstrations.
        # Serialize only answer fields; example IDs are bookkeeping, not model inputs.
        demonstrations = "\n\n".join(
            f"Example {index}\nRequirement:\n{example['requirement']}\nOutput:\n"
            + json.dumps({key: example[key] for key in ("given", "when", "then")}, ensure_ascii=False)
            for index, example in enumerate(examples, start=1)
        )
        # Substitute the examples and target once; JSON braces inside examples stay literal.
        prompt = FEW_SHOT_PROMPT.format(requirement=requirement, examples=demonstrations)
    else:
        # Keep earlier strategy prompts unchanged for a consistent experimental baseline.
        prompt = PROMPT_TEMPLATES[strategy].format(requirement=requirement)

    response = client.responses.create(  # Send a request to the OpenAI Responses API.
        model=model,  # Select the model supplied by the caller.
        instructions=SYSTEM_PROMPT,  # Supply the test-engineer role and behavior constraints.
        input=prompt,  # Supply the requirement and requested JSON format.
    )  # Finish this function call.

    return extract_json(response.output_text)  # Parse the response text into a Given/When/Then dictionary.


def save_results(results, output_path: Path):  # Write all accumulated result rows to a CSV file.
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Create missing output directories and accept existing directories.

    fieldnames = [  # Define output columns in their written order.
        "requirement_id",  # Source requirement identifier.
        "category",  # Optional source category.
        "difficulty",  # Optional source difficulty.
        "requirement",  # Original requirement text.
        "generated_given",  # Generated preconditions.
        "generated_when",  # Generated trigger or event.
        "generated_then",  # Generated expected behavior.
        "model",  # Model used for generation.
        "prompt_strategy",  # Prompting strategy label.
        "status",  # Generation outcome.
        "error",  # Failure message, if any.
    ]  # Finish the column list.

    with output_path.open("w", encoding="utf-8", newline="") as f:  # Replace the output CSV using UTF-8 and csv-managed newlines.
        writer = csv.DictWriter(f, fieldnames=fieldnames)  # Create a dictionary-based CSV writer with the selected columns.
        writer.writeheader()  # Write the column names as the first CSV row.
        writer.writerows(results)  # Write every accumulated result dictionary.


def main():  # Coordinate argument parsing, generation, saving, and reporting.
    args = parse_args()  # Read user-selected command-line settings.

    if not os.getenv("OPENAI_API_KEY"):  # Require a nonempty API-key environment variable.
        raise EnvironmentError(  # Stop with setup instructions when the API key is missing.
            "OPENAI_API_KEY is not set.\n"  # Build the API-key setup error message.
            "Set your API key as an environment variable before running this program."  # Build the API-key setup error message.
        )  # Finish this function call.

    client = OpenAI()  # Create an API client using environment-based configuration.
    requirements = load_requirements(args.input)  # Load and validate the selected input CSV.

    # Validate before applying --limit so held-out rows cannot become demonstrations.
    # Only the requirement column participates; reference answers never enter prompts.
    # Load once per Few-Shot batch and reuse the validated list for every target.
    examples = (
        load_few_shot_examples(evaluated_requirements=[row["requirement"] for row in requirements])
        if args.strategy == "few_shot" else None
    )

    if args.limit is not None:  # Apply a row limit only when the option was supplied.
        requirements = requirements[: args.limit]  # Keep the slice selected by the limit using Python slicing rules.

    results = []  # Collect both successful and failed generation records.
    total = len(requirements)  # Count the selected requirements for progress and summary reporting.

    print(f"Loaded {total} requirement(s) from {args.input}")  # Display progress, configuration, or a summary in the terminal.
    print(f"Model: {args.model}")  # Display progress, configuration, or a summary in the terminal.
    print(f"Prompt strategy: {args.strategy}")
    print("-" * 60)  # Display progress, configuration, or a summary in the terminal.

    for index, row in enumerate(requirements, start=1):  # Process each requirement with a one-based progress counter.
        req_id = row["requirement_id"]  # Read the identifier used to link results to the source requirement.
        requirement = row["requirement"]  # Read the requirement text that will be sent to the model.

        print(f"[{index}/{total}] Generating test case for {req_id}...")  # Display progress, configuration, or a summary in the terminal.

        result_row = {  # Initialize a result record before attempting generation.
            "requirement_id": req_id,  # Source requirement identifier; initialize or copy this output field.
            "category": row.get("category", ""),  # Optional source category; initialize or copy this output field.
            "difficulty": row.get("difficulty", ""),  # Optional source difficulty; initialize or copy this output field.
            "requirement": requirement,  # Original requirement text; initialize or copy this output field.
            "generated_given": "",  # Generated preconditions; initialize or copy this output field.
            "generated_when": "",  # Generated trigger or event; initialize or copy this output field.
            "generated_then": "",  # Generated expected behavior; initialize or copy this output field.
            "model": args.model,  # Model used for generation; initialize or copy this output field.
            "prompt_strategy": args.strategy,  # Record which prompt produced this row for evaluation.
            "status": "",  # Generation outcome; initialize or copy this output field.
            "error": "",  # Failure message, if any; initialize or copy this output field.
        }  # Finish this dictionary.

        try:  # Attempt the following operations and handle failures below.
            # Apply the selected prompt while sharing model settings and output parsing.
            generated = generate_test_case(client, args.model, requirement, args.strategy, examples=examples)
            result_row["generated_given"] = generated["given"]  # Store the generated preconditions.
            result_row["generated_when"] = generated["when"]  # Store the generated trigger or event.
            result_row["generated_then"] = generated["then"]  # Store the generated expected behavior.
            result_row["status"] = "success"  # Mark this requirement as successfully processed.

        except Exception as exc:  # Record a per-requirement failure so later requirements can continue.
            result_row["status"] = "error"  # Mark this requirement as failed.
            result_row["error"] = str(exc)  # Preserve the exception message in the output record.
            print(f"  ERROR: {exc}")  # Display progress, configuration, or a summary in the terminal.

        results.append(result_row)  # Keep the record regardless of success or failure.

        # Save after every requirement so progress is preserved if execution stops.
        save_results(results, args.output)  # Checkpoint all results so far by rewriting the output CSV.

        if args.delay > 0 and index < total:  # Pause only for a positive delay when another requirement remains.
            time.sleep(args.delay)  # Wait the requested number of seconds before the next requirement.

    successful = sum(r["status"] == "success" for r in results)  # Count successful rows by summing Boolean comparisons.
    failed = total - successful  # Count all records that were not marked successful.

    print("-" * 60)  # Display progress, configuration, or a summary in the terminal.
    print("Generation complete.")  # Display progress, configuration, or a summary in the terminal.
    print(f"Successful: {successful}")  # Display progress, configuration, or a summary in the terminal.
    print(f"Failed:     {failed}")  # Display progress, configuration, or a summary in the terminal.
    print(f"Results:    {args.output}")  # Display progress, configuration, or a summary in the terminal.


if __name__ == "__main__":  # Run the program only when executed directly, rather than imported.
    main()  # Start the command-line workflow.
