import asyncio
from pathlib import Path

import httpx

from agent_control_plane.api import create_app


DEMO_VAULT = Path(__file__).parents[1] / "examples" / "demo_vault"


class ApiClient:
    """Synchronous test facade over HTTPX's ASGI transport; no deprecated TestClient."""

    def __init__(self, app) -> None:
        self.app = app

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, path: str) -> httpx.Response:
        return self._request("GET", path)

    def post(self, path: str, json: dict | None = None) -> httpx.Response:
        return self._request("POST", path, json=json)

    def _request(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())


def create_client(tmp_path: Path) -> ApiClient:
    app = create_app(database_path=tmp_path / "control-plane.sqlite3", vault_path=DEMO_VAULT)
    return ApiClient(app)


def test_task_can_run_fixture_pipeline_and_expose_auditable_trace(tmp_path: Path):
    with create_client(tmp_path) as client:
        created = client.post(
            "/tasks",
            json={
                "project_id": "demo-research",
                "objective": "Create an evidence brief from public fixtures.",
            },
        )
        assert created.status_code == 201
        task = created.json()
        assert task["status"] == "DRAFT"

        run_response = client.post(f"/tasks/{task['id']}/run")
        assert run_response.status_code == 200
        run = run_response.json()
        assert run["status"] == "VERIFIED"
        assert len(run["evidence_cards"]) == 3
        assert all(claim["evidence_card_ids"] for claim in run["brief"]["claims"])

        trace_response = client.get(f"/runs/{run['id']}/trace")
        assert trace_response.status_code == 200
        assert [event["role"] for event in trace_response.json()["trace"]] == [
            "orchestrator",
            "research_worker",
            "brief_writer",
            "verification_worker",
        ]

        packet_response = client.get(f"/runs/{run['id']}/context-packet")
        assert packet_response.status_code == 200
        assert packet_response.json()["context_packet"]["source_scope"] == "public-fixtures-only"


def test_local_dashboard_is_served_with_a_real_fixture_run_control(tmp_path: Path):
    with create_client(tmp_path) as client:
        page = client.get("/")
        script = client.get("/static/app.js")

    assert page.status_code == 200
    assert "Evidence-First Agent Knowledge" in page.text
    assert "Run verified fixture" in page.text
    assert script.status_code == 200
    assert "runFixture" in script.text
    assert "event.detail" in script.text
    assert "card.excerpt" in script.text
    assert "escapeHtml" in script.text


def test_unknown_task_or_run_returns_404(tmp_path: Path):
    with create_client(tmp_path) as client:
        assert client.post("/tasks/missing/run").status_code == 404
        assert client.get("/runs/missing/trace").status_code == 404


def test_task_without_scoped_public_knowledge_is_rejected_before_a_run(tmp_path: Path):
    with create_client(tmp_path) as client:
        created = client.post(
            "/tasks",
            json={"project_id": "unknown-project", "objective": "Create a brief."},
        )

        response = client.post(f"/tasks/{created.json()['id']}/run")

    assert response.status_code == 422
    assert response.json()["detail"] == "No public knowledge is available for this project."
