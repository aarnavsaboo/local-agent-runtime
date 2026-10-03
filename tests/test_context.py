import unittest

from local_agent_runtime.context import render


class Tests(unittest.TestCase):
    def test_render(self):
        context = {
            "input":{"question":"hello"},
            "nodes":{"a":{"text":"retrieved text"}},
        }
        value = render(
            "Q={{input.question}} C={{nodes.a.text}}",
            context,
        )
        self.assertEqual(value, "Q=hello C=retrieved text")

    def test_full_reference_preserves_type(self):
        context = {"input":{"items":[1,2]}, "nodes":{}}
        self.assertEqual(render("{{input.items}}", context), [1,2])


if __name__ == "__main__":
    unittest.main()
