r"""
Minimal LangGraph example: 3 nodes + 1 conditional edge.

Flow:
    START -> classify_number -> (conditional) -> even_branch  -> END
                                              \-> odd_branch   -> END
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class GraphState(TypedDict):
    number: int
    message: str


def classify_number(state: GraphState) -> GraphState:
    """Node 1: just logs/passes the number through."""
    print(f"[classify_number] received number: {state['number']}")
    return state


def even_branch(state: GraphState) -> GraphState:
    """Node 2: runs when the number is even."""
    state["message"] = f"{state['number']} is EVEN"
    return state


def odd_branch(state: GraphState) -> GraphState:
    """Node 3: runs when the number is odd."""
    state["message"] = f"{state['number']} is ODD"
    return state


def is_even_or_odd(state: GraphState) -> str:
    """Conditional function: decides which node to go to next."""
    return "even_branch" if state["number"] % 2 == 0 else "odd_branch"


graph_builder = StateGraph(GraphState)

graph_builder.add_node("classify_number", classify_number)
graph_builder.add_node("even_branch", even_branch)
graph_builder.add_node("odd_branch", odd_branch)

graph_builder.add_edge(START, "classify_number")

graph_builder.add_conditional_edges(
    "classify_number",
    is_even_or_odd,
    {
        "even_branch": "even_branch",
        "odd_branch": "odd_branch",
    },
)

graph_builder.add_edge("even_branch", END)
graph_builder.add_edge("odd_branch", END)

graph = graph_builder.compile()


if __name__ == "__main__":
    for n in (4, 7):
        result = graph.invoke({"number": n, "message": ""})
        print(result["message"])
