import os
import re
from time import sleep
from dotenv import load_dotenv
from groq import Groq

# ===============================
# Load API Key
# ===============================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found!")

client = Groq(api_key=api_key)

MODEL = "llama-3.3-70b-versatile"

# ===============================
# Tools
# ===============================

def get_product_price(product):
    """Returns product price."""

    prices = {
        "iPhone 17": 1000,
        "iPhone 15": 500,
    }

    return prices.get(product, 0)


def calculator(expression):
    """Simple calculator."""

    try:
        return eval(expression)
    except Exception as e:
        return f"Calculator Error: {e}"


# Dictionary of available tools
tools = {
    "get_product_price": get_product_price,
    "calculator": calculator,
}

# ===============================
# System Prompt
# ===============================

system_prompt = """
You are a shopping assistant.

You have these tools:

1. get_product_price(product)
2. calculator(expression)

Rules:

1. Think step by step.
2. Call ONLY ONE tool at a time.
3. After writing an Action, STOP.
4. Wait for the Observation.
5. Never make up tool results.
6. Continue until the task is complete.
7. End with Final Answer.

Tool Format:

Thought: explain reasoning

Action: get_product_price("iPhone 17")

OR

Action: calculator("5000 - 1000")

Never use keyword arguments like:

get_product_price(product="iPhone 17")

When done:

Final Answer: ...
"""

# ===============================
# Agent
# ===============================

def run_agent(question):

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    MAX_STEPS = 10

    for step in range(MAX_STEPS):

        print("\n" + "=" * 50)
        print(f"STEP {step + 1}")
        print("=" * 50)

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
        )

        answer = response.choices[0].message.content

        print(answer)

        # Save assistant response
        messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        # -------------------------
        # Check Final Answer
        # -------------------------

        if "Final Answer:" in answer:
            print("\nAgent Finished!")
            break

        # -------------------------
        # Extract Action
        # -------------------------

        match = re.search(
            r'Action:\s*(\w+)\("?(.*?)"?\)',
            answer,
            re.DOTALL,
        )

        if not match:
            print("\nNo action found.")
            break

        tool_name = match.group(1)
        tool_input = match.group(2).strip()

        print("\nTool :", tool_name)
        print("Input:", tool_input)

        # -------------------------
        # Execute Tool
        # -------------------------

        if tool_name not in tools:
            observation = f"Tool '{tool_name}' not found."

        else:

            try:
                observation = tools[tool_name](tool_input)

            except Exception as e:
                observation = f"Tool Error: {e}"

        print("Observation:", observation)

        # -------------------------
        # Send Observation Back
        # -------------------------

        messages.append(
            {
                "role": "user",
                "content": f"Observation: {observation}",
            }
        )

        sleep(1)

    else:
        print("\nReached maximum number of steps.")

# ===============================
# Run
# ===============================

prompt = """
I have 5000 rupees.

What is the price of iPhone 17?

How much money will I have left?
"""

run_agent(prompt)