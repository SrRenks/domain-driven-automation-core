from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func, Column, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declared_attr
from ...domain.enums import ExecutionStatus

class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps to a model.

    Attributes:
        created_at (Mapped[datetime]): Timestamp of creation (server default now).
        updated_at (Mapped[datetime]): Timestamp of last update (auto-updated).
    """
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AuditMixin:
    """Mixin that adds audit fields (created_by, updated_by).

    Attributes:
        created_by (Mapped[Optional[str]]): User who created the record.
        updated_by (Mapped[Optional[str]]): User who last updated the record.
    """
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    updated_by: Mapped[Optional[str]] = mapped_column(String(100))

class VersionMixin:
    """Mixin that adds an optimistic locking version field.

    Attributes:
        version (Mapped[int]): Version number, incremented on each update.
    """
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

class StatusTrackingMixin:
    """Mixin that adds standard execution status tracking fields.

    Attributes:
        status (Mapped[ExecutionStatus]): Current execution status.
        started_at (Mapped[Optional[datetime]]): When execution started.
        finished_at (Mapped[Optional[datetime]]): When execution finished.
    """
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLAlchemyEnum(ExecutionStatus, name="executionstatus", create_type=False),
        index=True,
        nullable=False,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds if both timestamps exist.

        Returns:
            Optional[float]: Duration in seconds, or None if not finished.
        """
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

class RetryableMixin:
    """Mixin that adds retry tracking capabilities.

    Attributes:
        attempt_count (Mapped[int]): Number of attempts made (default 0).
        max_attempts (Mapped[Optional[int]]): Maximum allowed attempts.
    """
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[Optional[int]] = mapped_column(Integer)

__all__ = [
    "TimestampMixin",
    "AuditMixin",
    "VersionMixin",
    "StatusTrackingMixin",
    "RetryableMixin",
]
