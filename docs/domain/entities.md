## Domain Entities

### [Automation]
**Definition**: Core configuration entity representing an automated process definition.

**Purpose**: Serve as the root aggregate for all automation-related entities; defines the blueprint for batches and items.

**Key characteristics**:
- **name**: Unique identifier (string, required, stripped).
- **description**: Optional explanation.
- **batch_schema**: Optional JSON schema for batch payloads.
- **item_schema**: Optional JSON schema for item payloads.
- Inherits `DomainEntity` fields: `id`, `created_at`, `updated_at`, `created_by`, `updated_by`, `version`, `is_active`, `_events`.
- Validates `name` not empty in `__post_init__`.
- `update_schemas()` allows changing schemas and validates them.
- `__post_init__` now validates schemas if provided at creation time.

**Relationships / Rules**:
- Owns `Batch` entities (one-to-many).
- Owns `Run` entities (one-to-many).
- Schemas, if provided, are used to validate batch/item payloads during execution.
- In the database, a **partial unique index** (`ix_automation_name_active`) ensures unique `name` only for active automations (`WHERE is_active = true`), allowing soft-deleted records to retain the same name.

**Examples**:
```python
automation = Automation(name="Data Import", description="Import customer data")
automation.update_schemas(batch_schema={...}, item_schema={...})
```

### [Batch]
**Definition**: Logical group of items within an automation.

**Purpose**: Organize items into manageable groups with custom payloads, enabling batch-level operations and tracking.

**Key characteristics**:
- **automation_id**: UUID reference to parent `Automation`.
- **name**: Unique within automation (string, stripped).
- **payload**: Optional JSON data for batch-level configuration.
- Inherits `DomainEntity`.
- Validates `name` and `automation_id` in `__post_init__`.
- `update_payload()` allows modifying payload.

**Relationships / Rules**:
- Belongs to an `Automation`.
- Owns `Item` entities (ordered by `sequence_number`).
- Can have multiple `BatchExecution` records.
- Unique constraint: (`automation_id`, `name`) in the database.

**Examples**:
```python
batch = Batch(automation_id=automation.id, name="Q1-2024", payload={"quarter": 1})
```

### [Item]
**Definition**: Individual unit of work within a batch.

**Purpose**: Represent a single actionable item with sequential ordering; atomic unit of processing.

**Key characteristics**:
- **batch_id**: UUID reference to parent `Batch`.
- **sequence_number**: Integer position within batch (>=0).
- **payload**: Optional JSON data for item-specific content.
- Inherits `DomainEntity`.
- Validates `batch_id` and `sequence_number` in `__post_init__`.
- `update_payload()` allows modifying payload.

**Relationships / Rules**:
- Belongs to a `Batch`.
- Can have multiple `ItemExecution` records.
- Unique constraint: (`batch_id`, `sequence_number`).

**Examples**:
```python
item = Item(batch_id=batch.id, sequence_number=1, payload={"customer_id": 123})
```

### [Run]
**Definition**: Single execution instance of an automation.

**Purpose**: Track overall execution lifecycle, status transitions, errors, and performance.

**Key characteristics**:
- **automation_id**: UUID reference to `Automation`.
- **correlation_id**: Optional external tracking ID.
- **cancellation_reason**: Optional text explaining cancellation.
- **error_summary**: Optional high-level error.
- **status**: `ExecutionStatus` enum (default PENDING).
- **started_at**, **finished_at**: Optional timestamps.
- Inherits `DomainEntity`.
- Provides state transition methods: `start()`, `complete()`, `fail()`, `cancel()`.
- Each transition validates current status and bumps version.
- Emits corresponding domain events (`RunCompleted`, `RunFailed`, `RunCancelled`).

**Relationships / Rules**:
- Belongs to an `Automation`.
- Owns `BatchExecution` and `ItemExecution` records.
- May be linked to `OrchestrationInstance` via `RunOrchestration`.
- Status transitions are governed by `ExecutionStatus.can_transition_to()`.

**Examples**:
```python
run = Run(automation_id=automation.id)
run.start()      # status -> PROCESSING, version++
run.complete()   # status -> COMPLETED, version++, emits RunCompleted
```

### [BatchExecution]
**Definition**: Tracks execution status of a specific batch within a run.

**Purpose**: Monitor batch-level progress, success/failure, and provide granular visibility.

**Key characteristics**:
- **run_id**: UUID reference to parent `Run`.
- **batch_id**: UUID reference to `Batch`.
- **status**: `ExecutionStatus` enum.
- **started_at**, **finished_at**: Optional timestamps.
- Inherits `DomainEntity`.
- Provides `start()`, `complete()`, `fail()` methods.
- Emits `BatchExecutionFailed` on failure.

**Relationships / Rules**:
- Belongs to a `Run` and a `Batch`.
- Owns `ItemExecution` records.
- Unique constraint: (`run_id`, `batch_id`).

**Examples**:
```python
batch_exec = BatchExecution(run_id=run.id, batch_id=batch.id)
batch_exec.start()
batch_exec.complete()
```

### [ItemExecution]
**Definition**: Tracks execution of individual items with retry support.

**Purpose**: Provide granular tracking of each item's execution, including results, errors, and retry attempts.

