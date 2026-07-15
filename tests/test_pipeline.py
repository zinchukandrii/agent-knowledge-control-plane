from pathlib import Path

import pytest

from agent_control_plane.knowledge import build_context_packet, load_nodes
from agent_control_plane.models import Claim
from agent_control_plane.pipeline import PolicyViolation, run_research_brief
from agent_control_plane.state import TaskStatus


@pytest.fixture
def demo_packet():
    vault = Path(__file__).parents[1] / "examples" / "demo_vault"
    nodes = load_nodes(vault)
    packet = build_context_packet(
        task_id="task-demo-002",
        project_id="demo-research",
        objective="Create an evidence brief from public fixtures.",
        nodes=nodes,
    )
    return packet, nodes


def test_fixture_pipeline_verifies_a_brief_with_evidence_backed_claims(demo_packet):
    packet, nodes = demo_packet

    run = run_research_brief(packet=packet, nodes=nodes)

    assert run.status is TaskStatus.VERIFIED
    assert len(run.evidence_cards) == 3
    assert run.brief is not None
    assert all(claim.evidence_card_ids for claim in run.brief.claims)
    assert [event.role for event in run.trace] == [
        "orchestrator",
        "research_worker",
        "brief_writer",
        "verification_worker",
    ]


def test_pipeline_blocks_an_unsupported_claim_and_records_exact_defect(demo_packet):
    packet, nodes = demo_packet

    def add_unsupported_claim(claims: tuple[Claim, ...]) -> tuple[Claim, ...]:
        return claims + (
            Claim(
                id="claim-unsupported",
                text="This claim has no evidence card.",
                evidence_card_ids=(),
            ),
        )

    run = run_research_brief(packet=packet, nodes=nodes, claim_mutator=add_unsupported_claim)

    assert run.status is TaskStatus.BLOCKED
    assert run.brief is not None
    assert run.verification_defects == ("claim-unsupported: missing evidence",)
    assert run.trace[-1].outcome == "BLOCKED"


def test_pipeline_rejects_packet_without_required_worker_actions(demo_packet):
    packet, nodes = demo_packet
    restricted_packet = packet.__class__(
        task_id=packet.task_id,
        project_id=packet.project_id,
        objective=packet.objective,
        knowledge_node_ids=packet.knowledge_node_ids,
        source_scope=packet.source_scope,
        allowed_actions=("retrieve", "summarize"),
    )

    with pytest.raises(PolicyViolation, match="cite"):
        run_research_brief(packet=restricted_packet, nodes=nodes)
