"""Deterministic, provider-free bounded worker pipeline for public fixtures."""

from collections.abc import Callable

from .models import (
    CandidateBrief,
    Claim,
    ContextPacket,
    EvidenceCard,
    KnowledgeNode,
    PipelineRun,
    TraceEvent,
)
from .state import TaskStatus, transition

_REQUIRED_ACTIONS = ("retrieve", "summarize", "cite")
_PUBLIC_FIXTURE_SCOPE = "public-fixtures-only"


class PolicyViolation(ValueError):
    """Raised when a worker packet violates a fail-closed policy boundary."""


def _validate_packet(packet: ContextPacket) -> None:
    if packet.source_scope != _PUBLIC_FIXTURE_SCOPE:
        raise PolicyViolation(f"Unsupported source scope: {packet.source_scope}")
    allowed = set(packet.allowed_actions)
    for action in _REQUIRED_ACTIONS:
        if action not in allowed:
            raise PolicyViolation(f"Worker action is forbidden: {action}")


def _select_scoped_nodes(packet: ContextPacket, nodes: list[KnowledgeNode]) -> tuple[KnowledgeNode, ...]:
    nodes_by_id = {node.id: node for node in nodes}
    selected: list[KnowledgeNode] = []
    for node_id in packet.knowledge_node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            raise PolicyViolation(f"Packet references an unknown knowledge node: {node_id}")
        if node.project_id != packet.project_id or node.sensitivity != "public":
            raise PolicyViolation(f"Packet node is outside public project scope: {node_id}")
        selected.append(node)
    return tuple(selected)


def _research(nodes: tuple[KnowledgeNode, ...]) -> tuple[EvidenceCard, ...]:
    return tuple(
        EvidenceCard(
            id=f"evidence-{node.id}",
            source_node_id=node.id,
            source=node.source,
            excerpt=node.content,
        )
        for node in nodes
    )


def _write_brief(task_id: str, evidence_cards: tuple[EvidenceCard, ...]) -> CandidateBrief:
    claims = tuple(
        Claim(
            id=f"claim-{index}",
            text=card.excerpt,
            evidence_card_ids=(card.id,),
        )
        for index, card in enumerate(evidence_cards, start=1)
    )
    return CandidateBrief(task_id=task_id, claims=claims)


def _verify(brief: CandidateBrief, evidence_cards: tuple[EvidenceCard, ...]) -> tuple[str, ...]:
    evidence_ids = {card.id for card in evidence_cards}
    defects: list[str] = []
    for claim in brief.claims:
        if not claim.evidence_card_ids:
            defects.append(f"{claim.id}: missing evidence")
            continue
        unknown_ids = sorted(set(claim.evidence_card_ids) - evidence_ids)
        if unknown_ids:
            defects.append(f"{claim.id}: unknown evidence: {', '.join(unknown_ids)}")
    return tuple(defects)


def run_research_brief(
    *,
    packet: ContextPacket,
    nodes: list[KnowledgeNode],
    claim_mutator: Callable[[tuple[Claim, ...]], tuple[Claim, ...]] | None = None,
) -> PipelineRun:
    """Run research → candidate brief → independent verification with no side effects."""
    _validate_packet(packet)
    status = transition(TaskStatus.DRAFT, TaskStatus.PLANNED)
    trace = [TraceEvent("orchestrator", status.value, "Validated packet policy and created local plan.")]

    scoped_nodes = _select_scoped_nodes(packet, nodes)
    status = transition(status, TaskStatus.RUNNING)
    evidence_cards = _research(scoped_nodes)
    trace.append(
        TraceEvent(
            "research_worker",
            "CANDIDATE",
            f"Produced {len(evidence_cards)} evidence cards from scoped public nodes.",
        )
    )

    brief = _write_brief(packet.task_id, evidence_cards)
    if claim_mutator is not None:
        brief = CandidateBrief(task_id=brief.task_id, claims=claim_mutator(brief.claims))
    status = transition(status, TaskStatus.EVIDENCE_PENDING)
    trace.append(
        TraceEvent("brief_writer", "CANDIDATE", f"Produced {len(brief.claims)} claims from evidence cards.")
    )

    defects = _verify(brief, evidence_cards)
    if defects:
        status = transition(status, TaskStatus.BLOCKED)
        trace.append(TraceEvent("verification_worker", status.value, "; ".join(defects)))
    else:
        status = transition(status, TaskStatus.VERIFIED)
        trace.append(TraceEvent("verification_worker", status.value, "All claims have known evidence."))

    return PipelineRun(
        task_id=packet.task_id,
        status=status,
        evidence_cards=evidence_cards,
        brief=brief,
        verification_defects=defects,
        trace=tuple(trace),
    )
