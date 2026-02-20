from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from ..base import DomainEntity
from ..enums import ExecutionStatus
from ..exceptions.domain import ValidationError, InvalidStateError
from ..events import ItemExecutionFailed, RunCompleted, RunFailed, RunCancelled, BatchExecutionFailed

@dataclass
class Run(DomainEntity):
    """Run domain entity - execution instance of an automation.

    Tracks overall execution lifecycle, status transitions, errors, and performance.

    Attributes:
        automation_id (UUID): Reference to parent Automation.
        correlation_id (Optional[str]): External tracking ID.
        cancellation_reason (Optional[str]): Reason for cancellation.
        error_summary (Optional[str]): High-level error description.
        status (ExecutionStatus): Current status (default PENDING).
        started_at (Optional[datetime]): When execution started.
        finished_at (Optional[datetime]): When execution finished.
    """
    automation_id: UUID
    correlation_id: Optional[str] = None
    cancellation_reason: Optional[str] = None
    error_summary: Optional[str] = None

    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If automation_id is missing.
        """
        if not self.automation_id:
            raise ValidationError("Run", "automation_id", "is required")

    def start(self) -> None:
        """Transition run to PROCESSING state.

        Raises:
            InvalidStateError: If transition from current status is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.PROCESSING):
            raise InvalidStateError("Run", self.id, self.status.value, "start")
        self.status = ExecutionStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self._bump_version()

    def complete(self) -> None:
        """Mark run as completed.

        Emits RunCompleted event.

        Raises:
            InvalidStateError: If transition to COMPLETED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.COMPLETED):
            raise InvalidStateError("Run", self.id, self.status.value, "complete")
        self.status = ExecutionStatus.COMPLETED
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()
        self.register_event(RunCompleted(
            run_id=self.id,
            automation_id=self.automation_id,
            finished_at=self.finished_at
        ))

    def fail(self, error_summary: str) -> None:
        """Mark run as failed.

        Emits RunFailed event.

        Args:
            error_summary (str): High-level error description.

        Raises:
            InvalidStateError: If transition to FAILED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.FAILED):
            raise InvalidStateError("Run", self.id, self.status.value, "fail")
        self.status = ExecutionStatus.FAILED
        self.error_summary = error_summary
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()
        self.register_event(RunFailed(
            run_id=self.id,
            automation_id=self.automation_id,
            error_summary=error_summary,
            finished_at=self.finished_at
        ))

    def cancel(self, reason: str) -> None:
        """Cancel the run.

        Emits RunCancelled event.

        Args:
            reason (str): Reason for cancellation.

        Raises:
            InvalidStateError: If transition to CANCELLED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.CANCELLED):
            raise InvalidStateError("Run", self.id, self.status.value, "cancel")
        self.status = ExecutionStatus.CANCELLED
        self.cancellation_reason = reason
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()
        self.register_event(RunCancelled(
            run_id=self.id,
            automation_id=self.automation_id,
            cancellation_reason=reason,
            finished_at=self.finished_at
        ))


@dataclass
class BatchExecution(DomainEntity):
    """Batch Execution domain entity - tracks batch-level execution.

    Attributes:
        run_id (UUID): Reference to parent Run.
        batch_id (UUID): Reference to Batch being executed.
        status (ExecutionStatus): Current status (default PENDING).
        started_at (Optional[datetime]): When execution started.
        finished_at (Optional[datetime]): When execution finished.
    """
    run_id: UUID
    batch_id: UUID

    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If run_id or batch_id is missing.
        """
        if not self.run_id:
            raise ValidationError("BatchExecution", "run_id", "is required")
        if not self.batch_id:
            raise ValidationError("BatchExecution", "batch_id", "is required")

    def start(self) -> None:
        """Transition batch execution to PROCESSING state.

        Raises:
            InvalidStateError: If transition from current status is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.PROCESSING):
            raise InvalidStateError("BatchExecution", self.id, self.status.value, "start")
        self.status = ExecutionStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self._bump_version()

    def complete(self) -> None:
        """Mark batch execution as completed.

        Raises:
            InvalidStateError: If transition to COMPLETED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.COMPLETED):
            raise InvalidStateError("BatchExecution", self.id, self.status.value, "complete")
        self.status = ExecutionStatus.COMPLETED
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()

    def fail(self) -> None:
        """Mark batch execution as failed.

        Emits BatchExecutionFailed event.

        Raises:
            InvalidStateError: If transition to FAILED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.FAILED):
            raise InvalidStateError("BatchExecution", self.id, self.status.value, "fail")
        self.status = ExecutionStatus.FAILED
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()
        self.register_event(BatchExecutionFailed(
            batch_execution_id=self.id,
            run_id=self.run_id,
            batch_id=self.batch_id,
            finished_at=self.finished_at
        ))


@dataclass
class ItemExecution(DomainEntity):
    """Item Execution domain entity - tracks individual item execution with retry support.

    Attributes:
        run_id (UUID): Reference to parent Run.
        batch_execution_id (UUID): Reference to parent BatchExecution.
        item_id (UUID): Reference to Item being executed.
        result_payload (Optional[Dict[str, Any]]): Output from successful execution.
        error_message (Optional[str]): Error details if failed.
        status (ExecutionStatus): Current status (default PENDING).
        started_at (Optional[datetime]): When execution started.
        finished_at (Optional[datetime]): When execution finished.
        attempt_count (int): Number of attempts made (default 0).
        max_attempts (Optional[int]): Maximum allowed attempts.
    """
    run_id: UUID
    batch_execution_id: UUID
    item_id: UUID
    result_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    attempt_count: int = 0
    max_attempts: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If required IDs missing or max_attempts < 0.
        """
        if not self.run_id:
            raise ValidationError("ItemExecution", "run_id", "is required")
        if not self.batch_execution_id:
            raise ValidationError("ItemExecution", "batch_execution_id", "is required")
        if not self.item_id:
            raise ValidationError("ItemExecution", "item_id", "is required")
        if self.max_attempts is not None and self.max_attempts < 0:
            raise ValidationError("ItemExecution", "max_attempts", "must be >= 0")

    def start(self) -> None:
        """Start (or retry) item execution.

        Increments attempt_count and transitions to PROCESSING.

        Raises:
            InvalidStateError: If max attempts already reached or transition not allowed.
        """
        if self.max_attempts is not None and self.attempt_count >= self.max_attempts:
            raise InvalidStateError(
                "ItemExecution", self.id, self.status.value,
                f"start (max attempts {self.max_attempts} already reached)"
            )
        if not self.status.can_transition_to(ExecutionStatus.PROCESSING):
            raise InvalidStateError("ItemExecution", self.id, self.status.value, "start")
        self.status = ExecutionStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self.attempt_count += 1
        self._bump_version()

    def complete(self, result_payload: Optional[Dict[str, Any]] = None) -> None:
        """Mark item execution as completed.

        Args:
            result_payload (Optional[Dict[str, Any]]): Output data.

        Raises:
            InvalidStateError: If transition to COMPLETED is not allowed.
        """
        if not self.status.can_transition_to(ExecutionStatus.COMPLETED):
            raise InvalidStateError("ItemExecution", self.id, self.status.value, "complete")
        self.status = ExecutionStatus.COMPLETED
        self.result_payload = result_payload
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()

    def fail(self, error_message: str) -> None:
        """Fail the item execution.

        If retries are allowed and attempts remain, transitions to RETRYING;
        otherwise to FAILED. Emits ItemExecutionFailed event.

        Args:
            error_message (str): Details of the failure.

        Raises:
            InvalidStateError: If transition to target status is not allowed.
        """
        self.error_message = error_message

        if self.max_attempts is not None and self.attempt_count < self.max_attempts:
            target_status = ExecutionStatus.RETRYING
        else:
            target_status = ExecutionStatus.FAILED

        if not self.status.can_transition_to(target_status):
            raise InvalidStateError(
                "ItemExecution",
                self.id,
                self.status.value,
                f"transition to {target_status.value}"
            )

        self.status = target_status
        if target_status == ExecutionStatus.FAILED:
            self.finished_at = datetime.now(timezone.utc)

        self._bump_version()
        self.register_event(ItemExecutionFailed(
            item_execution_id=self.id,
            run_id=self.run_id,
            item_id=self.item_id,
            error_message=error_message,
            attempt_count=self.attempt_count
        ))

    def can_retry(self) -> bool:
        """Check if the item can be retried based on max_attempts.

        Returns:
            bool: True if max_attempts is set and attempts < max_attempts.
        """
        return (self.max_attempts is not None and self.attempt_count < self.max_attempts)

@dataclass
class ItemStateHistory:
    """Immutable audit record of a state change for an item execution.

    Attributes:
        item_execution_id (UUID): Reference to ItemExecution.
        new_status (ExecutionStatus): New status after transition.
        id (UUID): Unique identifier (automatically generated).
        previous_status (Optional[ExecutionStatus]): Status before transition.
        changed_at (datetime): Timestamp of state transition.
        created_at (datetime): Timestamp of record creation.
        created_by (Optional[str]): User who triggered the transition.
    """
    item_execution_id: UUID
    new_status: ExecutionStatus
    id: UUID = field(default_factory=uuid4)
    previous_status: Optional[ExecutionStatus] = None
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None

    def __post_init__(self):
        """Validate required fields.

        Raises:
            ValidationError: If item_execution_id or new_status is missing.
        """
        if not self.item_execution_id:
            raise ValidationError("ItemStateHistory", "item_execution_id", "is required")
        if not self.new_status:
            raise ValidationError("ItemStateHistory", "new_status", "is required")