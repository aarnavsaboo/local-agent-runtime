from __future__ import annotations

from pathlib import Path
from threading import RLock
from time import time
import json
import sqlite3


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at REAL NOT NULL,
    finished_at REAL,
    input_json TEXT NOT NULL,
    output_json TEXT
);

CREATE TABLE IF NOT EXISTS node_attempts (
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at REAL NOT NULL,
    finished_at REAL,
    output_json TEXT,
    error TEXT,
    PRIMARY KEY (run_id, node_id, attempt)
);

CREATE INDEX IF NOT EXISTS idx_node_attempts_run ON node_attempts(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
"""


class Journal:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.lock = RLock()

    def close(self):
        with self.lock:
            self.connection.close()

    def start_run(self, run_id: str, workflow: str, inputs: dict):
        with self.lock:
            self.connection.execute(
                "INSERT INTO runs(run_id,workflow,status,started_at,input_json) VALUES(?,?,?,?,?)",
                (run_id, workflow, "running", time(), json.dumps(inputs, sort_keys=True)),
            )
            self.connection.commit()

    def finish_run(self, run_id: str, status: str, output: dict):
        with self.lock:
            self.connection.execute(
                "UPDATE runs SET status=?, finished_at=?, output_json=? WHERE run_id=?",
                (status, time(), json.dumps(output, sort_keys=True), run_id),
            )
            self.connection.commit()

    def start_node(self, run_id: str, node_id: str, attempt: int):
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO node_attempts(run_id,node_id,attempt,status,started_at)
                VALUES(?,?,?,?,?)
                """,
                (run_id, node_id, attempt, "running", time()),
            )
            self.connection.commit()

    def finish_node(
        self,
        run_id: str,
        node_id: str,
        attempt: int,
        status: str,
        output: dict | None = None,
        error: str | None = None,
    ):
        with self.lock:
            self.connection.execute(
                """
                UPDATE node_attempts
                SET status=?, finished_at=?, output_json=?, error=?
                WHERE run_id=? AND node_id=? AND attempt=?
                """,
                (
                    status,
                    time(),
                    None if output is None else json.dumps(output, sort_keys=True),
                    error,
                    run_id,
                    node_id,
                    attempt,
                ),
            )
            self.connection.commit()

    def history(self, limit: int = 20) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["input"] = json.loads(item.pop("input_json"))
            raw = item.pop("output_json")
            item["output"] = None if raw is None else json.loads(raw)
            output.append(item)
        return output

    def attempts(self, run_id: str) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                """
                SELECT * FROM node_attempts
                WHERE run_id=?
                ORDER BY started_at, node_id, attempt
                """,
                (run_id,),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            raw = item.pop("output_json")
            item["output"] = None if raw is None else json.loads(raw)
            output.append(item)
        return output
