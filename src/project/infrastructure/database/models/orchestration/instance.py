from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:
    from .link import RunOrchestrationModel
    from .engine import EngineModel

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...base import Base
from ...mixins import TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin


class OrchestrationInstanceModel(Base, TimestampMixin, AuditMixin, VersionMixin, StatusTrackingMixin):
    """Orchestration Instance database model.

    Represents a specific workflow instance in an external engine.

    Attributes:
        engine_id (Mapped[UUID]): Foreign key to the engine.
        external_id (Mapped[str]): External system's identifier.
        duration_seconds (Mapped[Optional[int]]): Execution duration if known.
        metadata (Mapped[Optional[dict]]): Additional data from external system.
        is_active (Mapped[bool]): Soft delete flag.
        engine (Mapped["EngineModel"]): Related engine.
        runs (Mapped[List["RunOrchestrationModel"]]): Links to runs.
    """
    __tablename__ = "orchestration_instance"

    engine_id: Mapped[UUID] = mapped_column(
        ForeignKey("engine.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    instance_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    engine: Mapped["EngineModel"] = relationship(back_populates="instances")
    runs: Mapped[List["RunOrchestrationModel"]] = relationship(
        back_populates="orchestration_instance",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_orchestration_instance_engine_id", "engine_id"),
        Index("ix_orchestration_status_started", "status", "started_at"),
        Index("ix_orchestration_instance_is_active", "is_active"),
        UniqueConstraint("engine_id", "external_id", name="uq_orchestration_engine_external"),
    )
