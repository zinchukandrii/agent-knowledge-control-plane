"""Small SQLite persistence layer for local task and run audit records."""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from .state import TaskStatus


class SQLiteStore:
    """Persists local control-plane records without credentials or external effects."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    context_packet_json TEXT NOT NULL,
                    evidence_cards_json TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    verification_defects_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
                """
            )

    def create_task(self, *, project_id: str, objective: str) -> dict[str, str]:
        task = {
            "id": f"task-{uuid4().hex}",
            "project_id": project_id,
            "objective": objective,
            "status": TaskStatus.DRAFT.value,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO tasks (id, project_id, objective, status) VALUES (?, ?, ?, ?)",
                tuple(task.values()),
            )
        return task

    def get_task(self, task_id: str) -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT id, project_id, objective, status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def update_task_status(self, *, task_id: str, status: TaskStatus) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE tasks SET status = ? WHERE id = ?", (status.value, task_id))

    def create_run(self, *, task_id: str, run: dict, context_packet: dict) -> dict:
        run_id = f"run-{uuid4().hex}"
        record = {"id": run_id, "task_id": task_id, **run}
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, task_id, status, context_packet_json, evidence_cards_json, brief_json,
                    verification_defects_json, trace_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_id,
                    run["status"],
                    json.dumps(context_packet),
                    json.dumps(run["evidence_cards"]),
                    json.dumps(run["brief"]),
                    json.dumps(run["verification_defects"]),
                    json.dumps(run["trace"]),
                ),
            )
        return record

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        record = dict(row)
        return {
            "id": record["id"],
            "task_id": record["task_id"],
            "status": record["status"],
            "context_packet": json.loads(record["context_packet_json"]),
            "evidence_cards": json.loads(record["evidence_cards_json"]),
            "brief": json.loads(record["brief_json"]),
            "verification_defects": json.loads(record["verification_defects_json"]),
            "trace": json.loads(record["trace_json"]),
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
