from __future__ import annotations

import re
from typing import Any


REFERENCE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


def lookup(context: dict[str, Any], path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(f"unknown workflow reference: {path}")
    return current


def render(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: render(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [render(item, context) for item in value]
    if not isinstance(value, str):
        return value

    full = REFERENCE.fullmatch(value)
    if full:
        return lookup(context, full.group(1))

    def replace(match: re.Match) -> str:
        resolved = lookup(context, match.group(1))
        if isinstance(resolved, (dict, list)):
            import json
            return json.dumps(resolved, ensure_ascii=False)
        return str(resolved)

    return REFERENCE.sub(replace, value)


def build_context(inputs: dict[str, Any], outputs: dict[str, dict]) -> dict[str, Any]:
    return {
        "input": inputs,
        "nodes": outputs,
    }
