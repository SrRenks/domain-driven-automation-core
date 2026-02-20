from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


class DomainEvent:
    """Base class for all domain events."""
    pass

@dataclass
class ItemExecutionFailed(DomainEvent):
    """Event emitted when an item execution fails permanently or enters retry state.

    Attributes:
        item_execution_id (UUID): ID of the failing item execution.
        run_id (UUID): ID of the parent run.
        item_id (UUID): ID of the item.
        error_message (str): Details of the failure.
        attempt_count (int): Number of attempts made.
        timestamp (datetime): When the event occurred.
    """
    item_execution_id: UUID
    run_id: UUID
    item_id: UUID
    error_message: str
    attempt_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class RunCompleted(DomainEvent):
    """Event emitted when a run completes successfully.

    Attributes:
        run_id (UUID): ID of the completed run.
        automation_id (UUID): ID of the automation.
        finished_at (datetime): Completion timestamp.
        timestamp (datetime): When the event occurred.
    """
    run_id: UUID
    automation_id: UUID
    finished_at: datetime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class RunFailed(DomainEvent):
    """Event emitted when a run fails.

    Attributes:
        run_id (UUID): ID of the failed run.
        automation_id (UUID): ID of the automation.
        error_summary (str): High-level error description.
        finished_at (datetime): Failure timestamp.
        timestamp (datetime): When the event occurred.
    """
    run_id: UUID
    automation_id: UUID
    error_summary: str
    finished_at: datetime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RunCancelled(DomainEvent):
    """Event emitted when a run is cancelled.

    Attributes:
        run_id (UUID): ID of the cancelled run.
        automation_id (UUID): ID of the automation.
        cancellation_reason (str): Why it was cancelled.
        finished_at (datetime): Cancellation timestamp.
        timestamp (datetime): When the event occurred.
    """
    run_id: UUID
    automation_id: UUID
    cancellation_reason: str
    finished_at: datetime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class BatchExecutionFailed(DomainEvent):
    """Event emitted when a batch execution fails.

    Attributes:
        batch_execution_id (UUID): ID of the failing batch execution.
        run_id (UUID): ID of the parent run.
        batch_id (UUID): ID of the batch.
        finished_at (datetime): Failure timestamp.
        timestamp (datetime): When the event occurred.
    """
    batch_execution_id: UUID
    run_id: UUID
    batch_id: UUID
    finished_at: datetime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
