from __future__ import annotations

import asyncio
from typing import Any

from .context import render
from .ollama import Ollama
from .retrieval import BM25, load_corpus, packed_text
from .workflow import Node


class Steps:
    def __init__(self, ollama_endpoint: str = "http://127.0.0.1:11434"):
        self.ollama = Ollama(ollama_endpoint)
        self._retrievers: dict[str, BM25] = {}

    def _retriever(self, path: str) -> BM25:
        if path not in self._retrievers:
            self._retrievers[path] = BM25(load_corpus(path))
        return self._retrievers[path]

    async def execute(self, node: Node, context: dict[str, Any]) -> dict[str, Any]:
        config = render(node.config, context)

        if node.type == "template":
            text = str(config.get("text", ""))
            return {"text": text}

        if node.type == "join":
            separator = str(config.get("separator", "\n\n"))
            values = config.get("values", [])
            return {"text": separator.join(str(value) for value in values)}

        if node.type == "select":
            return {"value": config.get("value")}

        if node.type == "retrieve":
            corpus = str(config["corpus"])
            query = str(config["query"])
            top_k = int(config.get("top_k", 5))
            max_chars = int(config.get("max_chars", 12000))
            hits = await asyncio.to_thread(self._retriever(corpus).search, query, top_k)
            return {
                "query": query,
                "hits": hits,
                "ids": [hit["id"] for hit in hits],
                "text": packed_text(hits, max_chars),
            }

        if node.type == "ollama":
            result = await asyncio.to_thread(
                self.ollama.generate,
                model=str(config["model"]),
                prompt=str(config["prompt"]),
                max_tokens=int(config.get("max_tokens", 256)),
                temperature=float(config.get("temperature", 0.0)),
                keep_alive=str(config.get("keep_alive", "10m")),
            )
            return result

        raise ValueError(f"unknown step type: {node.type}")
