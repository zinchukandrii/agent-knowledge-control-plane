"""Fail-closed task lifecycle for local agent runs."""

from enum import Enum


class TaskStateError(ValueError):
    """Raised when a task attempts an unauthorized lifecycle transition."""


class TaskStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    VERIFIED = "VERIFIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    NEEDS_INPUT = "NEEDS_INPUT"
    CANCELLED = "CANCELLED"


_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.DRAFT: frozenset({TaskStatus.PLANNED, TaskStatus.CANCELLED}),
    TaskStatus.PLANNED: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.EVIDENCE_PENDING, TaskStatus.FAILED, TaskStatus.CANCELLED}
    ),
    TaskStatus.EVIDENCE_PENDING: frozenset({TaskStatus.VERIFIED, TaskStatus.BLOCKED}),
    TaskStatus.VERIFIED: frozenset({TaskStatus.COMPLETED, TaskStatus.APPROVAL_REQUIRED}),
    TaskStatus.APPROVAL_REQUIRED: frozenset({TaskStatus.COMPLETED, TaskStatus.CANCELLED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.NEEDS_INPUT, TaskStatus.CANCELLED}),
    TaskStatus.NEEDS_INPUT: frozenset({TaskStatus.PLANNED, TaskStatus.CANCELLED}),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def transition(current: TaskStatus, target: TaskStatus) -> TaskStatus:
    """Return an allowed target state or reject the transition explicitly."""
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise TaskStateError(f"Invalid task transition: {current.value} -> {target.value}")
    return target
