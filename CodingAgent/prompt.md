# Build a Simple CLI Coding Agent for Bug Fixing

## Project Goal

Build a simple, beginner-friendly coding agent that can identify and fix small bugs in C++ source files using an LLM and a set of custom tools.

The agent should accept a bug description in plain English through the CLI, inspect the source code, identify the relevant lines, and attempt to fix the bug automatically.

Keep the implementation simple and easy to understand. Do not use LangGraph or other agent orchestration frameworks.

## 1. Technology Stack

- **Language:** Python
- **LLM Provider:** Groq
- **Model:** `openai/gpt-oss-120b`
- **API Key:** Already available in the project's `.env` file.
- **Environment:** Use the existing project environment and dependencies where possible.

Load the Groq API key securely from `.env`. Never hardcode or print the API key.

Use a straightforward tool-calling loop with the Groq API. Prefer the official Groq Python SDK and its supported tool-calling interface.

## 2. Agent Workflow

When I run the agent:

1. Display a welcome message and ask me to describe the bug in plain English.
2. Read the target C++ source file.
3. Send the bug description and relevant source context to the LLM.
4. Allow the LLM to call the available tools to investigate the bug.
5. Have the LLM propose and apply a minimal fix using the replacement tool.
6. Verify that the requested modification was actually applied.
7. Allow the LLM to inspect the updated code and determine whether another correction is needed.
8. Stop when the LLM confirms the bug is fixed or the maximum retry limit is reached.

The agent should operate on the same C++ file every time unless explicitly configured otherwise.

## 3. Custom Tools

Implement the following tools as separate, clearly named Python functions.

### Tool 1: Search Files

**Purpose:** Help the LLM identify files that are relevant to the reported bug.

- Search the project directory for relevant source files.
- Exclude directories such as `.git`, `.venv`, `venv`, `node_modules`, and build directories.
- Return matching file paths with short explanations of their relevance.
- Initially, the agent will only need to work with the prepared C++ file.

### Tool 2: Search Within a File

**Purpose:** Find relevant code and return its line numbers and surrounding context.

Inputs:
- File path
- Search query or code pattern
- Optional context-line count

Outputs:
- Matching line numbers
- Matching source lines
- A few surrounding lines for context

Use 1-based line numbers. Clearly distinguish the matching line from surrounding context.

### Tool 3: Replace Code

**Purpose:** Apply a minimal, targeted modification to the source file.

Inputs:
- File path
- Exact original code
- Replacement code

Requirements:
- Only modify files inside the configured project directory.
- Confirm that the original code exists before replacing it.
- Require exactly one match to avoid accidental multiple replacements.
- If the original code is missing or ambiguous, return an error without modifying the file.
- After replacement, return a clear success or failure message.
- Do not allow arbitrary shell commands or unrestricted file-system access.

## 4. Retry and Failure Handling

Set the maximum number of repair attempts to **3**.

- Each repair attempt should involve inspecting the code and applying a proposed fix.
- If a tool call fails, provide the error to the LLM so it can recover within the retry limit.
- Do not retry indefinitely.
- If the agent cannot resolve the bug within 3 attempts, print:

`Unable to fix the bug within the maximum of 3 attempts.`

- If the agent successfully fixes the bug, print a clear success message and summarize the changes.

Keep tool-call limits and repair-attempt limits separate if necessary, so the agent cannot get stuck repeatedly calling tools without making progress.

## 5. CLI Logging

I want to understand the entire agent workflow.

Print clear, readable messages whenever:

- The agent starts.
- The bug description is received.
- The LLM is called.
- A tool is requested.
- A tool starts executing.
- A tool returns its result.
- A code modification is applied.
- A repair attempt begins or ends.
- The agent succeeds or reaches the retry limit.

Example output:

```text
========================================
       SIMPLE C++ CODING AGENT
========================================

Describe the bug:
> The program incorrectly calculates the average.

[AGENT] Starting repair attempt 1/3
[LLM] Sending bug description and source context...
[TOOL] search_files
[TOOL] search_in_file
[TOOL] replace_code
[TOOL RESULT] Replacement successful.
[AGENT] Checking the updated source...
[SUCCESS] Bug fix completed.
```

Do not print API keys, secrets, or unnecessary internal reasoning. Print concise explanations of actions and tool results instead.

## 6. C++ Test File

Create a simple file named `main.cpp` containing clean, working C++ boilerplate.

Requirements:
- Include a `main()` function.
- Include a few simple functions that perform basic operations.
- Keep the code easy to understand.
- Do not introduce any bugs intentionally.
- Do not write test cases or a testing framework.

I will manually introduce a bug into this file and then run the agent to see whether it can identify and fix it.


## 7. Implementation Requirements

- Provide complete, runnable code for every file.
- Explain the purpose of each file briefly.
- Include the required dependencies in `requirements.txt`.
- Give me the exact commands to install dependencies and run the agent on Windows PowerShell.
- Keep functions small and readable.
- Add basic error handling for API failures, invalid tool arguments, missing files, and failed replacements.
- Do not implement automated tests yet.
- Do not introduce unnecessary frameworks, abstractions, or features.

## Expected Result

When I run the agent, it should ask me to describe a bug, investigate the C++ source using its tools, apply a minimal fix, and report whether it succeeded within 3 repair attempts.

If any requirement is unclear, ask me before making major assumptions.