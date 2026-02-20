## Repositories

### [BaseRepository] (Abstract Generic)
**Definition**: Abstract base class implementing common CRUD operations for all repositories.

**Purpose**: Provide reusable logic for `get`, `list`, `create`, `update`, `delete`, `exists`, `count`; handle soft delete, optimistic locking, and audit fields consistently.

**Key characteristics**:
- Generic over `ModelType` (SQLAlchemy model) and `EntityType` (domain entity).
- **`use_versioning` (class-level flag)**: If `True` (default), enables optimistic locking logic; if `False`, version fields are ignored (used for immutable entities like `ItemStateHistory`).
- **get()**: Retrieves entity by ID; checks identity map first; stores the model’s version in an internal map `_original_versions` keyed by entity ID for optimistic locking (only if `use_versioning` is True and entity has version attribute).
- **get_or_raise()**: Same as `get` but raises `EntityNotFoundError` if not found.
- **list()**: Now validates filter keys against the model’s column names; raises `RepositoryError` if an invalid field is provided.
- **create()**: Converts entity to model, adds to session, flushes, and updates entity with generated ID. If `use_versioning` and entity has `version`, it sets the version from the model and stores `_original_version`. Sets audit fields (`created_by`, `updated_by`) if `user` provided.
- **update()**: If `use_versioning`, uses `_original_version` in the WHERE clause to ensure atomicity; increments version; raises `ConcurrencyError` on mismatch. If `use_versioning` is False, no version check is performed. The method also calls `entity.touch(user)` if the entity has a `touch` method. Uses `_get_changed_data()` to compare entity with existing model and only update changed fields.
- **delete()**: Supports hard and soft delete; optional version check (only if `use_versioning`). For soft delete, updates `is_active` to `False` and bumps version. Returns `True` if deletion succeeded.
- **exists()**, **count()**: Basic existence and counting.
- **_get_changed_data()**: Compares entity with existing model and returns a dict of changed fields, respecting `updatable_fields` if defined in the subclass. Excludes fields like `id` and `created_at` by default.
- **_copy_common_attrs()**: Helper to copy common fields (id, timestamps, audit, version, is_active) from model to entity.
- **_to_entity_or_update()**: Converts a model to an entity, but returns the already tracked instance from the identity map if present.
- **_apply_soft_delete_filter()**: Applies `is_active == True` filter unless `include_soft_deleted` is True.
- **refresh()**: Refreshes a tracked entity from the database.

**Relationships / Rules**:
- All concrete repositories inherit from `BaseRepository`.
- Relies on domain entities having `version` and `touch()` method when versioning is enabled.
- Uses SQLAlchemy’s `update().returning()` for efficient concurrency‑safe updates.

**Examples**:
```python
class AutomationRepository(BaseRepository[AutomationModel, Automation]):
    updatable_fields = ['name', 'description', 'batch_schema', 'item_schema']

    def _to_entity(self, model: AutomationModel) -> Automation:
        entity = Automation(name=model.name, description=model.description,
                            batch_schema=model.batch_schema, item_schema=model.item_schema)
        self._copy_common_attrs(model, entity, ['id', 'created_at', 'updated_at',
                                                 'created_by', 'updated_by', 'version', 'is_active'])
        return entity

    def _to_model(self, entity: Automation) -> AutomationModel:
        return AutomationModel(id=entity.id, name=entity.name, ...)
```

### [AutomationRepository]
**Definition**: Repository for `Automation` entities.

**Specific methods**:
- `get_by_name(name, include_soft_deleted)`: Retrieve automation by unique name.
- `list_active(limit=100, offset=0)`: List all automations with `is_active=True`.

### [BatchRepository]
**Definition**: Repository for `Batch` entities.

**Specific methods**:
- `get_by_automation_and_name(automation_id, name, include_soft_deleted)`
- `list_by_automation(automation_id, include_soft_deleted, limit=100, offset=0)`

### [ItemRepository]
**Definition**: Repository for `Item` entities.

**Specific methods**:
- `get_by_batch_and_sequence(batch_id, sequence_number, include_soft_deleted)`
- `list_by_batch(batch_id, include_soft_deleted, limit=100, offset=0)`

### [RunRepository]
**Definition**: Repository for `Run` entities.

**Specific methods**:
- `get_by_correlation_id(correlation_id, include_soft_deleted)`
- `list_by_automation(automation_id, limit=100, offset=0, status=None, include_soft_deleted=False)`
- `list_by_status(status, limit=100, offset=0, include_soft_deleted=False)`
- `find_running(automation_id=None, include_soft_deleted=False)`: Finds runs with status `PROCESSING` or `RETRYING`.

### [BatchExecutionRepository]
**Definition**: Repository for `BatchExecution` entities.

**Specific methods**:
- `get_by_run_and_batch(run_id, batch_id, include_soft_deleted)`
- `list_by_run(run_id, include_soft_deleted, limit=100, offset=0)`
- `list_by_batch(batch_id, include_soft_deleted, limit=100, offset=0)`

### [ItemExecutionRepository]
**Definition**: Repository for `ItemExecution` entities.

**Specific methods**:
- `get_by_run_and_item(run_id, item_id, include_soft_deleted)`
- `list_by_batch_execution(batch_execution_id, include_soft_deleted, limit=100, offset=0)`
- `list_pending_by_run(run_id, include_soft_deleted, limit=100, offset=0)`
- `list_failed_by_run(run_id, include_soft_deleted, limit=100, offset=0)`
- `count_by_status(run_id, status, include_soft_deleted)`

### [ItemStateHistoryRepository]
**Definition**: Repository for `ItemStateHistory` entities.

**Specific methods**:
- `list_by_item_execution(item_execution_id, limit=100, offset=0, include_soft_deleted=False)`
- `get_latest_by_item_execution(item_execution_id, include_soft_deleted=False)`

**Special behavior**:
- **`use_versioning = False`** – no optimistic locking; history records are immutable.
- **`updatable_fields = []`** – no fields can be updated.
- **`update()` and `delete()`** are overridden to raise `NotImplementedError`, as history records cannot be modified or removed.

### [EngineRepository]
**Definition**: Repository for `Engine` entities.

**Specific methods**:
- `get_by_name(name, include_soft_deleted)`
- `list_by_type(engine_type, include_soft_deleted, limit=100, offset=0)`

### [OrchestrationInstanceRepository]
**Definition**: Repository for `OrchestrationInstance` entities.

**Specific methods**:
- `get_by_engine_and_external(engine_id, external_id, include_soft_deleted)`
- `list_by_engine(engine_id, include_soft_deleted, limit=100, offset=0)`
- `list_by_status(status, include_soft_deleted, limit=100, offset=0)`
- `list_running(include_soft_deleted, limit=100, offset=0)`

### [RunOrchestrationRepository]
**Definition**: Repository for `RunOrchestration` entities.

**Specific methods**:
- `get_by_run_and_instance(run_id, instance_id, include_soft_deleted)`
- `list_by_run(run_id, include_soft_deleted, limit=100, offset=0)`
- `list_by_instance(instance_id, include_soft_deleted, limit=100, offset=0)`