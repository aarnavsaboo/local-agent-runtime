from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
import asyncio
import uuid

from .context import build_context
from .journal import Journal
from .steps import Steps
from .workflow import Node, Workflow


@dataclass(frozen=True)
class RunResult:
    run_id: str
    workflow: str
    status: str
    elapsed_seconds: float
    outputs: dict[str, dict]
    node_status: dict[str, str]


class Engine:
    def __init__(
        self,
        workflow: Workflow,
        *,
        journal: Journal | None = None,
        steps: Steps | None = None,
    ):
        workflow.validate()
        self.workflow = workflow
        self.journal = journal
        self.steps = steps or Steps()
        self.nodes = workflow.node_map()
        self.semaphore = asyncio.Semaphore(workflow.concurrency)

    async def _attempt_node(
        self,
        run_id: str,
        node: Node,
        inputs: dict,
        outputs: dict[str, dict],
    ) -> dict:
        context = build_context(inputs, outputs)
        last_error: Exception | None = None

        for attempt in range(node.retries + 1):
            if self.journal:
                self.journal.start_node(run_id, node.id, attempt)

            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(
                        self.steps.execute(node, context),
                        timeout=node.timeout_seconds,
                    )
                if self.journal:
                    self.journal.finish_node(
                        run_id, node.id, attempt, "success", output=result
                    )
                return result
            except Exception as exc:
                last_error = exc
                if self.journal:
                    self.journal.finish_node(
                        run_id,
                        node.id,
                        attempt,
                        "failure",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                if attempt < node.retries:
                    await asyncio.sleep(min(.25 * (2 ** attempt), 2.0))

        assert last_error is not None
        raise last_error

    async def run(self, inputs: dict, run_id: str | None = None) -> RunResult:
        resolved_run_id = run_id or uuid.uuid4().hex
        if self.journal:
            self.journal.start_run(resolved_run_id, self.workflow.name, inputs)

        started = perf_counter()
        outputs: dict[str, dict] = {}
        status = {node.id: "pending" for node in self.workflow.nodes}
        running: dict[str, asyncio.Task] = {}

        try:
            while True:
                # Nodes depending on a failed/skipped node cannot run.
                for node in self.workflow.nodes:
                    if status[node.id] != "pending":
                        continue
                    dependency_states = [status[dep] for dep in node.depends_on]
                    if any(value in {"failure", "skipped"} for value in dependency_states):
                        status[node.id] = "skipped"

                ready = [
                    node
                    for node in self.workflow.nodes
                    if status[node.id] == "pending"
                    and all(status[dep] == "success" for dep in node.depends_on)
                ]

                for node in ready:
                    status[node.id] = "running"
                    running[node.id] = asyncio.create_task(
                        self._attempt_node(resolved_run_id, node, inputs, outputs)
                    )

                if not running:
                    if not any(value == "pending" for value in status.values()):
                        break
                    raise RuntimeError("workflow scheduler has pending nodes but no runnable work")

                done, _ = await asyncio.wait(
                    list(running.values()),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                completed_ids = [
                    node_id
                    for node_id, task in running.items()
                    if task in done
                ]

                for node_id in completed_ids:
                    task = running.pop(node_id)
                    try:
                        outputs[node_id] = task.result()
                        status[node_id] = "success"
                    except Exception as exc:
                        outputs[node_id] = {
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        status[node_id] = "failure"

            success_count = sum(value == "success" for value in status.values())
            failure_count = sum(value == "failure" for value in status.values())
            if failure_count == 0 and success_count == len(status):
                final_status = "success"
            elif success_count:
                final_status = "partial"
            else:
                final_status = "failed"

            result = RunResult(
                run_id=resolved_run_id,
                workflow=self.workflow.name,
                status=final_status,
                elapsed_seconds=perf_counter() - started,
                outputs=outputs,
                node_status=status,
            )

            if self.journal:
                self.journal.finish_run(
                    resolved_run_id,
                    final_status,
                    {
                        "elapsed_seconds": result.elapsed_seconds,
                        "outputs": outputs,
                        "node_status": status,
                    },
                )
            return result
        except Exception:
            if self.journal:
                self.journal.finish_run(
                    resolved_run_id,
                    "failed",
                    {"outputs": outputs, "node_status": status},
                )
            raise
