from uuid import UUID
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...uow.unit_of_work import UnitOfWork

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_

from ....domain.entities.execution import (
    Run, BatchExecution, ItemExecution, ItemStateHistory
)
from ....domain.enums import ExecutionStatus
from ...database.models.execution import (
    RunModel, BatchExecutionModel, ItemExecutionModel, ItemStateHistoryModel
)

from ...exceptions.repository import RepositoryError
from .base import BaseRepository

class RunRepository(BaseRepository[RunModel, Run]):
    """Repository for Run entities.

    Provides methods specific to Run, including lookup by correlation ID, status filtering, and finding running runs.
    """
    updatable_fields = [
        'correlation_id', 'cancellation_reason', 'error_summary',
        'status', 'started_at', 'finished_at', 'is_active'
    ]

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, RunModel, Run, uow)

    def get_by_correlation_id(self, correlation_id: str, include_soft_deleted: bool = False) -> Optional[Run]:
        """Retrieve a run by its correlation ID.

        Args:
            correlation_id (str): External tracking identifier.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[Run]: The run if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.correlation_id == correlation_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_automation(
        self,
        automation_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ExecutionStatus] = None,
        include_soft_deleted: bool = False
    ) -> List[Run]:
        """List runs for an automation with optional filters.

        Args:
            automation_id (UUID): ID of the automation.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.
            status (Optional[ExecutionStatus]): Filter by status.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            List[Run]: List of runs matching the criteria.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.automation_id == automation_id
        )

        if status:
            query = query.filter(self.model_class.status == status)

        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()

        return [self._to_entity_or_update(m) for m in models]

    def list_by_status(
        self,
        status: ExecutionStatus,
        limit: int = 100,
        offset: int = 0,
        include_soft_deleted: bool = False
    ) -> List[Run]:
        """List runs by status with pagination.

        Args:
            status (ExecutionStatus): Status to filter by.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            List[Run]: List of runs.
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

    def find_running(self, automation_id: Optional[UUID] = None,
                    include_soft_deleted: bool = False) -> List[Run]:
        """Find all running runs (status PROCESSING or RETRYING).

        Args:
            automation_id (Optional[UUID]): If provided, filter by automation.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            List[Run]: List of running runs, ordered by started_at descending.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.status.in_([
                ExecutionStatus.PROCESSING,
                ExecutionStatus.RETRYING
            ])
        )
        if automation_id:
            query = query.filter(self.model_class.automation_id == automation_id)
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.started_at.desc(),
            self.model_class.id.desc()
        ).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: RunModel) -> Run:
        """Convert a RunModel to a Run domain entity.

        Args:
            model (RunModel): The SQLAlchemy model.

        Returns:
            Run: The corresponding domain entity.
        """
        entity = Run(
            automation_id=model.automation_id,
            correlation_id=model.correlation_id,
            cancellation_reason=model.cancellation_reason,
            error_summary=model.error_summary,
        )
        entity.status = model.status
        entity.started_at = model.started_at
        entity.finished_at = model.finished_at
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: Run) -> RunModel:
        """Convert a Run domain entity to a RunModel.

        Args:
            entity (Run): The domain entity.

        Returns:
            RunModel: The corresponding SQLAlchemy model.
        """
        return RunModel(
            id=entity.id,
            automation_id=entity.automation_id,
            correlation_id=entity.correlation_id,
            cancellation_reason=entity.cancellation_reason,
            error_summary=entity.error_summary,
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


class BatchExecutionRepository(BaseRepository[BatchExecutionModel, BatchExecution]):
    """Repository for BatchExecution entities.

    Provides methods specific to BatchExecution, including lookup by run and batch.
    """
    updatable_fields = ['status', 'started_at', 'finished_at', 'is_active']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, BatchExecutionModel, BatchExecution, uow)

    def get_by_run_and_batch(self, run_id: UUID, batch_id: UUID, include_soft_deleted: bool = False) -> Optional[BatchExecution]:
        """Retrieve a batch execution by run ID and batch ID.

        Args:
            run_id (UUID): ID of the run.
            batch_id (UUID): ID of the batch.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[BatchExecution]: The batch execution if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.batch_id == batch_id
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_run(self, run_id: UUID,
                    include_soft_deleted: bool = False,
                    limit: int = 100,
                    offset: int = 0) -> List[BatchExecution]:
        """List all batch executions for a run with pagination.

        Args:
            run_id (UUID): ID of the run.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[BatchExecution]: List of batch executions.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.run_id == run_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_by_batch(self, batch_id: UUID,
                      include_soft_deleted: bool = False,
                      limit: int = 100,
                      offset: int = 0) -> List[BatchExecution]:
        """List all executions for a batch with pagination.

        Args:
            batch_id (UUID): ID of the batch.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[BatchExecution]: List of batch executions.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.batch_id == batch_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: BatchExecutionModel) -> BatchExecution:
        """Convert a BatchExecutionModel to a BatchExecution domain entity.

        Args:
            model (BatchExecutionModel): The SQLAlchemy model.

        Returns:
            BatchExecution: The corresponding domain entity.
        """
        entity = BatchExecution(
            run_id=model.run_id,
            batch_id=model.batch_id,
        )
        entity.status = model.status
        entity.started_at = model.started_at
        entity.finished_at = model.finished_at
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity


    def _to_model(self, entity: BatchExecution) -> BatchExecutionModel:
        """Convert a BatchExecution domain entity to a BatchExecutionModel.

        Args:
            entity (BatchExecution): The domain entity.

        Returns:
            BatchExecutionModel: The corresponding SQLAlchemy model.
        """
        return BatchExecutionModel(
            id=entity.id,
            run_id=entity.run_id,
            batch_id=entity.batch_id,
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


class ItemExecutionRepository(BaseRepository[ItemExecutionModel, ItemExecution]):
    """Repository for ItemExecution entities.

    Provides methods specific to ItemExecution, including lookup by run/item, and status‑based queries.
    """
    updatable_fields = [
        'result_payload', 'error_message', 'status',
        'started_at', 'finished_at', 'attempt_count',
        'max_attempts', 'is_active'
    ]

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, ItemExecutionModel, ItemExecution, uow)

    def get_by_run_and_item(self, run_id: UUID, item_id: UUID,
                            include_soft_deleted: bool = False) -> Optional[ItemExecution]:
        """Retrieve an item execution by run ID and item ID.

        Args:
            run_id (UUID): ID of the run.
            item_id (UUID): ID of the item.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[ItemExecution]: The item execution if found, else None.

        Raises:
            RepositoryError: If multiple executions are found (data integrity issue).
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.item_id == item_id
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        try:
            model = query.one()
            return self._to_entity_or_update(model)

        except NoResultFound:
            return None

        except MultipleResultsFound as e:
            self.logger.error(f"Multiple item executions found for run {run_id} item {item_id}")
            raise RepositoryError(f"Data integrity issue: multiple executions for same run/item") from e

    def list_by_batch_execution(self, batch_execution_id: UUID,
                                include_soft_deleted: bool = False,
                                limit: int = 100,
                                offset: int = 0) -> List[ItemExecution]:
        """List all item executions for a batch execution with pagination.

        Args:
            batch_execution_id (UUID): ID of the batch execution.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[ItemExecution]: List of item executions.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.batch_execution_id == batch_execution_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_pending_by_run(self, run_id: UUID,
                            include_soft_deleted: bool = False,
                            limit: int = 100,
                            offset: int = 0) -> List[ItemExecution]:
        """List all pending item executions for a run with pagination.

        Args:
            run_id (UUID): ID of the run.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[ItemExecution]: List of pending item executions.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.status == ExecutionStatus.PENDING
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def list_failed_by_run(self, run_id: UUID,
                        include_soft_deleted: bool = False,
                        limit: int = 100,
                        offset: int = 0) -> List[ItemExecution]:
        """List all failed item executions for a run with pagination.

        Args:
            run_id (UUID): ID of the run.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[ItemExecution]: List of failed item executions.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.status == ExecutionStatus.FAILED
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def count_by_status(self, run_id: UUID, status: ExecutionStatus, include_soft_deleted: bool = False) -> int:
        """Count item executions by status for a run.

        Args:
            run_id (UUID): ID of the run.
            status (ExecutionStatus): Status to count.
            include_soft_deleted (bool): Whether to include soft-deleted.

        Returns:
            int: Count of item executions.
        """
        query = self.db.query(self.model_class).filter(
            and_(
                self.model_class.run_id == run_id,
                self.model_class.status == status
            )
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        return query.count()

    def _to_entity(self, model: ItemExecutionModel) -> ItemExecution:
        """Convert an ItemExecutionModel to an ItemExecution domain entity.

        Args:
            model (ItemExecutionModel): The SQLAlchemy model.

        Returns:
            ItemExecution: The corresponding domain entity.
        """
        entity = ItemExecution(
            run_id=model.run_id,
            batch_execution_id=model.batch_execution_id,
            item_id=model.item_id,
            result_payload=model.result_payload,
            error_message=model.error_message,
        )
        entity.status = model.status
        entity.started_at = model.started_at
        entity.finished_at = model.finished_at
        entity.attempt_count = model.attempt_count
        entity.max_attempts = model.max_attempts
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: ItemExecution) -> ItemExecutionModel:
        """Convert an ItemExecution domain entity to an ItemExecutionModel.

        Args:
            entity (ItemExecution): The domain entity.

        Returns:
            ItemExecutionModel: The corresponding SQLAlchemy model.
        """
        return ItemExecutionModel(
            id=entity.id,
            run_id=entity.run_id,
            batch_execution_id=entity.batch_execution_id,
            item_id=entity.item_id,
            result_payload=entity.result_payload,
            error_message=entity.error_message,
            is_active=entity.is_active,
            status=entity.status,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            attempt_count=entity.attempt_count,
            max_attempts=entity.max_attempts,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )


class ItemStateHistoryRepository(BaseRepository[ItemStateHistoryModel, ItemStateHistory]):
    """Repository for ItemStateHistory entities.

    This repository disables versioning (`use_versioning = False`) because history records are immutable.
    Update and delete operations are not allowed.
    """
    updatable_fields = []
    use_versioning = False

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, ItemStateHistoryModel, ItemStateHistory, uow)

    def list_by_item_execution(
        self,
        item_execution_id: UUID,
        limit: int = 100,
        offset: int = 0,
        include_soft_deleted: bool = False
    ) -> List[ItemStateHistory]:
        """List history records for an item execution with pagination.

        Args:
            item_execution_id (UUID): ID of the item execution.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.
            include_soft_deleted (bool): Whether to include soft-deleted (always false for history).

        Returns:
            List[ItemStateHistory]: List of history records.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.item_execution_id == item_execution_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            self.model_class.changed_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def get_latest_by_item_execution(
        self,
        item_execution_id: UUID,
        include_soft_deleted: bool = False
    ) -> Optional[ItemStateHistory]:
        """Retrieve the most recent history record for an item execution.

        Args:
            item_execution_id (UUID): ID of the item execution.
            include_soft_deleted (bool): Whether to include soft-deleted.

        Returns:
            Optional[ItemStateHistory]: The latest history record, or None if none.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.item_execution_id == item_execution_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.order_by(
            self.model_class.changed_at.desc(),
            self.model_class.id.desc()
        ).first()
        return self._to_entity_or_update(model) if model else None


    def _to_entity(self, model: ItemStateHistoryModel) -> ItemStateHistory:
        """Convert an ItemStateHistoryModel to an ItemStateHistory domain entity.

        Args:
            model (ItemStateHistoryModel): The SQLAlchemy model.

        Returns:
            ItemStateHistory: The corresponding domain entity.
        """
        entity = ItemStateHistory(
            item_execution_id=model.item_execution_id,
            new_status=model.new_status,
            previous_status=model.previous_status,
            changed_at=model.changed_at,
        )
        entity.id = model.id
        entity.created_at = model.created_at
        entity.created_by = model.created_by
        return entity

    def _to_model(self, entity: ItemStateHistory) -> ItemStateHistoryModel:
        """Convert an ItemStateHistory domain entity to an ItemStateHistoryModel.

        Args:
            entity (ItemStateHistory): The domain entity.

        Returns:
            ItemStateHistoryModel: The corresponding SQLAlchemy model.
        """
        return ItemStateHistoryModel(
            id=entity.id,
            item_execution_id=entity.item_execution_id,
            previous_status=entity.previous_status,
            new_status=entity.new_status,
            changed_at=entity.changed_at,
            created_at=entity.created_at,
            created_by=entity.created_by,
        )

    def update(self, id: UUID, entity: ItemStateHistory, user: Optional[str] = None) -> ItemStateHistory:
        """Not implemented – ItemStateHistory is immutable.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError("ItemStateHistory is immutable and cannot be updated")

    def delete(self, id: UUID, soft: bool = False, user: Optional[str] = None, expected_version: Optional[int] = None) -> bool:
        """Not implemented – ItemStateHistory cannot be deleted.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError("ItemStateHistory cannot be deleted")