**Key characteristics**:
- **run_id**: UUID reference to parent `Run`.
- **batch_execution_id**: UUID reference to `BatchExecution`.
- **item_id**: UUID reference to `Item`.
- **result_payload**: Optional JSON output from successful execution.
- **error_message**: Optional string error details.
- **status**: `ExecutionStatus` enum.
- **started_at**, **finished_at**: Optional timestamps.
- **attempt_count**: Integer, number of attempts (default 0).
- **max_attempts**: Optional integer, maximum allowed attempts.
- Inherits `DomainEntity`.
- **Retry rule**: If `max_attempts` is set and attempts < max, `fail()` transitions to `RETRYING`; otherwise to `FAILED`. If `max_attempts` is `None`, no retry is allowed (goes directly to `FAILED`).
- Methods: `start()`, `complete()`, `fail()`, `can_retry()`.
- **Guard in `start()`**: If `max_attempts` is not `None` and `attempt_count >= max_attempts`, `start()` raises `InvalidStateError` to prevent exceeding the retry limit.
- Emits `ItemExecutionFailed` on failure (whether transitioning to `RETRYING` or `FAILED`).

**Relationships / Rules**:
- Belongs to a `Run`, `BatchExecution`, and `Item`.
- Owns `ItemStateHistory` records.
- Status transitions are validated.

**Examples**:
```python
item_exec = ItemExecution(run_id=run.id, batch_execution_id=batch_exec.id, item_id=item.id, max_attempts=3)
item_exec.start()        # attempt_count becomes 1, status PROCESSING
item_exec.fail("Timeout") # if attempts < max_attempts, status RETRYING
```

### [ItemStateHistory]
**Definition**: Immutable audit record of a state change for an item execution.

**Purpose**: Provide a complete, append‑only history of status transitions for debugging, compliance, and audit requirements.

**Key characteristics**:
- **id**: UUID (generated automatically).
- **item_execution_id**: UUID reference to `ItemExecution`.
- **previous_status**: Optional previous `ExecutionStatus`.
- **new_status**: Current `ExecutionStatus` (required).
- **changed_at**: Timestamp of the state transition (defaults to now).
- **created_at**: Timestamp of record creation (automatically set, required).
- **created_by**: Optional user who triggered the transition.
- **No version field**: History records are immutable and never updated; optimistic locking is irrelevant.
- **No soft delete**: Records are never soft‑deleted; they are permanently retained for audit purposes.
- **Not a `DomainEntity`**: Does not inherit from `DomainEntity` because it lacks identity, versioning, and lifecycle methods.

**Relationships / Rules**:
- Belongs to an `ItemExecution`.
- Records are automatically created when an item execution’s status changes (via repository or domain events).
- **Immutable**: Once created, cannot be updated or deleted. Attempts to call `update()` or `delete()` on its repository will raise `NotImplementedError`.

**Examples**:
```python
history = ItemStateHistory(
    item_execution_id=item_exec.id,
    previous_status=ExecutionStatus.PENDING,
    new_status=ExecutionStatus.PROCESSING
)
```

### [Engine]
**Definition**: Represents external orchestration systems (Jenkins, Argo, etc.).

**Purpose**: Manage connections to different workflow engines, providing abstraction over external systems.

**Key characteristics**:
- **name**: Unique identifier for the engine (string, stripped).
- **type**: Engine type classification (string, stripped).
- Inherits `DomainEntity`.
- Validates `name` and `type` not empty.

**Relationships / Rules**:
- Owns `OrchestrationInstance` records.
- Unique constraint on `name`.

**Examples**:
```python
engine = Engine(name="jenkins-prod", type="Jenkins")
```

### [OrchestrationInstance]
**Definition**: Represents a specific workflow instance in an external engine.

**Purpose**: Track external workflow executions linked to our system, enabling cross-system traceability.

**Key characteristics**:
- **engine_id**: UUID reference to `Engine`.
- **external_id**: External system's identifier (string, stripped).
- **duration_seconds**: Optional execution duration.
- **instance_metadata**: Optional JSON data from external system (renamed from `metadata` to avoid conflict with SQLAlchemy).
- **status**: `ExecutionStatus` enum.
- **started_at**, **finished_at**: Optional timestamps.
- Inherits `DomainEntity`.
- Methods: `start()`, `complete()`, `fail()`.

**Relationships / Rules**:
- Belongs to an `Engine`.
- Linked to `Run` via `RunOrchestration`.
- Unique constraint: (`engine_id`, `external_id`).

**Examples**:
```python
instance = OrchestrationInstance(engine_id=engine.id, external_id="build-123")
instance.start()
instance.complete()  # calculates duration
```

### [RunOrchestration]
**Definition**: Link table connecting runs to orchestration instances.

**Purpose**: Create many-to-many relationship between runs and orchestration instances, enabling complex orchestration scenarios.

**Key characteristics**:
- **run_id**: UUID reference to `Run`.
- **orchestration_instance_id**: UUID reference to `OrchestrationInstance`.
- **attached_at**: Timestamp when the link was established.
- Inherits `DomainEntity` (including version and audit fields).

**Relationships / Rules**:
- Belongs to a `Run` and an `OrchestrationInstance`.
- Unique constraint: (`run_id`, `orchestration_instance_id`).

**Examples**:
```python
link = RunOrchestration(run_id=run.id, orchestration_instance_id=instance.id)
```