import unittest

from local_agent_runtime.workflow import from_dict


class Tests(unittest.TestCase):
    def test_topological(self):
        workflow = from_dict({
            "name": "x",
            "nodes": [
                {"id":"a","type":"template"},
                {"id":"b","type":"template","depends_on":["a"]},
            ],
        })
        self.assertEqual(workflow.topological(), ["a","b"])

    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            from_dict({
                "name":"x",
                "nodes":[
                    {"id":"a","type":"template","depends_on":["b"]},
                    {"id":"b","type":"template","depends_on":["a"]},
                ],
            })


if __name__ == "__main__":
    unittest.main()
