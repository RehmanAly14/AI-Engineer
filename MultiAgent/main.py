"""
Simple Multi-Agent System
=========================

    User ──► Manager Agent ──┬──► Search Agent (Tavily web search tool)
                │            └──► Math Agent   (calculator tool)
                ▼
          notebook.json  (record of every request)

1. The Manager reads the user request and, using its system prompt,
   makes a plan: one or more steps, each handled by a worker agent.
   e.g. "10% of Pakistan's population?" -> search first, then math.
2. Each worker agent uses its own tool. The result of every step is
   passed to the next step, so math can use numbers found by search.
3. If there were several steps, the Manager combines the results
   into one final answer.
4. The Manager writes a record of the request into the notebook.

All three agents use Groq as the LLM.
"""

import ast
import json
import operator as op
import os
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

load_dotenv()

groq = Groq(api_key=os.getenv("Groq_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MODEL = "openai/gpt-oss-120b"
NOTEBOOK_FILE = os.path.join(os.path.dirname(__file__), "notebook.json")


# --- Tools ---------------------------------------------------------------

def web_search(query: str) -> str:
    result = tavily.search(query=query, max_results=5)
    results = result.get("results", [])
    if not results:
        return "No results found."
    lines = [f"{r['title']}: {r['content']} ({r['url']})" for r in results]
    return "\n".join(lines)


_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_eval_node(tree.body))
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


# --- Tool schemas for the LLM --------------------------------------------

search_tool = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for up-to-date information and return a summary of results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web.",
                }
            },
            "required": ["query"],
        },
    },
}

calculator_tool = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate a basic math expression (+, -, *, /, **, %, //) and return the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression to evaluate, e.g. '2*2' or '(3+5)/4'.",
                }
            },
            "required": ["expression"],
        },
    },
}


# --- Worker agent (shared loop) ------------------------------------------

def run_worker(system_prompt: str, task: str, tools: list, functions: dict, max_steps: int = 5) -> str:
    """Ask the LLM, run any tools it calls, repeat until it gives a final answer."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    for _ in range(max_steps):
        response = groq.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"   [tool] {name}({args})")
            result = functions[name](**args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": result,
                }
            )

    return "Sorry, I could not finish this task."


# --- Worker agent 1: Search Agent ----------------------------------------

SEARCH_PROMPT = """You are a Search Agent.
Always use the web_search tool to find current information before answering.
Give a short, clear answer and mention the source URLs you used."""


def search_agent(task: str) -> str:
    return run_worker(SEARCH_PROMPT, task, [search_tool], {"web_search": web_search})


# --- Worker agent 2: Math Agent ------------------------------------------

MATH_PROMPT = """You are a Math Agent.
Always use the calculate tool for arithmetic, never compute in your head.
Convert word problems into a math expression, call the tool, then give the final answer briefly."""


def math_agent(task: str) -> str:
    return run_worker(MATH_PROMPT, task, [calculator_tool], {"calculate": calculate})


WORKERS = {
    "search": search_agent,
    "math": math_agent,
}


# --- Notebook (the Manager's record book) --------------------------------

class Notebook:
    def __init__(self, path: str = NOTEBOOK_FILE):
        self.path = path

    def read(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write(self, request: str, steps: list, reason: str, answer: str) -> dict:
        records = self.read()
        record = {
            "id": len(records) + 1,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "request": request,
            "routed_to": [step["agent"] for step in steps],
            "reason": reason,
            "steps": steps,
            "answer": answer,
        }
        records.append(record)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        return record

    def show(self):
        records = self.read()
        if not records:
            print("Notebook is empty.")
            return
        for r in records:
            route = r["routed_to"]
            if isinstance(route, list):  # old records saved a single agent as a string
                route = " -> ".join(route) or "none"
            print(f"#{r['id']} [{r['time']}] -> {route}: {r['request']}")


# --- Manager agent -------------------------------------------------------

MANAGER_PROMPT = """You are the Manager of a team of agents. You do NOT answer questions yourself.
Your only job is to make a plan: which agent(s) should handle the user's request, and in what order.

Agents:
- "search": finds information on the internet (news, facts, people, places, weather, prices, anything current).
- "math": does math calculations (arithmetic, percentages, word problems with numbers).

Rules:
- Use one step if one agent is enough.
- Use several steps if the request needs both, e.g. "What is 10% of Pakistan's population?"
  -> step 1: search for Pakistan's population, step 2: math to calculate 10% of it.
- Later steps automatically receive the results of earlier steps, so just describe what to do.
- For greetings or small talk that need no agent, return an empty list of steps.

Reply ONLY with JSON in this format:
{"steps": [{"agent": "search" | "math", "task": "<clear instruction for the agent>"}], "reason": "<one short sentence>"}"""

COMBINE_PROMPT = """You are the Manager. Your agents have finished their steps.
Using ONLY their results, write one short, clear final answer to the user's request."""


def manager_plan(request: str) -> dict:
    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": MANAGER_PROMPT},
            {"role": "user", "content": request},
        ],
        response_format={"type": "json_object"},
    )
    plan = json.loads(response.choices[0].message.content)
    # Keep only valid steps
    plan["steps"] = [
        {"agent": step["agent"], "task": step.get("task") or request}
        for step in plan.get("steps", [])
        if step.get("agent") in WORKERS
    ]
    plan.setdefault("reason", "")
    return plan


def manager_combine(request: str, steps: list) -> str:
    results = "\n\n".join(
        f"Step {i} ({step['agent']} agent): {step['task']}\nResult: {step['result']}"
        for i, step in enumerate(steps, start=1)
    )
    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": COMBINE_PROMPT},
            {"role": "user", "content": f"Request: {request}\n\n{results}"},
        ],
    )
    return response.choices[0].message.content


def manager(request: str, notebook: Notebook | None = None) -> dict:
    notebook = notebook or Notebook()

    plan = manager_plan(request)
    steps = plan["steps"]
    route = " -> ".join(step["agent"] for step in steps) or "none"
    print(f"[manager] plan: {route} ({plan['reason']})")

    if not steps:
        answer = "Hi! I can search the web or solve math problems for you. What would you like?"
        return notebook.write(request, steps, plan["reason"], answer)

    # Run each step in order, giving every agent the results of earlier steps
    previous = ""
    for i, step in enumerate(steps, start=1):
        print(f"[manager] step {i}: {step['agent']} agent -> {step['task']}")
        task = step["task"]
        if previous:
            task += f"\n\nResults from earlier steps:\n{previous}"
        step["result"] = WORKERS[step["agent"]](task)
        previous += f"\nStep {i} ({step['agent']}): {step['result']}"

    if len(steps) == 1:
        answer = steps[0]["result"]
    else:
        answer = manager_combine(request, steps)

    return notebook.write(request, steps, plan["reason"], answer)


# --- Run -----------------------------------------------------------------

def main():
    notebook = Notebook()
    print("Multi-Agent System (type 'notebook' to see records, 'exit' to quit)")
    while True:
        request = input("\nYou: ").strip()
        if not request:
            continue
        if request.lower() in ("exit", "quit"):
            break
        if request.lower() == "notebook":
            notebook.show()
            continue
        record = manager(request, notebook)
        print(f"\nAnswer: {record['answer']}")


if __name__ == "__main__":
    main()
