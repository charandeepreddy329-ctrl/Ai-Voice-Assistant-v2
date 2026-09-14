import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from nova_assistant.assistant import NovaAssistant
from nova_assistant.calculator import extract_expression, safe_calculate
from nova_assistant.models import UnsafeExpressionError
from nova_assistant.storage import LocalStorage


class FakeLLM:
    def __init__(self): self.calls = []
    def answer(self, question, *, math_mode=False):
        self.calls.append((question, math_mode)); return "Local model answer."
    def health(self): return "Ollama is online."


class FakeActions:
    def __init__(self): self.calls = []
    def search_google(self, query): self.calls.append(("google", query)); return f"Searching Google for {query}."
    def search_youtube(self, query): self.calls.append(("youtube", query)); return f"Searching YouTube for {query}."
    def open_website(self, name): return f"Opening {name}."
    def open_app(self, name): return f"Opening {name}."
    def create_python_file(self, request): self.calls.append(("python", request)); return "Saved safely."


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.storage = LocalStorage(Path(self.tmp.name))
        self.llm = FakeLLM(); self.actions = FakeActions()
        self.nova = NovaAssistant(self.storage, self.llm, self.actions,
                                  now=lambda: datetime(2026, 8, 15, 9, 5))
    def tearDown(self): self.tmp.cleanup()
    def test_math(self): self.assertEqual(self.nova.handle("calculate (8 + 4) / 3").text, "The answer is 4.")
    def test_precedence(self): self.assertEqual(safe_calculate("2 + 3 * 4"), 14)
    def test_spoken_math(self): self.assertEqual(safe_calculate(extract_expression("calculate 24 plus 8 divided by 4")), 26)
    def test_unsafe_math(self):
        with self.assertRaises(UnsafeExpressionError): safe_calculate("__import__('os').system('x')")
    def test_memory(self):
        self.nova.handle("remember that demo is Friday")
        self.assertIn("demo is Friday", self.nova.handle("what do you remember").text)
    def test_search_query(self):
        self.nova.handle("search Google for terraform tutorials")
        self.assertEqual(self.actions.calls[-1], ("google", "terraform tutorials"))
    def test_python_routing(self):
        self.nova.handle("create python file called timer")
        self.assertEqual(self.actions.calls[-1][0], "python")
    def test_general_model(self):
        self.assertEqual(self.nova.handle("Explain recursion").text, "Local model answer.")
    def test_exit(self): self.assertTrue(self.nova.handle("stop").should_exit)


if __name__ == "__main__": unittest.main()

