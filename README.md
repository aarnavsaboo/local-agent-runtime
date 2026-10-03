# local-agent-runtime

A small local workflow runtime for composing retrieval and language-model steps into inspectable DAGs.

The project is built around application-shaped AI workflows rather than an autonomous chat loop. A workflow is a JSON graph of named steps with explicit dependencies. Independent nodes can run concurrently; dependent nodes receive structured outputs from earlier steps.

The included step types are intentionally narrow:

- template/render steps
- local lexical retrieval
- local Ollama generation
- joins and field selection

The runtime adds orchestration around those steps:

- dependency validation
- cycle detection
- bounded parallel execution
- per-node retries
- per-node timeouts
- run/node status tracking
- SQLite execution journal
- JSONL batch inputs
- deterministic run summaries
- raw node outputs for later inspection

## Example workflow

```json
{
  "name": "local-rag-summary",
  "concurrency": 3,
  "nodes": [
    {
      "id": "retrieve",
      "type": "retrieve",
      "config": {
        "corpus": "examples/corpus.jsonl",
        "query": "{{input.question}}",
        "top_k": 4
      }
    },
    {
      "id": "answer",
      "type": "ollama",
      "depends_on": ["retrieve"],
      "timeout_seconds": 120,
      "retries": 1,
      "config": {
        "model": "qwen3:4b",
        "prompt": "Use the passages below to answer the question.\n\n{{nodes.retrieve.text}}\n\nQuestion: {{input.question}}",
        "max_tokens": 256
      }
    }
  ]
}
```

Run it:

```bash
python -m local_agent_runtime run \
  examples/workflow.json \
  --input examples/input.json \
  --db runs/workflows.db
```

Batch several inputs:

```bash
python -m local_agent_runtime batch \
  examples/workflow.json \
  examples/inputs.jsonl \
  --db runs/workflows.db \
  --workers 4
```

Inspect previous runs:

```bash
python -m local_agent_runtime history \
  --db runs/workflows.db \
  --limit 20
```

## Execution model

```text
workflow JSON
    |
    v
graph validation
    |
    +--> dependency check
    +--> cycle detection
    |
    v
run scheduler
    |
    +--> ready nodes
    |       |
    |       +--> template
    |       +--> retrieval
    |       +--> local model
    |
    +--> bounded concurrency
    +--> retry / timeout
    |
    v
node outputs
    |
    +--> downstream context
    +--> SQLite journal
    |
    v
final run record
```

## Context references

Configuration strings can refer to run input and previous node outputs.

```text
{{input.question}}
{{input.document_id}}
{{nodes.retrieve.text}}
{{nodes.answer.text}}
```

References are resolved immediately before a node starts, so a node can only consume outputs from dependencies that have completed.

## Retrieval steps

The built-in retrieval step uses a small BM25 implementation over JSONL documents.

```json
{"id":"doc-1","text":"..."}
{"id":"doc-2","text":"..."}
```

The output includes ranked IDs, scores and a packed text representation for downstream model prompts.

This is deliberately a local baseline. A workflow can be extended with another step implementation without changing the scheduler.

## Local model steps

The built-in model step sends generation requests to an Ollama endpoint on localhost by default.

Each result keeps:

- response text
- model
- prompt token count
- output token count
- load duration
- prompt-evaluation duration
- generation duration
- client wall-clock duration

The scheduler treats those values as step output rather than hiding them in logs.

## Run journal

SQLite stores a run row and one row per node attempt.

The journal is useful when running batches because a final workflow result can be inspected after the console output is gone. Node records include status, start/end timestamps, attempt number, output JSON and error text.

The journal is local and intentionally small; it is not a distributed workflow database.

## Failure behaviour

A failed node is retried according to its node configuration. If it still fails, dependent nodes are marked skipped while independent branches can finish.

The final run status is one of:

- `success`
- `partial`
- `failed`

This makes partial workflow results visible instead of discarding the entire run.

## Repository layout

- `workflow.py` — graph data model and validation
- `context.py` — reference resolution and template rendering
- `retrieval.py` — local BM25 step support
- `ollama.py` — local model adapter
- `steps.py` — built-in step implementations
- `journal.py` — SQLite run/node journal
- `engine.py` — asynchronous DAG scheduler
- `batch.py` — multiple input execution
- `report.py` — workflow/run summaries
- `io.py` — JSON workflow and input loading
- `examples/` — local RAG workflow fixtures
- `docs/` — runtime design notes
- `tests/` — graph, rendering, retrieval and scheduler tests

Maintained by **Aarnav Saboo**.
