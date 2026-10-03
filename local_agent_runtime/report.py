from __future__ import annotations

from collections import Counter
from statistics import median


def summarize_runs(rows: list[dict]) -> dict:
    statuses = Counter(row["status"] for row in rows)
    durations = [
        float(row["finished_at"] - row["started_at"])
        for row in rows
        if row.get("finished_at") is not None
    ]
    return {
        "runs": len(rows),
        "statuses": dict(sorted(statuses.items())),
        "median_elapsed_seconds": None if not durations else median(durations),
        "max_elapsed_seconds": None if not durations else max(durations),
    }


def summarize_attempts(rows: list[dict]) -> dict:
    statuses = Counter(row["status"] for row in rows)
    nodes = Counter(row["node_id"] for row in rows)
    return {
        "attempts": len(rows),
        "statuses": dict(sorted(statuses.items())),
        "by_node": dict(sorted(nodes.items())),
    }
