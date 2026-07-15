import pytest

from agent_control_plane.state import TaskStateError, TaskStatus, transition


def test_task_moves_through_verified_local_artifact_lifecycle():
    status = TaskStatus.DRAFT
    for next_status in (
        TaskStatus.PLANNED,
        TaskStatus.RUNNING,
        TaskStatus.EVIDENCE_PENDING,
        TaskStatus.VERIFIED,
        TaskStatus.COMPLETED,
    ):
        status = transition(status, next_status)

    assert status is TaskStatus.COMPLETED


def test_state_machine_fails_closed_for_invalid_transition():
    with pytest.raises(TaskStateError, match="DRAFT.*VERIFIED"):
        transition(TaskStatus.DRAFT, TaskStatus.VERIFIED)


def test_verified_external_action_requires_human_approval():
    assert transition(TaskStatus.VERIFIED, TaskStatus.APPROVAL_REQUIRED) is TaskStatus.APPROVAL_REQUIRED
