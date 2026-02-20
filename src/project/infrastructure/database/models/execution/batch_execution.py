from __future__ import annotations

from typing import List, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from . import RunModel, ItemExecutionModel
    from ..definition.batch import BatchModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Index, UniqueConstraint, Boolean, text

from ...mixins import TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin
from ...base import Base


class BatchExecutionModel(Base, TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin):
    """Batch Execution database model.

    Tracks the execution status of a specific batch within a run.

    Attributes:
        run_id (Mapped[UUID]): Foreign key to parent run.
        batch_id (Mapped[UUID]): Foreign key to the batch being executed.
        is_active (Mapped[bool]): Soft delete flag.
        run (Mapped["RunModel"]): Parent run relationship.
        batch (Mapped["BatchModel"]): Related batch.
        item_executions (Mapped[List["ItemExecutionModel"]]): Item executions in this batch execution.
    """
    __tablename__ = "batch_execution"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("run.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    run: Mapped["RunModel"] = relationship(back_populates="batch_executions")
    batch: Mapped["BatchModel"] = relationship(back_populates="executions")

    item_executions: Mapped[List["ItemExecutionModel"]] = relationship(
        back_populates="batch_execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("run_id", "batch_id", name="uq_batch_execution_run_batch"),
        Index("ix_batch_execution_is_active", "is_active"),
    )
