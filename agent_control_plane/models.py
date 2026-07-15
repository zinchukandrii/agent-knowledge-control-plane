"""Typed contracts for the P2 control-plane core."""

from dataclasses import dataclass

from .state import TaskStatus


@dataclass(frozen=True)
class KnowledgeNode:
    """A Markdown-backed, explicitly scoped item of project knowledge."""

    id: str
    node_type: str
    project_id: str
    source: str
    review_status: str
    sensitivity: str
    content: str


@dataclass(frozen=True)
class ContextPacket:
    """The minimum context a bounded worker may receive for one task."""

    task_id: str
    project_id: str
    objective: str
    knowledge_node_ids: tuple[str, ...]
    source_scope: str
    allowed_actions: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceCard:
    """A candidate evidence record derived from one scoped knowledge node."""

    id: str
    source_node_id: str
    source: str
    excerpt: str


@dataclass(frozen=True)
class Claim:
    """A candidate brief statement and the evidence cards that support it."""

    id: str
    text: str
    evidence_card_ids: tuple[str, ...]


@dataclass(frozen=True)
class CandidateBrief:
    """A worker-produced artifact that remains untrusted until verification."""

    task_id: str
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class TraceEvent:
    """One auditable, deterministic control-plane event."""

    role: str
    outcome: str
    detail: str


@dataclass(frozen=True)
class PipelineRun:
    """The immutable output of a bounded local research workflow."""

    task_id: str
    status: TaskStatus
    evidence_cards: tuple[EvidenceCard, ...]
    brief: CandidateBrief | None
    verification_defects: tuple[str, ...]
    trace: tuple[TraceEvent, ...]
