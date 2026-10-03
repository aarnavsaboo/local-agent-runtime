from argparse import ArgumentParser
from dataclasses import asdict
import asyncio
import json

from .batch import run_batch
from .engine import Engine
from .io import load_input, load_inputs, load_workflow
from .journal import Journal
from .report import summarize_runs
from .steps import Steps


def main():
    parser = ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("workflow")
    run.add_argument("--input", required=True)
    run.add_argument("--db", default="runs/workflows.db")
    run.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")

    batch = sub.add_parser("batch")
    batch.add_argument("workflow")
    batch.add_argument("inputs")
    batch.add_argument("--db", default="runs/workflows.db")
    batch.add_argument("--workers", type=int, default=4)
    batch.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")

    history = sub.add_parser("history")
    history.add_argument("--db", default="runs/workflows.db")
    history.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()

    if args.cmd == "history":
        journal = Journal(args.db)
        try:
            rows = journal.history(args.limit)
            print(json.dumps({
                "summary": summarize_runs(rows),
                "runs": rows,
            }, indent=2))
        finally:
            journal.close()
        return

    workflow = load_workflow(args.workflow)
    journal = Journal(args.db)

    try:
        if args.cmd == "run":
            engine = Engine(
                workflow,
                journal=journal,
                steps=Steps(args.ollama_endpoint),
            )
            result = asyncio.run(engine.run(load_input(args.input)))
            print(json.dumps(asdict(result), indent=2))
        else:
            records = load_inputs(args.inputs)

            def factory():
                return Engine(
                    workflow,
                    journal=journal,
                    steps=Steps(args.ollama_endpoint),
                )

            rows = asyncio.run(run_batch(factory, records, args.workers))
            print(json.dumps({
                "runs": len(rows),
                "success": sum(row["status"] == "success" for row in rows),
                "results": rows,
            }, indent=2))
    finally:
        journal.close()


if __name__ == "__main__":
    main()
