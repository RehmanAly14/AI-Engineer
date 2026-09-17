"""
==================================================================
 SIMPLE RESTAURANT MANAGEMENT SYSTEM - LangGraph Learning Project
==================================================================

GOAL OF THIS FILE:
    Learn how LangGraph's core building blocks work together:
        - State            (the shared data that flows through the graph)
        - Node              (a python function that does one job)
        - Edge              (a fixed connection: "after A, always do B")
        - Conditional Edge   (a connection where a function decides "what's next")
        - START / END       (the entry and exit points of the graph)

THE WORKFLOW WE ARE BUILDING:

    START
      |
      v
     LLM  <-------------------------+
      |                             |
      | (router decides)            |
      v                             |
  take_order ----------------------->
      |
      v
     LLM  <-------------------------+
      |                             |
      v                             |
    cook ------------------------->
      |
      v
     LLM  <-------------------------+
      |                             |
      v                             |
    serve ------------------------->
      |
      v
     LLM
      |
      v (router decides "end")
     END

Notice the LOOP: take_order -> LLM -> cook -> LLM -> serve -> LLM -> END
The LLM never does the restaurant work itself. It only looks at the
state and decides which node should run next. This is why we call it
a "router".
"""

# ------------------------------------------------------------------
# 1. IMPORTS
# ------------------------------------------------------------------

import os
from typing import TypedDict, Literal

from dotenv import load_dotenv          # to read GROQ_API_KEY from .env
from pydantic import BaseModel, Field   # to force the LLM's output into a fixed shape

from langchain_groq import ChatGroq     # the Groq LLM wrapper for LangChain
from langchain_core.messages import SystemMessage, HumanMessage

from langgraph.graph import StateGraph, START, END


# ------------------------------------------------------------------
# 2. LOAD THE GROQ API KEY FROM .env
# ------------------------------------------------------------------

load_dotenv()  # reads the .env file sitting next to this file

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY not found. Add a line like GROQ_API_KEY=your_key_here "
        "to the .env file in this folder."
    )

# temperature=0 means "always pick the most likely/confident answer".
# For a router (a decision-maker, not a creative writer) we want it
# to be consistent, not creative.
llm = ChatGroq(
    model="openai/gpt-oss-120b",  # a current, solid general-purpose Groq model
    temperature=0,
    groq_api_key=groq_api_key,
)



class RestaurantState(TypedDict):
    user_message: str    # what the customer originally said, e.g. "I want a burger and a coke"
    order: dict | None   # the structured order once take_order has run, e.g. {"items": [...]}
    order_status: str    # tracks progress: "new" -> "ordered" -> "cooked" -> "served"
    current_step: str    # the name of the last routing decision (used to pick the next node)
    response: str        # the final message we show the customer, filled in by serve()


# ------------------------------------------------------------------
# 4. THE ROUTER'S STRUCTURED OUTPUT SHAPE
# ------------------------------------------------------------------
# We don't want the LLM to reply with free-form text like
# "I think we should probably cook it now!" because that's hard to
# parse reliably. Instead we force it to choose from an exact list
# of options using Pydantic + with_structured_output(). Groq's
# llama-3.3-70b-versatile supports tool-calling well, so this is
# reliable enough for a beginner project.

class RouteDecision(BaseModel):
    next_step: Literal["take_order", "cook", "serve", "end"] = Field(
        description="Which node should run next, based on the current order_status."
    )


# .with_structured_output() wraps the model so that instead of returning
# a plain chat message, it returns an already-parsed RouteDecision object.
router_llm = llm.with_structured_output(RouteDecision)


# ------------------------------------------------------------------
# 5. THE "LLM ROUTER" NODE
# ------------------------------------------------------------------
# This node does NOT take orders, cook, or serve. Its only job is to
# look at order_status and ask the LLM: "what should happen next?"

