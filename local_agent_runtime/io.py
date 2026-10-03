from pathlib import Path
import json

from .workflow import Workflow, from_dict


def load_workflow(path: str) -> Workflow:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def load_input(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_inputs(path: str) -> list[tuple[str, dict]]:
    rows = []
    for index, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines()
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        item_id = str(row.get("id", f"item-{index}"))
        inputs = dict(row.get("input", row))
        inputs.pop("id", None)
        rows.append((item_id, inputs))
    return rows
