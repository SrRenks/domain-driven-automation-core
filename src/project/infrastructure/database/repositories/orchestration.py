from uuid import UUID
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...uow.unit_of_work import UnitOfWork

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ....domain.entities.orchestration import (
    Engine, OrchestrationInstance, RunOrchestration
)
from ....domain.enums import ExecutionStatus
from ...database.models.orchestration import (
    EngineModel, OrchestrationInstanceModel, RunOrchestrationModel
)
from .base import BaseRepository


class EngineRepository(BaseRepository[EngineModel, Engine]):
    """Repository for Engine entities.

    Provides methods specific to Engine, including lookup by name and type.
    """
    updatable_fields = ['name', 'type', 'is_active']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, EngineModel, Engine, uow)

    def get_by_name(self, name: str, include_soft_deleted: bool = False) -> Optional[Engine]:
        """Retrieve an engine by its unique name.

        Args:
            name (str): Engine name.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[Engine]: The engine if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.name == name
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_type(self, engine_type: str,
                     include_soft_deleted: bool = False,
                     limit: int = 100,
                     offset: int = 0) -> List[Engine]:
        """List all engines by type with pagination.

        Args:
            engine_type (str): Type to filter by.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[Engine]: List of engines.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.type == engine_type
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.name.asc(),
            self.model_class.id.asc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: EngineModel) -> Engine:
        """Convert an EngineModel to an Engine domain entity.

        Args:
            model (EngineModel): The SQLAlchemy model.

        Returns:
            Engine: The corresponding domain entity.
        """
        entity = Engine(
            name=model.name,
            type=model.type,
        )
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: Engine) -> EngineModel:
        """Convert an Engine domain entity to an EngineModel.

        Args:
            entity (Engine): The domain entity.

        Returns:
            EngineModel: The corresponding SQLAlchemy model.
        """
        return EngineModel(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )


class OrchestrationInstanceRepository(BaseRepository[OrchestrationInstanceModel, OrchestrationInstance]):
    """Repository for OrchestrationInstance entities.

    Provides methods specific to OrchestrationInstance, including lookup by engine/external ID and status filters.
    """
    updatable_fields = [
        'external_id', 'duration_seconds', 'instance_metadata',
        'status', 'started_at', 'finished_at', 'is_active'
    ]

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, OrchestrationInstanceModel, OrchestrationInstance, uow)

    def get_by_engine_and_external(self, engine_id: UUID, external_id: str, include_soft_deleted: bool = False) -> Optional[OrchestrationInstance]:
        """Retrieve an instance by engine ID and external ID.

        Args:
            engine_id (UUID): ID of the engine.
            external_id (str): External system's identifier.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[OrchestrationInstance]: The instance if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.engine_id == engine_id,
                self.model_class.external_id == external_id
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_engine(self, engine_id: UUID,
                       include_soft_deleted: bool = False,
                       limit: int = 100,
                       offset: int = 0) -> List[OrchestrationInstance]:
        """List all instances for an engine with pagination.

        Args:
            engine_id (UUID): ID of the engine.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[OrchestrationInstance]: List of instances.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.engine_id == engine_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_by_status(self, status: ExecutionStatus,
                       include_soft_deleted: bool = False,
                       limit: int = 100,
                       offset: int = 0) -> List[OrchestrationInstance]:
        """List all instances by status with pagination.

        Args:
            status (ExecutionStatus): Status to filter by.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[OrchestrationInstance]: List of instances.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.status == status
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_running(self, include_soft_deleted: bool = False,
                     limit: int = 100,
                     offset: int = 0) -> List[OrchestrationInstance]:
        """List all running instances (status PROCESSING or RETRYING) with pagination.

        Args:
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[OrchestrationInstance]: List of running instances.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.status.in_([
                ExecutionStatus.PROCESSING,
                ExecutionStatus.RETRYING
            ])
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: OrchestrationInstanceModel) -> OrchestrationInstance:
        """Convert an OrchestrationInstanceModel to an OrchestrationInstance domain entity.

        Args:
            model (OrchestrationInstanceModel): The SQLAlchemy model.

        Returns:
            OrchestrationInstance: The corresponding domain entity.
        """
        entity = OrchestrationInstance(
            engine_id=model.engine_id,
            external_id=model.external_id,
            duration_seconds=model.duration_seconds,
            instance_metadata=model.instance_metadata,
        )
        entity.status = model.status
        entity.started_at = model.started_at
        entity.finished_at = model.finished_at
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: OrchestrationInstance) -> OrchestrationInstanceModel:
        """Convert an OrchestrationInstance domain entity to an OrchestrationInstanceModel.

        Args:
            entity (OrchestrationInstance): The domain entity.

        Returns:
            OrchestrationInstanceModel: The corresponding SQLAlchemy model.
        """
        return OrchestrationInstanceModel(
            id=entity.id,
            engine_id=entity.engine_id,
            external_id=entity.external_id,
            duration_seconds=entity.duration_seconds,
            instance_metadata=entity.instance_metadata,
            is_active=entity.is_active,
            status=entity.status,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )


class RunOrchestrationRepository(BaseRepository[RunOrchestrationModel, RunOrchestration]):
    """Repository for RunOrchestration entities.

    Provides methods for linking runs to orchestration instances.
    """
    updatable_fields = ['is_active']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, RunOrchestrationModel, RunOrchestration, uow)

    def get_by_run_and_instance(self, run_id: UUID, instance_id: UUID, include_soft_deleted: bool = False) -> Optional[RunOrchestration]:
        """Retrieve a link by run ID and instance ID.

        Args:
            run_id (UUID): ID of the run.
            instance_id (UUID): ID of the orchestration instance.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[RunOrchestration]: The link if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.orchestration_instance_id == instance_id
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_run(self, run_id: UUID,
                    include_soft_deleted: bool = False,
                    limit: int = 100,
                    offset: int = 0) -> List[RunOrchestration]:
        """List all links for a run with pagination.

        Args:
            run_id (UUID): ID of the run.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[RunOrchestration]: List of links.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.run_id == run_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.attached_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_by_instance(self, instance_id: UUID,
                         include_soft_deleted: bool = False,
                         limit: int = 100,
                         offset: int = 0) -> List[RunOrchestration]:
        """List all links for an orchestration instance with pagination.

        Args:
            instance_id (UUID): ID of the orchestration instance.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[RunOrchestration]: List of links.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.orchestration_instance_id == instance_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.attached_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: RunOrchestrationModel) -> RunOrchestration:
        """Convert a RunOrchestrationModel to a RunOrchestration domain entity.

        Args:
            model (RunOrchestrationModel): The SQLAlchemy model.

        Returns:
            RunOrchestration: The corresponding domain entity.
        """
        entity = RunOrchestration(
            run_id=model.run_id,
            orchestration_instance_id=model.orchestration_instance_id,
            attached_at=model.attached_at,
        )
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: RunOrchestration) -> RunOrchestrationModel:
        """Convert a RunOrchestration domain entity to a RunOrchestrationModel.

        Args:
            entity (RunOrchestration): The domain entity.

        Returns:
            RunOrchestrationModel: The corresponding SQLAlchemy model.
        """
        return RunOrchestrationModel(
            id=entity.id,
            run_id=entity.run_id,
            orchestration_instance_id=entity.orchestration_instance_id,
            attached_at=entity.attached_at,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )
