from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, TYPE_CHECKING
from abc import abstractmethod
from uuid import UUID
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ...uow.unit_of_work import UnitOfWork

from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy import update, delete, inspect

from ...exceptions.repository import (
    EntityNotFoundError,
    DuplicateEntityError,
    ConcurrencyError,
    RepositoryError,
)

from ....utils.logger import setup_logger


ModelType = TypeVar("ModelType")
EntityType = TypeVar("EntityType")

logger = setup_logger(__name__)


class BaseRepository(Generic[ModelType, EntityType]):
    """Abstract base repository implementing common CRUD operations.

    Provides reusable logic for get, list, create, update, delete,
    handling soft delete, optimistic locking, audit fields, and identity map.

    Attributes:
        use_versioning (bool): Class-level flag to enable/disable optimistic locking.
        db (Session): SQLAlchemy session.
        model_class (Type[ModelType]): SQLAlchemy model class.
        entity_class (Type[EntityType]): Domain entity class.
        uow (UnitOfWork): Reference to the unit of work.
        logger (Logger): Logger instance.
        _original_versions (Dict[UUID, int]): Map of entity ID to version at load time.
    """
    use_versioning: bool = True

    def __init__(self, db: Session, model_class: Type[ModelType], entity_class: Type[EntityType], uow: "UnitOfWork"):
        self.db = db
        self.model_class = model_class
        self.entity_class = entity_class
        self.uow = uow
        self.logger = logger
        self._original_versions: Dict[UUID, int] = {}

    def _copy_common_attrs(self, source, target, fields: List[str]) -> None:
        """Copy common attributes from source (model) to target (entity).

        Args:
            source: Source object (model).
            target: Target object (entity).
            fields (List[str]): List of attribute names to copy.
        """
        for field in fields:
            if hasattr(source, field):
                setattr(target, field, getattr(source, field))

    def get(self, id: UUID, include_soft_deleted: bool = False) -> Optional[EntityType]:
        """Retrieve an entity by ID, using identity map.

        Args:
            id (UUID): Entity ID.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            Optional[EntityType]: The entity if found, else None.

        Raises:
            RepositoryError: On database error.
        """
        if self.uow.has_entity(self.entity_class, id):
            entity = self.uow.get_entity(self.entity_class, id)
            if include_soft_deleted or (hasattr(entity, 'is_active') and entity.is_active):
                if self.use_versioning and hasattr(entity, 'version'):
                    self._original_versions[id] = entity.version
                return entity

        try:
            query = self.db.query(self.model_class).filter(self.model_class.id == id)
            if not include_soft_deleted and hasattr(self.model_class, 'is_active'):
                query = query.filter(self.model_class.is_active == True)

            model = query.first()
            if model:
                entity = self._to_entity(model)
                self.uow.register_entity(entity, entity_id=model.id)
                if self.use_versioning and hasattr(entity, 'version'):
                    self._original_versions[id] = model.version
                return entity
            return None

        except Exception as e:
            self.logger.error(f"Error getting {self.model_class.__name__} by id {id}: {str(e)}")
            raise RepositoryError(f"Failed to retrieve entity: {str(e)}") from e

    def get_or_raise(self, id: UUID, include_soft_deleted: bool = False) -> EntityType:
        """Retrieve an entity by ID, raising if not found.

        Args:
            id (UUID): Entity ID.
            include_soft_deleted (bool): Whether to include soft-deleted records.

        Returns:
            EntityType: The entity.

        Raises:
            EntityNotFoundError: If entity not found.
        """
        entity = self.get(id, include_soft_deleted)
        if not entity:
            raise EntityNotFoundError(self.model_class.__name__, id)
        return entity

    def list(self, include_soft_deleted: bool = False, **filters) -> List[EntityType]:
        """List entities matching optional filters.

        Args:
            include_soft_deleted (bool): Whether to include soft-deleted records.
            **filters: Field-value pairs to filter on. Keys must match model column names.

        Returns:
            List[EntityType]: List of entities.

        Raises:
            RepositoryError: If an invalid filter field is provided or on other errors.
        """
        try:
            query = self.db.query(self.model_class)

            if not include_soft_deleted and hasattr(self.model_class, 'is_active'):
                query = query.filter(self.model_class.is_active == True)

            valid_columns = {c.key for c in inspect(self.model_class).columns}
            for field, value in filters.items():
                if field not in valid_columns:
                    raise RepositoryError(f"Invalid filter field: '{field}' for model {self.model_class.__name__}")
                if value is not None:
                    query = query.filter(getattr(self.model_class, field) == value)

            models = query.all()
            return [self._to_entity_or_update(m) for m in models]
        except Exception as e:
            self.logger.error(f"Error listing {self.model_class.__name__}: {str(e)}")
            raise RepositoryError(f"Failed to list entities: {str(e)}") from e

    def create(self, entity: EntityType, user: Optional[str] = None) -> EntityType:
        """Create a new entity.

        Args:
            entity (EntityType): The domain entity to create.
            user (Optional[str]): User performing the creation (for audit).

        Returns:
            EntityType: The created entity with generated fields (id, timestamps, version).

        Raises:
            DuplicateEntityError: On unique constraint violation.
            RepositoryError: On other database errors.
        """
        try:
            if hasattr(entity, 'created_by') and user:
                entity.created_by = user
            if hasattr(entity, 'updated_by') and user:
                entity.updated_by = user

            model = self._to_model(entity)
            self.db.add(model)
            self.db.flush()

            entity.id = model.id
            if hasattr(entity, 'created_at') and hasattr(model, 'created_at'):
                entity.created_at = model.created_at
            if hasattr(entity, 'updated_at') and hasattr(model, 'updated_at'):
                entity.updated_at = model.updated_at

            if self.use_versioning and hasattr(entity, 'version'):
                self._original_versions[entity.id] = model.version

            self.logger.info(f"Created {self.model_class.__name__} with id {entity.id}")
            self.uow.register_entity(entity)
            return entity

        except IntegrityError as e:
            self.db.rollback()
            if "unique constraint" in str(e).lower():
                raise DuplicateEntityError(self.model_class.__name__, str(e)) from e
            raise RepositoryError(f"Integrity error: {str(e)}") from e
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error creating {self.model_class.__name__}: {str(e)}")
            raise RepositoryError(f"Failed to create entity: {str(e)}") from e

    def _to_entity_or_update(self, model: ModelType) -> EntityType:
        """Convert model to entity, checking identity map first.

        Args:
            model (ModelType): The SQLAlchemy model.

        Returns:
            EntityType: The domain entity (either existing or newly converted).
        """
        existing = self.uow.get_entity(self.entity_class, model.id)
        if existing is not None:
            return existing

        entity = self._to_entity(model)
        self.uow.register_entity(entity, entity_id=model.id)
        if self.use_versioning and hasattr(entity, 'version'):
            self._original_versions[model.id] = model.version
        return entity

    def _update_entity_from_model(self, entity: EntityType, model: ModelType) -> None:
        """Update entity fields from model, excluding id and created_at.

        Args:
            entity (EntityType): The domain entity to update.
            model (ModelType): The SQLAlchemy model with latest data.
        """
        exclude = {'id', 'created_at'}
        for col in self.model_class.__table__.columns:
            key = col.name
            if key in exclude:
                continue
            if hasattr(entity, key):
                setattr(entity, key, getattr(model, key))

    def update(self, id: UUID, entity: EntityType, user: Optional[str] = None) -> EntityType:
        """Update an existing entity.

        Performs optimistic locking if `use_versioning` is True.

        Args:
            id (UUID): ID of the entity to update.
            entity (EntityType): The updated domain entity.
            user (Optional[str]): User performing the update.

        Returns:
            EntityType: The updated entity (with new version).

        Raises:
            EntityNotFoundError: If entity not found.
            ConcurrencyError: On version mismatch.
            RepositoryError: On other errors.
        """
        if self.use_versioning:
            expected_version = self._original_versions.get(id)
            print(f"[DEBUG] update - id: {id}, expected_version: {expected_version}, entity.version: {getattr(entity, 'version', None)}")
            if expected_version is None:
                raise ConcurrencyError(
                    self.model_class.__name__,
                    id,
                    -1,
                    getattr(entity, 'version', -1),
                    extra="Entity not tracked; retrieve it via get() first"
                )

        try:
            existing_model = self.db.get(self.model_class, id)
            print(f"[DEBUG] existing_model.version: {existing_model.version if existing_model else 'None'}")
            if not existing_model:
                raise EntityNotFoundError(self.model_class.__name__, id)

            if self.use_versioning and expected_version is not None:
                if existing_model.version != expected_version:
                    raise ConcurrencyError(
                        self.model_class.__name__,
                        id,
                        expected_version,
                        existing_model.version
                    )

            if hasattr(entity, 'touch'):
                entity.touch(user)

            update_data = self._get_changed_data(entity, existing_model, preserve_created=True)
            print(f"[DEBUG] update_data: {update_data}")

            if not update_data and (not self.use_versioning or entity.version == expected_version):
                print("[DEBUG] No changes, returning early")
                return entity

            if self.use_versioning:
                update_data['version'] = self.model_class.version + 1

            stmt = update(self.model_class).where(self.model_class.id == id)
            if self.use_versioning and expected_version is not None:
                stmt = stmt.where(self.model_class.version == expected_version)

            stmt = stmt.values(**update_data).returning(self.model_class)
            updated_model = self.db.execute(stmt).scalar_one_or_none()
            print(f"[DEBUG] updated_model: {updated_model is not None}")

            if updated_model is None:
                current_model = self.db.get(self.model_class, id)
                print(f"[DEBUG] current_model.version: {current_model.version if current_model else 'None'}")
                if not current_model:
                    raise EntityNotFoundError(self.model_class.__name__, id)
                if self.use_versioning:
                    raise ConcurrencyError(
                        self.model_class.__name__,
                        id,
                        expected_version or -1,
                        current_model.version if current_model else -1
                    )
                else:
                    raise RepositoryError(f"Unexpected error updating {self.model_class.__name__} {id}")

            self.db.expire(existing_model)

            tracked_entity = self.uow.get_entity(self.entity_class, id)
            if tracked_entity is not None:
                self._update_entity_from_model(tracked_entity, updated_model)
                updated_entity = tracked_entity
            else:
                updated_entity = self._to_entity(updated_model)
                self.uow.register_entity(updated_entity)

            if self.use_versioning and hasattr(updated_entity, 'version'):
                self._original_versions[id] = updated_entity.version

            return updated_entity

        except StaleDataError as e:
            self.db.rollback()
            raise ConcurrencyError(self.model_class.__name__, id, -1, -1) from e
        except (EntityNotFoundError, ConcurrencyError):
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating {self.model_class.__name__} {id}: {str(e)}")
            raise RepositoryError(f"Failed to update entity: {str(e)}") from e

    def _get_changed_data(self, entity: EntityType, existing_model: ModelType,
                          preserve_created: bool = True) -> Dict[str, Any]:
        """Compare entity with existing model and return only changed fields.

        Respects `updatable_fields` if defined in the subclass.

        Args:
            entity (EntityType): The updated domain entity.
            existing_model (ModelType): The existing database model.
            preserve_created (bool): If True, exclude created_at/created_by from changes.

        Returns:
            Dict[str, Any]: Dictionary of changed fields and their new values.
        """
        data = {}
        exclude_fields = {'id'}
        if preserve_created:
            exclude_fields.update({'created_at', 'created_by'})

        if hasattr(self, 'updatable_fields') and self.updatable_fields is not None:
            allowed_fields = set(self.updatable_fields)
        else:
            allowed_fields = {c.key for c in self.model_class.__table__.columns} - exclude_fields

        if hasattr(self.model_class, 'updated_at') and 'updated_at' not in exclude_fields:
            allowed_fields.add('updated_at')

        if hasattr(self.model_class, 'updated_by')  and 'updated_by' not in exclude_fields:
            allowed_fields.add('updated_by')

        model_dict = {}
        for col in self.model_class.__table__.columns:
            key = col.name
            if key in allowed_fields or key in exclude_fields:
                model_dict[key] = getattr(existing_model, key)


        print(f"[DEBUG] _get_changed_data: allowed_fields={allowed_fields}")
        print(f"[DEBUG] model_dict keys: {list(model_dict.keys())}")
        for field in allowed_fields:
            new_val = getattr(entity, field, None)
            old_val = model_dict.get(field)
            if new_val != old_val:
                data[field] = new_val
                print(f"[DEBUG] change detected: {field}: {old_val} -> {new_val}")
            else:
                print(f"[DEBUG] no change: {field} = {new_val}")

        all_entity_fields = [key for key in entity.__dict__.keys() if not key.startswith('_')]
        non_updatable = set(all_entity_fields) - allowed_fields - exclude_fields
        for field in non_updatable:
            new_val = getattr(entity, field, None)
            old_val = model_dict.get(field)
            if old_val != new_val:
                self.logger.debug(
                    f"Field '{field}' changed from {old_val} to {new_val} but is not updatable. "
                    f"Change will be ignored."
                )

        return data

    def delete(self, id: UUID, soft: bool = False, user: Optional[str] = None,
            expected_version: Optional[int] = None) -> bool:
        """Delete an entity (soft or hard).

        Args:
            id (UUID): Entity ID.
            soft (bool): If True, perform soft delete; else hard delete.
            user (Optional[str]): User performing deletion (for audit).
            expected_version (Optional[int]): Expected version for optimistic locking.

        Returns:
            bool: True if deletion succeeded.

        Raises:
            ConcurrencyError: On version mismatch (when expected_version provided).
            RepositoryError: On other errors.
        """
        try:
            if expected_version is None and self.use_versioning:
                expected_version = self._original_versions.get(id)

            if soft:
                if not hasattr(self.model_class, 'is_active'):
                    raise RepositoryError(f"Model {self.model_class.__name__} does not support soft delete")

                stmt = update(self.model_class).where(self.model_class.id == id)
                if self.use_versioning and expected_version is not None:
                    stmt = stmt.where(self.model_class.version == expected_version)

                update_values = {
                    'is_active': False,
                    'updated_at': datetime.now(timezone.utc),
                }
                if user and hasattr(self.model_class, 'updated_by'):
                    update_values['updated_by'] = user

                if self.use_versioning and hasattr(self.model_class, 'version'):
                    update_values['version'] = self.model_class.version + 1

                stmt = stmt.values(**update_values).returning(self.model_class)
                updated_model = self.db.execute(stmt).scalar_one_or_none()

                if updated_model is None:
                    existing = self.db.get(self.model_class, id)
                    if not existing:
                        return False
                    if self.use_versioning and expected_version is not None:
                        raise ConcurrencyError(
                            self.model_class.__name__,
                            id,
                            expected_version,
                            existing.version
                        )
                    return False

                tracked = self.uow.get_entity(self.entity_class, id)
                if tracked is not None:
                    self._update_entity_from_model(tracked, updated_model)
                    if self.use_versioning and hasattr(tracked, 'version'):
                        self._original_versions[id] = tracked.version
                else:
                    self._original_versions.pop(id, None)

                return True

            else:
                stmt = delete(self.model_class).where(self.model_class.id == id)
                if self.use_versioning and expected_version is not None:
                    stmt = stmt.where(self.model_class.version == expected_version)

                result = self.db.execute(stmt)
                if result.rowcount == 0:
                    existing = self.db.get(self.model_class, id)
                    if not existing:
                        return False
                    if self.use_versioning and expected_version is not None:
                        raise ConcurrencyError(
                            self.model_class.__name__,
                            id,
                            expected_version,
                            existing.version
                        )
                    return False

                if self.uow.has_entity(self.entity_class, id):
                    self.uow.unregister_entity(self.entity_class, id)
                self._original_versions.pop(id, None)
                self.db.flush()
                return True

        except ConcurrencyError:
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error deleting {self.model_class.__name__} {id}: {str(e)}")
            raise RepositoryError(f"Failed to delete entity: {str(e)}") from e

    def exists(self, id: UUID, include_soft_deleted: bool = False) -> bool:
        """Check if an entity with given ID exists.

        Args:
            id (UUID): Entity ID.
            include_soft_deleted (bool): Whether to consider soft-deleted.

        Returns:
            bool: True if exists.
        """
        query = self.db.query(self.model_class).filter(self.model_class.id == id)
        if not include_soft_deleted and hasattr(self.model_class, 'is_active'):
            query = query.filter(self.model_class.is_active == True)
        return query.first() is not None

    def count(self, include_soft_deleted: bool = False, **filters) -> int:
        """Count entities matching optional filters.

        Args:
            include_soft_deleted (bool): Whether to include soft-deleted.
            **filters: Field-value pairs to filter on.

        Returns:
            int: Count of matching entities.
        """
        query = self.db.query(self.model_class)
        if not include_soft_deleted and hasattr(self.model_class, 'is_active'):
            query = query.filter(self.model_class.is_active == True)
        for field, value in filters.items():
            if hasattr(self.model_class, field) and value is not None:
                query = query.filter(getattr(self.model_class, field) == value)
        return query.count()

    def _get_model_instance(self, entity: EntityType) -> ModelType:
        """Retrieve the model instance corresponding to an entity.

        Args:
            entity (EntityType): The domain entity.

        Returns:
            ModelType: The SQLAlchemy model.

        Raises:
            EntityNotFoundError: If no matching model found.
        """
        model = self.db.get(self.model_class, entity.id)
        if model is None:
            raise EntityNotFoundError(self.model_class.__name__, entity.id)
        return model

    def refresh(self, entity: EntityType) -> EntityType:
        """Refresh the given entity from the database.

        The entity must already be tracked by the repository (i.e., have been loaded
        in the current unit of work).

        Args:
            entity (EntityType): The domain entity to refresh.

        Returns:
            EntityType: The refreshed entity.

        Raises:
            RepositoryError: If entity not tracked.
            EntityNotFoundError: If entity not found in database.
        """
        if not self.uow.has_entity(self.entity_class, entity.id):
            raise RepositoryError(
                f"Cannot refresh untracked {self.entity_class.__name__} with id {entity.id}. "
                "Load the entity via get() or list() first."
            )

        model = self._get_model_instance(entity)
        self.db.refresh(model)
        self._update_entity_from_model(entity, model)
        if self.use_versioning and hasattr(entity, 'version'):
            self._original_versions[entity.id] = entity.version
        return entity

    def _apply_soft_delete_filter(self, query: Query, include_soft_deleted: bool = False) -> Query:
        """Apply soft delete filter to a query if needed.

        Args:
            query (Query): The SQLAlchemy query.
            include_soft_deleted (bool): Whether to skip the filter.

        Returns:
            Query: Modified query.
        """
        if not include_soft_deleted and hasattr(self.model_class, 'is_active'):
            return query.filter(self.model_class.is_active == True)
        return query

    @abstractmethod
    def _to_entity(self, model: ModelType) -> EntityType:
        """Convert a database model to a domain entity.

        Args:
            model (ModelType): The SQLAlchemy model.

        Returns:
            EntityType: The corresponding domain entity.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _to_entity method")

    @abstractmethod
    def _to_model(self, entity: EntityType) -> ModelType:
        """Convert a domain entity to a database model.

        Args:
            entity (EntityType): The domain entity.

        Returns:
            ModelType: The corresponding SQLAlchemy model.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _to_model method")