def llm_router(state: RestaurantState) -> RestaurantState:
    print("\n[LLM] Deciding next step... (current order_status =", state["order_status"], ")")

    # We tell the LLM the rules of our tiny restaurant in plain English,
    # then show it the current state so it can decide.
    system_prompt = (
        "You are a router for a restaurant workflow, not a worker. "
        "You never take orders, cook, or serve yourself - you only decide "
        "which step happens next based on order_status. Rules:\n"
        "- If order_status is 'new', the next step must be 'take_order'.\n"
        "- If order_status is 'ordered', the next step must be 'cook'.\n"
        "- If order_status is 'cooked', the next step must be 'serve'.\n"
        "- If order_status is 'served', the next step must be 'end'."
    )
    human_prompt = (
        f"user_message: {state['user_message']}\n"
        f"order_status: {state['order_status']}\n"
        f"order: {state['order']}\n"
        "What should the next step be?"
    )

    decision: RouteDecision = router_llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
    )

    print(f"[LLM] -> decided next_step = '{decision.next_step}'")

    # The router only records its decision. route_from_llm() (below)
    # reads current_step a moment later to pick the actual next node.
    state["current_step"] = decision.next_step
    return state


# ------------------------------------------------------------------
# 6. THE RESTAURANT OPERATION NODES (plain Python, no LLM involved)
# ------------------------------------------------------------------

def take_order(state: RestaurantState) -> RestaurantState:
    print("[take_order] Taking the order...")

    # For this simple demo we don't do real NLP extraction - we just
    # fake a structured order based on the user's message.
    state["order"] = {"items": state["user_message"], "quantity": 1}
    state["order_status"] = "ordered"

    print(f"[take_order] Order recorded: {state['order']}")
    return state


def cook(state: RestaurantState) -> RestaurantState:
    print("[cook] Cooking order...")

    state["order_status"] = "cooked"

    print("[cook] Order is now cooked.")
    return state


def serve(state: RestaurantState) -> RestaurantState:
    print("[serve] Serving order...")

    state["order_status"] = "served"
    state["response"] = f"Here is your order: {state['order']}. Enjoy your meal!"

    print("[serve] Order has been served.")
    return state


# ------------------------------------------------------------------
# 7. THE CONDITIONAL ROUTING FUNCTION
# ------------------------------------------------------------------
# This is NOT the LLM itself - it's a small, plain Python function
# that LangGraph calls right after the "llm" node runs. It just reads
# the decision the LLM already made (stored in current_step) and tells
# LangGraph the NAME of the next node to jump to.

def route_from_llm(state: RestaurantState) -> str:
    next_step = state["current_step"]
    print(f"[route_from_llm] Routing to: {next_step}")

    if next_step == "end":
        return END
    return next_step  # "take_order", "cook", or "serve"


# ------------------------------------------------------------------
# 8. BUILDING THE GRAPH
# ------------------------------------------------------------------

graph = StateGraph(RestaurantState)

# 8a. Register every node with a name.
graph.add_node("llm", llm_router)
graph.add_node("take_order", take_order)
graph.add_node("cook", cook)
graph.add_node("serve", serve)

# 8b. START always goes straight to the LLM router first.
graph.add_edge(START, "llm")

# 8c. From "llm", the next node depends on the router's decision.
# The dictionary maps route_from_llm()'s possible return values to
# actual node names in the graph (END is a special built-in value).
graph.add_conditional_edges(
    "llm",
    route_from_llm,
    {
        "take_order": "take_order",
        "cook": "cook",
        "serve": "serve",
        END: END,
    },
)

# 8d. This is the LOOP: after each operation finishes, we go back to
# the LLM router so it can decide the next step again.
graph.add_edge("take_order", "llm")
graph.add_edge("cook", "llm")
graph.add_edge("serve", "llm")

# 8e. Compile the graph into a runnable app.
app = graph.compile()


# ------------------------------------------------------------------
# 9. RUNNING THE GRAPH
# ------------------------------------------------------------------

if __name__ == "__main__":
    initial_state: RestaurantState = {
        "user_message": "I want a burger and a coke",
        "order": None,
        "order_status": "new",
        "current_step": "start",
        "response": "",
    }

    print("=" * 60)
    print("STARTING RESTAURANT GRAPH")
    print("=" * 60)

    result = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)
    for key, value in result.items():
        print(f"{key}: {value}")
