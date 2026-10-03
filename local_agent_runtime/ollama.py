from __future__ import annotations

from time import perf_counter
from urllib.request import Request, urlopen
from typing import Any
import json


class Ollama:
    def __init__(self, endpoint: str = "http://127.0.0.1:11434"):
        self.endpoint = endpoint.rstrip("/")

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.0,
        keep_alive: str = "10m",
    ) -> dict[str, Any]:
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }).encode()
        request = Request(
            self.endpoint + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started = perf_counter()
        with urlopen(request, timeout=600) as response:
            row = json.load(response)
        elapsed = perf_counter() - started

        eval_count = row.get("eval_count")
        eval_duration = row.get("eval_duration")
        decode_tps = None
        if eval_count and eval_duration:
            decode_tps = float(eval_count) / (float(eval_duration) / 1e9)

        return {
            "text": row.get("response", ""),
            "model": model,
            "elapsed_seconds": elapsed,
            "prompt_tokens": row.get("prompt_eval_count"),
            "output_tokens": eval_count,
            "decode_tps": decode_tps,
            "load_seconds": None if row.get("load_duration") is None else row["load_duration"] / 1e9,
            "prompt_eval_seconds": None if row.get("prompt_eval_duration") is None else row["prompt_eval_duration"] / 1e9,
            "generation_seconds": None if eval_duration is None else eval_duration / 1e9,
            "done_reason": row.get("done_reason"),
        }
