from uuid import UUID
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...uow.unit_of_work import UnitOfWork

from sqlalchemy.orm import Session

from ....domain.entities.definition import Automation, Batch, Item
from ...database.models.definition import AutomationModel, BatchModel, ItemModel
from .base import BaseRepository


class AutomationRepository(BaseRepository[AutomationModel, Automation]):
    """Repository for Automation entities.

    Provides methods specific to Automation, including lookup by name and listing active automations.
    """
    updatable_fields = ['name', 'description', 'batch_schema', 'item_schema']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, AutomationModel, Automation, uow)

    def get_by_name(self, name: str, include_soft_deleted: bool = False) -> Optional[Automation]:
        """Retrieve an automation by its unique name.

        Args:
            name (str): The automation name.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[Automation]: The automation if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.name == name
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_active(self, limit: int = 100, offset: int = 0) -> List[Automation]:
        """List all active automations with pagination.

        Args:
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[Automation]: List of active automations.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.is_active.is_(True)
        )
        models = query.order_by(
            self.model_class.created_at.desc(),
            self.model_class.id.desc()
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: AutomationModel) -> Automation:
        """Convert an AutomationModel to an Automation domain entity.

        Args:
            model (AutomationModel): The SQLAlchemy model.

        Returns:
            Automation: The corresponding domain entity.
        """
        entity = Automation(
            name=model.name,
            description=model.description,
            batch_schema=model.batch_schema,
            item_schema=model.item_schema,
        )

        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: Automation) -> AutomationModel:
        """Convert an Automation domain entity to an AutomationModel.

        Args:
            entity (Automation): The domain entity.

        Returns:
            AutomationModel: The corresponding SQLAlchemy model.
        """
        return AutomationModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active,
            batch_schema=entity.batch_schema,
            item_schema=entity.item_schema,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )


class BatchRepository(BaseRepository[BatchModel, Batch]):
    """Repository for Batch entities.

    Provides methods specific to Batch, including lookup by automation and name.
    """
    updatable_fields = ['name', 'payload', 'is_active']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, BatchModel, Batch, uow)

    def get_by_automation_and_name(self, automation_id: UUID, name: str, include_soft_deleted: bool = False) -> Optional[Batch]:
        """Retrieve a batch by its automation ID and name.

        Args:
            automation_id (UUID): ID of the parent automation.
            name (str): Batch name.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[Batch]: The batch if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.automation_id == automation_id,
            self.model_class.name == name
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_automation(self, automation_id: UUID,
                        include_soft_deleted: bool = False,
                        limit: int = 100,
                        offset: int = 0) -> List[Batch]:
        """List all batches for a specific automation with pagination.

        Args:
            automation_id (UUID): ID of the automation.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[Batch]: List of batches.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.automation_id == automation_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            BatchModel.name,
            BatchModel.id
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: BatchModel) -> Batch:
        """Convert a BatchModel to a Batch domain entity.

        Args:
            model (BatchModel): The SQLAlchemy model.

        Returns:
            Batch: The corresponding domain entity.
        """
        entity = Batch(
            automation_id=model.automation_id,
            name=model.name,
            payload=model.payload,
        )
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: Batch) -> BatchModel:
        """Convert a Batch domain entity to a BatchModel.

        Args:
            entity (Batch): The domain entity.

        Returns:
            BatchModel: The corresponding SQLAlchemy model.
        """
        return BatchModel(
            id=entity.id,
            automation_id=entity.automation_id,
            name=entity.name,
            payload=entity.payload,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )


class ItemRepository(BaseRepository[ItemModel, Item]):
    """Repository for Item entities.

    Provides methods specific to Item, including lookup by batch and sequence.
    """
    updatable_fields = ['payload', 'sequence_number', 'is_active']

    def __init__(self, db: Session, uow: "UnitOfWork"):
        """Initialize the repository.

        Args:
            db (Session): SQLAlchemy session.
            uow (UnitOfWork): The unit of work instance.
        """
        super().__init__(db, ItemModel, Item, uow)

    def get_by_batch_and_sequence(self, batch_id: UUID, sequence_number: int, include_soft_deleted: bool = False) -> Optional[Item]:
        """Retrieve an item by its batch ID and sequence number.

        Args:
            batch_id (UUID): ID of the parent batch.
            sequence_number (int): Sequence number of the item.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[Item]: The item if found, else None.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.batch_id == batch_id,
            self.model_class.sequence_number == sequence_number
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        model = query.first()
        return self._to_entity_or_update(model) if model else None

    def list_by_batch(self, batch_id: UUID,
                      include_soft_deleted: bool = False,
                      limit: int = 100,
                      offset: int = 0) -> List[Item]:
        """List all items in a batch ordered by sequence with pagination.

        Args:
            batch_id (UUID): ID of the batch.
            include_soft_deleted (bool): Whether to include soft-deleted.
            limit (int): Maximum number of records.
            offset (int): Number of records to skip.

        Returns:
            List[Item]: List of items.
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.batch_id == batch_id
        )
        query = self._apply_soft_delete_filter(query, include_soft_deleted)
        models = query.order_by(
            ItemModel.sequence_number,
            ItemModel.id
        ).limit(limit).offset(offset).all()
        return [self._to_entity_or_update(m) for m in models]

    def _to_entity(self, model: ItemModel) -> Item:
        """Convert an ItemModel to an Item domain entity.

        Args:
            model (ItemModel): The SQLAlchemy model.

        Returns:
            Item: The corresponding domain entity.
        """
        entity = Item(
            batch_id=model.batch_id,
            sequence_number=model.sequence_number,
            payload=model.payload,
        )
        self._copy_common_attrs(model, entity, [
            'id', 'created_at', 'updated_at', 'created_by',
            'updated_by', 'version', 'is_active'
        ])
        return entity

    def _to_model(self, entity: Item) -> ItemModel:
        """Convert an Item domain entity to an ItemModel.

        Args:
            entity (Item): The domain entity.

        Returns:
            ItemModel: The corresponding SQLAlchemy model.
        """
        return ItemModel(
            id=entity.id,
            batch_id=entity.batch_id,
            sequence_number=entity.sequence_number,
            payload=entity.payload,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            version=entity.version,
        )
