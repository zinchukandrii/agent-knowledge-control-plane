from pathlib import Path

import pytest

from agent_control_plane.knowledge import ScopeViolation, build_context_packet, load_nodes


def write_node(path: Path, *, node_id: str, project_id: str, sensitivity: str) -> None:
    path.write_text(
        f"""---
id: {node_id}
node_type: document
project_id: {project_id}
source: authored-fixture
review_status: reviewed
sensitivity: {sensitivity}
---
# {node_id}

Fixture content.
""",
        encoding="utf-8",
    )


def test_loads_public_markdown_node_with_metadata(tmp_path: Path):
    write_node(tmp_path / "overview.md", node_id="project-overview", project_id="demo", sensitivity="public")

    nodes = load_nodes(tmp_path)

    assert [node.id for node in nodes] == ["project-overview"]
    assert nodes[0].content == "# project-overview\n\nFixture content."


def test_context_packet_keeps_only_public_nodes_for_requested_project(tmp_path: Path):
    write_node(tmp_path / "overview.md", node_id="overview", project_id="demo", sensitivity="public")
    write_node(tmp_path / "private.md", node_id="private-note", project_id="demo", sensitivity="private")
    write_node(tmp_path / "other.md", node_id="other-project", project_id="other", sensitivity="public")

    packet = build_context_packet(
        task_id="task-demo-001",
        project_id="demo",
        objective="Create an evidence brief.",
        nodes=load_nodes(tmp_path),
    )

    assert packet.knowledge_node_ids == ("overview",)
    assert packet.source_scope == "public-fixtures-only"


def test_context_packet_fails_closed_when_requested_node_is_not_public(tmp_path: Path):
    write_node(tmp_path / "private.md", node_id="private-note", project_id="demo", sensitivity="private")

    with pytest.raises(ScopeViolation, match="private-note"):
        build_context_packet(
            task_id="task-demo-001",
            project_id="demo",
            objective="Create an evidence brief.",
            nodes=load_nodes(tmp_path),
            required_node_ids=("private-note",),
        )


def test_public_demo_vault_builds_a_scoped_context_packet():
    vault = Path(__file__).parents[1] / "examples" / "demo_vault"

    packet = build_context_packet(
        task_id="task-demo-001",
        project_id="demo-research",
        objective="Create an evidence brief.",
        nodes=load_nodes(vault),
    )

    assert packet.knowledge_node_ids == (
        "dec-public-fixtures-only",
        "project-demo-research",
        "skill-citation-check",
    )
