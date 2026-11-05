"""The three tools the agent can use. Each returns a plain string for the LLM."""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "out", "__pycache__", "cmake-build-debug"}
SOURCE_EXTENSIONS = {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp"}
MAX_MATCHES = 20


def resolve_project_path(file_path: str) -> Path:
    """Turn a path into an absolute path, refusing anything outside the project."""
    path = (PROJECT_DIR / file_path).resolve()
    if not path.is_relative_to(PROJECT_DIR):
        raise ValueError(f"Access denied: '{file_path}' is outside the project directory.")
    if not path.is_file():
        raise FileNotFoundError(f"File not found: '{file_path}'.")
    return path


def read_source(path: Path) -> tuple[str, str]:
    """Read a file with '\\n' line endings. Also returns the original newline style."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), newline


def write_source(path: Path, text: str, newline: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace("\n", newline))


def search_files(query: str = "") -> str:
    """Find C/C++ source files in the project, ranked by how many query words they contain."""
    words = [w.lower() for w in query.split()]
    results = []
    for path in PROJECT_DIR.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PROJECT_DIR).parts):
            continue
        if not path.is_file() or path.suffix not in SOURCE_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        hits = [w for w in words if w in text]
        reason = f"mentions: {', '.join(hits)}" if hits else "C/C++ source file"
        results.append((len(hits), path.relative_to(PROJECT_DIR).as_posix(), reason))

    if not results:
        return "No source files found in the project."
    results.sort(key=lambda r: -r[0])
    return "\n".join(f"{rel} -- {reason}" for _, rel, reason in results)


def search_in_file(file_path: str, query: str, context_lines: int = 2) -> str:
    """Return every line containing `query` (case-insensitive) with surrounding context."""
    if not query.strip():
        return "Error: query must not be empty."
    path = resolve_project_path(file_path)
    lines = read_source(path)[0].split("\n")
    context_lines = max(0, min(int(context_lines), 10))

    matches = [i for i, line in enumerate(lines) if query.lower() in line.lower()]
    if not matches:
        return f"No matches for '{query}' in {file_path}."

    blocks = []
    for i in matches[:MAX_MATCHES]:
        start, end = max(0, i - context_lines), min(len(lines), i + context_lines + 1)
        block = []
        for j in range(start, end):
            marker = ">>" if j == i else "  "
            block.append(f"{marker} {j + 1:4d} | {lines[j]}")
        blocks.append("\n".join(block))

    header = f"{len(matches)} match(es) for '{query}' in {file_path} ('>>' marks the matching line):"
    return header + "\n" + "\n---\n".join(blocks)


def replace_code(file_path: str, original_code: str, replacement_code: str) -> str:
    """Replace exactly one occurrence of `original_code`, then verify the file changed."""
    if not original_code:
        return "Error: original_code must not be empty."
    if original_code == replacement_code:
        return "Error: replacement_code is identical to original_code."

    path = resolve_project_path(file_path)
    text, newline = read_source(path)
    original_code = original_code.replace("\r\n", "\n")
    replacement_code = replacement_code.replace("\r\n", "\n")

    count = text.count(original_code)
    if count == 0:
        return "Error: original_code was not found in the file. Use search_in_file to copy the exact text."
    if count > 1:
        return f"Error: original_code matches {count} places. Include more surrounding lines so it is unique."

    line_number = text[: text.index(original_code)].count("\n") + 1
    new_text = text.replace(original_code, replacement_code, 1)
    write_source(path, new_text, newline)

    # Verify the change really landed on disk.
    if read_source(path)[0] != new_text:
        return "Error: the file could not be verified after writing. The change may not have been applied."
    return f"Replacement successful in {file_path} at line {line_number}."


TOOL_FUNCTIONS = {
    "search_files": search_files,
    "search_in_file": search_in_file,
    "replace_code": replace_code,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "List C/C++ source files in the project, ranked by how many of the query words they contain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords related to the bug, e.g. 'average sum'."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Find lines in a file containing a text pattern (case-insensitive). Returns 1-based line numbers with context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path relative to the project, e.g. 'main.cpp'."},
                    "query": {"type": "string", "description": "Text or code fragment to search for."},
                    "context_lines": {"type": "integer", "description": "Lines of context around each match (default 2)."},
                },
                "required": ["file_path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_code",
            "description": "Replace one exact, unique snippet of code in a file. Fails without changing anything if the snippet is missing or appears more than once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path relative to the project, e.g. 'main.cpp'."},
                    "original_code": {"type": "string", "description": "Exact existing code, including indentation. No line numbers."},
                    "replacement_code": {"type": "string", "description": "The corrected code that replaces it."},
                },
                "required": ["file_path", "original_code", "replacement_code"],
            },
        },
    },
]


def run_tool(name: str, args: dict) -> tuple[bool, str]:
    """Run a tool by name. Returns (ok, result_text); errors become text for the LLM."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return False, f"Error: unknown tool '{name}'."
    try:
        result = func(**args)
    except TypeError as e:
        return False, f"Error: invalid arguments for {name}: {e}"
    except (ValueError, OSError) as e:
        return False, f"Error: {e}"
    return not result.startswith("Error"), result
