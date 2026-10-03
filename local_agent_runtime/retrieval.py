from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log
from pathlib import Path
import json
import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict


def load_corpus(path: str) -> list[Document]:
    documents = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        documents.append(Document(
            id=str(row["id"]),
            text=str(row["text"]),
            metadata=dict(row.get("metadata", {})),
        ))
    return documents


class BM25:
    def __init__(self, documents: list[Document], k1: float = 1.5, b: float = .75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.counts = [Counter(tokenize(document.text)) for document in documents]
        self.lengths = [sum(counts.values()) for counts in self.counts]
        self.average = sum(self.lengths) / max(1, len(self.lengths))
        df = Counter(term for counts in self.counts for term in counts)
        n = len(documents)
        self.idf = {
            term: log(1 + (n - frequency + .5) / (frequency + .5))
            for term, frequency in df.items()
        }

    def search(self, query: str, k: int = 5) -> list[dict]:
        terms = set(tokenize(query))
        rows = []
        for document, counts, length in zip(self.documents, self.counts, self.lengths):
            score = 0.0
            for term in terms:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * length / max(self.average, 1e-9)
                )
                score += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / denominator
            if score > 0:
                rows.append({
                    "id": document.id,
                    "text": document.text,
                    "metadata": document.metadata,
                    "score": score,
                })
        return sorted(rows, key=lambda row: (-row["score"], row["id"]))[:k]


def packed_text(hits: list[dict], max_chars: int = 12000) -> str:
    blocks = []
    used = 0
    for index, hit in enumerate(hits, 1):
        block = f"[{index}] {hit['id']}\n{hit['text'].strip()}\n"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 64:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        used += len(block)
    return "\n".join(blocks)
