from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Index, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...base import Base
from ...mixins import TimestampMixin, AuditMixin, VersionMixin

if TYPE_CHECKING:
    from . import OrchestrationInstanceModel
    from ..execution.run import RunModel

class RunOrchestrationModel(Base, TimestampMixin, AuditMixin, VersionMixin):
    """Run Orchestration link database model.

    Connects runs to orchestration instances (many-to-many).

    Attributes:
        run_id (Mapped[UUID]): Foreign key to the run.
        orchestration_instance_id (Mapped[UUID]): Foreign key to the orchestration instance.
        attached_at (Mapped[datetime]): When the link was established.
        is_active (Mapped[bool]): Soft delete flag.
        run (Mapped["RunModel"]): Related run.
        orchestration_instance (Mapped["OrchestrationInstanceModel"]): Related orchestration instance.
    """
    __tablename__ = "run_orchestration"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("run.id", ondelete="CASCADE"),
        nullable=False,
    )
    orchestration_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("orchestration_instance.id", ondelete="CASCADE"),
        nullable=False,
    )

    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    run: Mapped["RunModel"] = relationship(back_populates="orchestration")
    orchestration_instance: Mapped["OrchestrationInstanceModel"] = relationship(back_populates="runs")

    __table_args__ = (
        Index("ix_run_orchestration_run_id", "run_id"),
        Index("ix_run_orchestration_instance_id", "orchestration_instance_id"),
        Index("ix_run_orchestration_is_active", "is_active"),
        UniqueConstraint("run_id", "orchestration_instance_id", name="uq_run_orchestration"),
    )