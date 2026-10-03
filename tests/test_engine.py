import asyncio
import unittest

from local_agent_runtime.engine import Engine
from local_agent_runtime.workflow import from_dict


class FakeSteps:
    async def execute(self, node, context):
        if node.type == "fail":
            raise RuntimeError("expected")
        if node.type == "template":
            return {"text": node.config.get("text", node.id)}
        return {"value": node.id}


class Tests(unittest.TestCase):
    def test_parallel_shape_and_dependency(self):
        workflow = from_dict({
            "name":"x",
            "concurrency":2,
            "nodes":[
                {"id":"a","type":"template","config":{"text":"a"}},
                {"id":"b","type":"template","config":{"text":"b"}},
                {"id":"c","type":"template","depends_on":["a","b"],"config":{"text":"c"}},
            ],
        })
        result = asyncio.run(Engine(workflow, steps=FakeSteps()).run({}))
        self.assertEqual(result.status, "success")
        self.assertEqual(result.outputs["c"]["text"], "c")

    def test_failed_branch_skips_descendant(self):
        workflow = from_dict({
            "name":"x",
            "nodes":[
                {"id":"a","type":"fail"},
                {"id":"b","type":"template","depends_on":["a"]},
                {"id":"c","type":"template"},
            ],
        })
        result = asyncio.run(Engine(workflow, steps=FakeSteps()).run({}))
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.node_status["a"], "failure")
        self.assertEqual(result.node_status["b"], "skipped")
        self.assertEqual(result.node_status["c"], "success")


if __name__ == "__main__":
    unittest.main()
