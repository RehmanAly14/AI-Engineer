"""
Tests for the multi-agent system.

Run:  uv run python -m unittest -v test_main.py

- Unit tests: no API calls (tools + notebook).
- Live tests: call Groq and Tavily for real to check the whole system.
"""

import os
import tempfile
import unittest

from main import Notebook, calculate, manager, manager_plan, math_agent, search_agent, web_search


def route(request: str) -> list:
    return [step["agent"] for step in manager_plan(request)["steps"]]


class TestCalculator(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(calculate("2 + 3 * 4"), "14")
        self.assertEqual(calculate("(10 - 4) / 3"), "2.0")
        self.assertEqual(calculate("2 ** 10"), "1024")
        self.assertEqual(calculate("-5 + 2"), "-3")

    def test_rejects_unsafe_code(self):
        self.assertIn("Error", calculate("__import__('os').system('dir')"))

    def test_divide_by_zero(self):
        self.assertIn("Error", calculate("1 / 0"))


class TestNotebook(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "nb.json")
        self.notebook = Notebook(self.path)

    def test_empty(self):
        self.assertEqual(self.notebook.read(), [])

    def test_write_and_read(self):
        self.notebook.write("2+2?", [{"agent": "math", "task": "2+2", "result": "4"}], "it is math", "4")
        self.notebook.write("hi", [], "greeting", "Hi!")
        records = self.notebook.read()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["routed_to"], ["math"])
        self.assertEqual(records[1]["routed_to"], [])
        self.assertEqual(records[1]["id"], 2)


class TestLive(unittest.TestCase):
    """These call the real APIs."""

    def test_web_search_tool(self):
        result = web_search("capital of Pakistan")
        self.assertIn("Islamabad", result)

    def test_manager_routes_math(self):
        self.assertEqual(route("What is 25% of 840?"), ["math"])

    def test_manager_routes_search(self):
        self.assertEqual(route("Who won the latest Cricket World Cup?"), ["search"])

    def test_manager_routes_greeting(self):
        self.assertEqual(route("hello!"), [])

    def test_manager_plans_search_then_math(self):
        self.assertEqual(route("What is 10% of Pakistan's population?"), ["search", "math"])

    def test_math_agent(self):
        answer = math_agent("I bought 3 shirts at 1250 rupees each and paid with 5000. How much change?")
        self.assertIn("1250", answer.replace(",", ""))

    def test_search_agent(self):
        answer = search_agent("What is the capital of Japan?")
        self.assertIn("Tokyo", answer)

    def test_full_system_writes_notebook(self):
        path = os.path.join(tempfile.mkdtemp(), "nb.json")
        notebook = Notebook(path)
        record = manager("Calculate 144 / 12 + 7", notebook)
        self.assertEqual(record["routed_to"], ["math"])
        self.assertIn("19", record["answer"])
        self.assertEqual(len(notebook.read()), 1)

    def test_full_system_search_then_math(self):
        path = os.path.join(tempfile.mkdtemp(), "nb.json")
        record = manager("What is the population of Japan divided by 1000?", Notebook(path))
        self.assertEqual(record["routed_to"], ["search", "math"])
        self.assertEqual(len(record["steps"]), 2)
        self.assertTrue(record["steps"][1]["result"])
        self.assertTrue(record["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
