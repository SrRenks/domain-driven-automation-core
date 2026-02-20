from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from ..base import DomainEntity
from ..enums import ExecutionStatus
from ..exceptions.domain import ValidationError, InvalidStateError


@dataclass
class Engine(DomainEntity):
    """Engine domain entity - represents external orchestration systems (Jenkins, Argo, etc.).

    Attributes:
        name (str): Unique identifier for the engine (stripped).
        type (str): Engine type classification (stripped).
    """
    name: str
    type: str

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If name or type is empty.
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Engine", "name", "cannot be empty")
        if not self.type or not self.type.strip():
            raise ValidationError("Engine", "type", "cannot be empty")

        self.name = self.name.strip()
        self.type = self.type.strip()


@dataclass
class OrchestrationInstance(DomainEntity):
    """Orchestration Instance domain entity - external workflow instance.

    Attributes:
        engine_id (UUID): Reference to parent Engine.
        external_id (str): External system's identifier (stripped).
        duration_seconds (Optional[int]): Execution duration in seconds.
        instance_metadata (Optional[Dict[str, Any]]): Additional data from external system.
        status (ExecutionStatus): Current status (default PENDING).
        started_at (Optional[datetime]): When execution started.
        finished_at (Optional[datetime]): When execution finished.
    """
    engine_id: UUID
    external_id: str
    duration_seconds: Optional[int] = None
    instance_metadata: Optional[Dict[str, Any]] = None

    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If engine_id missing or external_id empty.
        """
        if not self.engine_id:
            raise ValidationError("OrchestrationInstance", "engine_id", "is required")
        if not self.external_id or not self.external_id.strip():
            raise ValidationError("OrchestrationInstance", "external_id", "cannot be empty")
        self.external_id = self.external_id.strip()

    def start(self) -> None:
        """Start the orchestration instance.

        Raises:
            InvalidStateError: If not in PENDING state.
        """
        if self.status != ExecutionStatus.PENDING:
            raise InvalidStateError("OrchestrationInstance", self.id, self.status.value, "start")
        self.status = ExecutionStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self._bump_version()

    def complete(self) -> None:
        """Mark orchestration instance as completed.

        Calculates duration if started_at is set.

        Raises:
            InvalidStateError: If not in PROCESSING state.
        """
        if self.status != ExecutionStatus.PROCESSING:
            raise InvalidStateError("OrchestrationInstance", self.id, self.status.value, "complete")
        self.status = ExecutionStatus.COMPLETED
        self.finished_at = datetime.now(timezone.utc)
        if self.started_at is not None:
            self.duration_seconds = int((self.finished_at - self.started_at).total_seconds())
        self._bump_version()

    def fail(self) -> None:
        """Mark orchestration instance as failed.

        Raises:
            InvalidStateError: If not in PROCESSING state.
        """
        if self.status != ExecutionStatus.PROCESSING:
            raise InvalidStateError("OrchestrationInstance", self.id, self.status.value, "fail")
        self.status = ExecutionStatus.FAILED
        self.finished_at = datetime.now(timezone.utc)
        self._bump_version()


@dataclass
class RunOrchestration(DomainEntity):
    """Run Orchestration link domain entity - connects runs to orchestration instances.

    Attributes:
        run_id (UUID): Reference to Run.
        orchestration_instance_id (UUID): Reference to OrchestrationInstance.
        attached_at (datetime): When the link was established (default now).
    """
    run_id: UUID
    orchestration_instance_id: UUID
    attached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate after initialization.

        Raises:
            ValidationError: If run_id or orchestration_instance_id is missing.
        """
        if not self.run_id:
            raise ValidationError("RunOrchestration", "run_id", "is required")
        if not self.orchestration_instance_id:
            raise ValidationError("RunOrchestration", "orchestration_instance_id", "is required")
