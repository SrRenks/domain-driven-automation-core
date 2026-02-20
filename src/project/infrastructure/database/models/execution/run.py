from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from . import BatchExecutionModel, ItemExecutionModel
    from ..definition.automation import AutomationModel
    from ..orchestration.link import RunOrchestrationModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Index, String, Text, Boolean, text

from ...mixins import TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin
from ...base import Base

class RunModel(Base, TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin):
    """Run database model.

    Represents a single execution instance of an automation.

    Attributes:
        automation_id (Mapped[UUID]): Foreign key to the automation being executed.
        correlation_id (Mapped[Optional[str]]): External tracking identifier.
        cancellation_reason (Mapped[Optional[str]]): Reason for cancellation.
        error_summary (Mapped[Optional[str]]): High-level error description.
        is_active (Mapped[bool]): Soft delete flag.
        automation (Mapped["AutomationModel"]): Related automation.
        batch_executions (Mapped[List["BatchExecutionModel"]]): Batch executions in this run.
        item_executions (Mapped[List["ItemExecutionModel"]]): Item executions in this run.
        orchestration (Mapped[List["RunOrchestrationModel"]]): Links to orchestration instances.
    """
    __tablename__ = "run"

    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text)
    error_summary: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    automation: Mapped["AutomationModel"] = relationship(back_populates="runs")

    batch_executions: Mapped[List["BatchExecutionModel"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    item_executions: Mapped[List["ItemExecutionModel"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    orchestration: Mapped[List["RunOrchestrationModel"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_run_started_status", "started_at", "status"),
        Index("ix_run_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the run model.

        Returns:
            str: Representation including truncated id and status.
        """
        return f"<RunModel #{str(self.id)[:8]} status={self.status}>"
