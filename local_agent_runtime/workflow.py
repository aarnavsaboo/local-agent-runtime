from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    depends_on: tuple[str, ...] = ()
    retries: int = 0
    timeout_seconds: float = 120.0
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Workflow:
    name: str
    nodes: tuple[Node, ...]
    concurrency: int = 4

    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("workflow name is required")
        if self.concurrency < 1:
            raise ValueError("concurrency must be positive")

        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node IDs must be unique")
        if any(not node_id.strip() for node_id in ids):
            raise ValueError("node IDs must be non-empty")

        known = set(ids)
        for node in self.nodes:
            if node.id in node.depends_on:
                raise ValueError(f"node {node.id} cannot depend on itself")
            missing = set(node.depends_on) - known
            if missing:
                raise ValueError(f"node {node.id} has unknown dependencies: {sorted(missing)}")
            if node.retries < 0:
                raise ValueError("retries must be non-negative")
            if node.timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive")

        # DFS cycle detection.
        graph = {node.id: node.depends_on for node in self.nodes}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str):
            if node_id in visiting:
                raise ValueError("workflow contains a dependency cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in graph[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in ids:
            visit(node_id)

    def topological(self) -> list[str]:
        self.validate()
        done: set[str] = set()
        order: list[str] = []
        while len(order) < len(self.nodes):
            ready = [
                node.id
                for node in self.nodes
                if node.id not in done and set(node.depends_on) <= done
            ]
            if not ready:
                raise ValueError("workflow cannot be topologically ordered")
            for node_id in ready:
                done.add(node_id)
                order.append(node_id)
        return order


def from_dict(data: dict[str, Any]) -> Workflow:
    nodes = []
    for row in data.get("nodes", []):
        nodes.append(Node(
            id=str(row["id"]),
            type=str(row["type"]),
            depends_on=tuple(str(x) for x in row.get("depends_on", [])),
            retries=int(row.get("retries", 0)),
            timeout_seconds=float(row.get("timeout_seconds", 120.0)),
            config=dict(row.get("config", {})),
        ))
    workflow = Workflow(
        name=str(data["name"]),
        nodes=tuple(nodes),
        concurrency=int(data.get("concurrency", 4)),
    )
    workflow.validate()
    return workflow
