"""Simple CLI coding agent that fixes bugs in a C++ file using Groq tool calling."""

import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq, GroqError

from tools import PROJECT_DIR, TOOL_SCHEMAS, read_source, resolve_project_path, run_tool

MODEL = "openai/gpt-oss-120b"
TARGET_FILE = "main.cpp"
MAX_ATTEMPTS = 3
MAX_TOOL_CALLS_PER_ATTEMPT = 8

SYSTEM_PROMPT = f"""You are a careful C++ bug-fixing agent working on the file '{TARGET_FILE}'.

You have three tools:
- search_files: find relevant source files.
- search_in_file: locate code and get exact 1-based line numbers.
- replace_code: apply a fix by replacing one exact, unique code snippet.

Rules:
- Make the smallest change that fixes the described bug. Do not refactor or restyle.
- Copy original_code exactly from the file (same indentation, no line numbers).
- If a tool returns an error, read it and try again with corrected arguments.
- When you have applied your fix, stop calling tools and briefly describe what you changed."""

VERIFY_PROMPT = """Here is the updated source of {file}:

{source}

Does this code now fix the reported bug without introducing new problems?
Answer on the first line with exactly FIXED or NOT_FIXED, then one or two sentences explaining why."""


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


def numbered_source(file_path: str) -> str:
    lines = read_source(resolve_project_path(file_path))[0].split("\n")
    return "\n".join(f"{i:4d} | {line}" for i, line in enumerate(lines, start=1))


def load_client() -> Groq:
    load_dotenv(PROJECT_DIR / ".env")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq_API_KEY")
    if not api_key:
        log("ERROR", "GROQ_API_KEY not found in .env.")
        sys.exit(1)
    return Groq(api_key=api_key)


def call_llm(client: Groq, messages: list, use_tools: bool = True):
    """Call the model once. Returns the assistant message, or None on API failure."""
    log("LLM", "Calling the model...")
    options = {"tools": TOOL_SCHEMAS, "tool_choice": "auto"} if use_tools else {}
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2,
            **options,
        )
    except GroqError as e:
        log("ERROR", f"API request failed: {e}")
        return None
    return response.choices[0].message


def assistant_message_dict(message) -> dict:
    """Convert the SDK message into a plain dict we can send back in the history."""
    entry = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        entry["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in message.tool_calls
        ]
    return entry


def execute_tool_call(call, changes: list) -> str:
    """Run one requested tool, log it, and record successful replacements."""
    name = call.function.name
    log("TOOL", f"LLM requested: {name}")
    try:
        args = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        result = "Error: tool arguments were not valid JSON."
        log("TOOL RESULT", result)
        return result

    shown_args = {k: v for k, v in args.items() if k not in ("original_code", "replacement_code")}
    log("TOOL", f"Executing {name}({shown_args})")
    ok, result = run_tool(name, args)

    first_line = result.splitlines()[0] if result else "(empty result)"
    log("TOOL RESULT", first_line)
    if name == "replace_code" and ok:
        log("CHANGE", f"Applied: {result}")
        changes.append((args["original_code"], args["replacement_code"], result))
    return result


def run_attempt(client: Groq, messages: list, changes: list) -> bool:
    """Let the LLM investigate and fix. Returns True if it applied at least one change."""
    changes_before = len(changes)
    tool_calls_used = 0

    while True:
        message = call_llm(client, messages)
        if message is None:
            return False
        messages.append(assistant_message_dict(message))

        if not message.tool_calls:
            if message.content:
                log("LLM", message.content.strip().splitlines()[0])
            break

        for call in message.tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS_PER_ATTEMPT:
                result = "Error: tool-call limit for this attempt reached."
                log("AGENT", "Tool-call limit reached for this attempt.")
            else:
                result = execute_tool_call(call, changes)
            tool_calls_used += 1
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        if tool_calls_used >= MAX_TOOL_CALLS_PER_ATTEMPT:
            break

    return len(changes) > changes_before


def verify_fix(client: Groq, messages: list) -> bool:
    """Show the LLM the updated file and ask whether the bug is fixed."""
    log("AGENT", "Checking the updated source...")
    messages.append({
        "role": "user",
        "content": VERIFY_PROMPT.format(file=TARGET_FILE, source=numbered_source(TARGET_FILE)),
    })
    message = call_llm(client, messages, use_tools=False)
    if message is None:
        return False
    answer = (message.content or "").strip()
    messages.append({"role": "assistant", "content": answer})
    log("LLM", answer.replace("\n", " "))
    return answer.upper().startswith("FIXED")


def print_summary(changes: list) -> None:
    print("\nSummary of changes:")
    for original, replacement, result in changes:
        print(f"  {result}")
        print("  - " + original.strip().replace("\n", "\n  - "))
        print("  + " + replacement.strip().replace("\n", "\n  + "))


def main() -> None:
    print("=" * 40)
    print("       SIMPLE C++ CODING AGENT")
    print("=" * 40)
    log("AGENT", f"Started. Target file: {TARGET_FILE}")

    try:
        source = numbered_source(TARGET_FILE)
    except (ValueError, OSError) as e:
        log("ERROR", str(e))
        sys.exit(1)

    client = load_client()

    bug = input("\nDescribe the bug:\n> ").strip()
    if not bug:
        log("ERROR", "No bug description given.")
        sys.exit(1)
    log("AGENT", "Bug description received.")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Bug report: {bug}\n\nCurrent source of {TARGET_FILE}:\n\n{source}"},
    ]
    changes = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print()
        log("AGENT", f"Starting repair attempt {attempt}/{MAX_ATTEMPTS}")
        applied = run_attempt(client, messages, changes)

        if applied and verify_fix(client, messages):
            log("AGENT", f"Repair attempt {attempt} ended: bug fixed.")
            log("SUCCESS", "Bug fix completed.")
            print_summary(changes)
            return

        reason = "the fix was not confirmed" if applied else "no change was applied"
        log("AGENT", f"Repair attempt {attempt} ended: {reason}.")
        messages.append({
            "role": "user",
            "content": "The bug is not fixed yet. Inspect the current code again and apply a corrected fix.",
        })

    print()
    log("FAILED", f"Unable to fix the bug within the maximum of {MAX_ATTEMPTS} attempts.")
    if changes:
        print_summary(changes)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[AGENT] Interrupted by user.")
