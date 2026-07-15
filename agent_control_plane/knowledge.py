"""Markdown knowledge loading and fail-closed context scoping."""

from pathlib import Path

from .models import ContextPacket, KnowledgeNode

_REQUIRED_METADATA = {
    "id",
    "node_type",
    "project_id",
    "source",
    "review_status",
    "sensitivity",
}
_PUBLIC_SENSITIVITY = "public"
_ALLOWED_ACTIONS = ("retrieve", "summarize", "cite")


class KnowledgeFormatError(ValueError):
    """Raised for a malformed knowledge node."""


class ScopeViolation(ValueError):
    """Raised when task context would include disallowed knowledge."""


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise KnowledgeFormatError("Knowledge node must start with YAML frontmatter")

    try:
        _, raw_metadata, body = text.split("---\n", maxsplit=2)
    except ValueError as exc:
        raise KnowledgeFormatError("Knowledge node frontmatter is not closed") from exc

    metadata: dict[str, str] = {}
    for line in raw_metadata.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise KnowledgeFormatError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", maxsplit=1)
        metadata[key.strip()] = value.strip()

    missing = sorted(_REQUIRED_METADATA - metadata.keys())
    if missing:
        raise KnowledgeFormatError(f"Knowledge node missing metadata: {', '.join(missing)}")
    return metadata, body.strip()


def load_nodes(vault_path: Path) -> list[KnowledgeNode]:
    """Load Markdown nodes in deterministic path order."""
    nodes: list[KnowledgeNode] = []
    for path in sorted(vault_path.rglob("*.md")):
        metadata, content = _parse_frontmatter(path.read_text(encoding="utf-8"))
        nodes.append(KnowledgeNode(content=content, **metadata))
    return nodes


def build_context_packet(
    *,
    task_id: str,
    project_id: str,
    objective: str,
    nodes: list[KnowledgeNode],
    required_node_ids: tuple[str, ...] = (),
) -> ContextPacket:
    """Build a public-only, single-project packet for a bounded worker."""
    nodes_by_id = {node.id: node for node in nodes}

    if required_node_ids:
        selected: list[KnowledgeNode] = []
        for node_id in required_node_ids:
            node = nodes_by_id.get(node_id)
            if node is None:
                raise ScopeViolation(f"Required knowledge node does not exist: {node_id}")
            if node.project_id != project_id or node.sensitivity != _PUBLIC_SENSITIVITY:
                raise ScopeViolation(f"Required knowledge node is outside allowed scope: {node_id}")
            selected.append(node)
    else:
        selected = [
            node
            for node in nodes
            if node.project_id == project_id and node.sensitivity == _PUBLIC_SENSITIVITY
        ]

    return ContextPacket(
        task_id=task_id,
        project_id=project_id,
        objective=objective,
        knowledge_node_ids=tuple(node.id for node in selected),
        source_scope="public-fixtures-only",
        allowed_actions=_ALLOWED_ACTIONS,
    )
