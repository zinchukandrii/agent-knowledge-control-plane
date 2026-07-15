"""Read-only FastAPI control-plane surface for deterministic local fixture runs."""

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .knowledge import build_context_packet, load_nodes
from .pipeline import run_research_brief
from .store import SQLiteStore


class CreateTaskRequest(BaseModel):
    """The only accepted task intake payload for the fixture API."""

    project_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)


def create_app(*, database_path: Path | None = None, vault_path: Path | None = None) -> FastAPI:
    """Create an isolated local app; worker execution has no external side effects."""
    project_root = Path(__file__).parents[1]
    store = SQLiteStore(database_path or Path("data") / "control-plane.sqlite3")
    store.initialize()
    fixture_vault = vault_path or project_root / "examples" / "demo_vault"

    static_dir = Path(__file__).with_name("static")
    app = FastAPI(title="Evidence-First Agent Knowledge & Control Plane", version="0.1.0")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.post("/tasks", status_code=status.HTTP_201_CREATED)
    def create_task(payload: CreateTaskRequest) -> dict[str, str]:
        return store.create_task(project_id=payload.project_id, objective=payload.objective)

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, str]:
        task = store.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        return task

    @app.post("/tasks/{task_id}/run")
    def run_task(task_id: str) -> dict:
        task = store.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        nodes = load_nodes(fixture_vault)
        has_scoped_node = any(
            node.project_id == task["project_id"] and node.sensitivity == "public" for node in nodes
        )
        if not has_scoped_node:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No public knowledge is available for this project.",
            )

        packet = build_context_packet(
            task_id=task["id"],
            project_id=task["project_id"],
            objective=task["objective"],
            nodes=nodes,
        )
        pipeline_run = run_research_brief(packet=packet, nodes=nodes)
        run_record = store.create_run(
            task_id=task["id"],
            run=asdict(pipeline_run),
            context_packet=asdict(packet),
        )
        store.update_task_status(task_id=task["id"], status=pipeline_run.status)
        return run_record

    @app.get("/runs/{run_id}/trace")
    def get_run_trace(run_id: str) -> dict:
        run = _get_run_or_404(store, run_id)
        return {"id": run["id"], "task_id": run["task_id"], "status": run["status"], "trace": run["trace"]}

    @app.get("/runs/{run_id}/context-packet")
    def get_context_packet(run_id: str) -> dict:
        run = _get_run_or_404(store, run_id)
        return {"id": run["id"], "task_id": run["task_id"], "context_packet": run["context_packet"]}

    return app


def _get_run_or_404(store: SQLiteStore, run_id: str) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run
