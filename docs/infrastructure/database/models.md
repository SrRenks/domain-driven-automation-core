## **Domain-Driven Database Design: Model Documentation**

### **Core Architecture Concept**

**Domain-Driven Database Design**: Database models organized around business domains (Definition, Execution, Orchestration) with clear separation of concerns.

**Purpose**: Creates maintainable, scalable data structures that mirror business capabilities while ensuring data integrity and auditability.

**Key characteristics:**
- **Domain separation**: Models grouped by business capability (definition, execution, orchestration)
- **Audit readiness**: All models include `created_at/updated_at`, `created_by/updated_by`, and version fields (via mixins)
- **Status tracking**: Executable entities track status, start/finish times, and durations (via `StatusTrackingMixin`)
- **Cascade relationships**: Parent-child deletions cascade to maintain referential integrity
- **Optimistic locking**: Most models include a `version` field (via `VersionMixin`) to prevent concurrent modification conflicts. Exceptions are noted (e.g., `ItemStateHistoryModel`).
- **Soft delete support**: Most models have an `is_active` flag (default true) to support soft deletion. Exceptions are noted (e.g., `ItemStateHistoryModel`).
- **JSONB flexibility**: Payloads and schemas stored as JSONB for schema-less extensibility

**Relationships / Rules:**
- Definition → Execution: Automation definitions drive runtime executions
- Execution → Orchestration: Runs link to external orchestration systems
- All models inherit from `Base` with UUID primary keys
- All models use SQLAlchemy 2.0 style with `Mapped` annotations
- Foreign keys are indexed for query performance
- Unique constraints enforce business rules (e.g., automation name uniqueness, batch name per automation)

**Examples:**
- AutomationModel (definition) → RunModel (execution) → OrchestrationInstanceModel (orchestration)
- BatchModel (definition) → BatchExecutionModel (execution) → ItemExecutionModel (execution)

## **Domain: Definition Models**

### [AutomationModel]
Core configuration entity representing an automated process definition.

**Purpose**: Stores the blueprint for automation including schemas for batches and items, serving as the root aggregate for all automation-related entities.

**Key characteristics:**
- **name**: Unique identifier for automation (`String(200)`, indexed). A **partial unique index** (`ix_automation_name_active`) enforces uniqueness only for active automations (`WHERE is_active = true`), allowing soft-deleted records to retain the same name.
- **description**: Optional detailed explanation of automation purpose
- **is_active**: Controls whether automation can be executed (default true, server default)
- **batch_schema**: `JSONB` schema defining expected batch structure
- **item_schema**: `JSONB` schema defining expected item structure
- **Audit fields**: `created_at`, `updated_at`, `created_by`, `updated_by` (via mixins)
- **Version control**: Optimistic locking via `version` field

**Relationships / Rules:**
- **One-to-Many** with `BatchModel` (`automation_id` FK, cascade delete)
- **One-to-Many** with `RunModel` (`automation_id` FK, cascade delete)
- Index on `name` for fast lookup

### [BatchModel]
Represents a logical group of items within an automation.

**Purpose**: Organizes items into manageable groups with custom payloads, enabling batch-level operations and tracking.

**Key characteristics:**
- **automation_id**: Foreign key to parent automation (indexed, cascade delete)
- **name**: Unique identifier within automation context (`String(200)`)
- **payload**: Optional `JSONB` data for batch-level configuration
- **Audit fields**: Full audit trail with timestamps and user tracking
- **Version control**: Optimistic locking enabled
- **is_active**: Soft delete flag

**Relationships / Rules:**
- **Many-to-One** with `AutomationModel` (back_populates="batches")
- **One-to-Many** with `ItemModel` (ordered by `sequence_number`)
- **One-to-Many** with `BatchExecutionModel`
- **Unique constraint**: (`automation_id`, `name`) ensures batch names are unique per automation

### [ItemModel]
Individual unit of work within a batch.

**Purpose**: Represents a single actionable item with sequential ordering, forming the atomic unit of processing.

**Key characteristics:**
- **batch_id**: Foreign key to parent batch (indexed, cascade delete)
- **sequence_number**: Position within batch (`Integer`, required)
- **payload**: Optional `JSONB` data for item-specific content
- **Full audit capabilities**: Timestamps and user tracking
- **Version field**: For optimistic locking
- **is_active**: Soft delete flag

**Relationships / Rules:**
- **Many-to-One** with `BatchModel` (back_populates="items")
- **One-to-Many** with `ItemExecutionModel`
- **Unique constraint**: (`batch_id`, `sequence_number`) ensures ordered uniqueness

## **Domain: Execution Models**

### [RunModel]
Represents a single execution instance of an automation.

**Purpose**: Tracks the overall execution lifecycle from start to finish, including status transitions, errors, and performance metrics.

**Key characteristics:**
- **automation_id**: Foreign key to automation being executed (indexed, cascade delete)
- **correlation_id**: External tracking identifier (`String(100)`, indexed)
- **cancellation_reason**: `Text` explaining why run was cancelled
- **error_summary**: High-level error information (`Text`)
- **Status tracking**: Inherits `StatusTrackingMixin` with `status`, `started_at`, `finished_at`
- **Duration property**: Calculates execution time automatically (`duration`)
- **Full audit trail**: Created/updated timestamps and user tracking
- **is_active**: Soft delete flag
- **Version control**: Optimistic locking

**Relationships / Rules:**
- **Many-to-One** with `AutomationModel` (back_populates="runs")
- **One-to-Many** with `BatchExecutionModel` (cascade delete)
- **One-to-Many** with `ItemExecutionModel` (cascade delete)
- **One-to-Many** with `RunOrchestrationModel` (cascade delete)
- **Compound index**: (`started_at`, `status`) for efficient querying

### [BatchExecutionModel]
Tracks execution status of a specific batch within a run.

**Purpose**: Monitors batch-level progress, success/failure, and provides granular visibility into batch processing.

**Key characteristics:**
- **run_id**: Foreign key to parent run (cascade delete)
- **batch_id**: Foreign key to the batch being executed (cascade delete)
- **Status tracking**: Inherits `StatusTrackingMixin`
- **Audit fields**: Complete user and timestamp tracking
- **is_active**: Soft delete flag
- **Version control**: Optimistic locking enabled

**Relationships / Rules:**
- **Many-to-One** with `RunModel` (back_populates="batch_executions")
- **Many-to-One** with `BatchModel` (back_populates="executions")
- **One-to-Many** with `ItemExecutionModel` (cascade delete)
- **Unique constraint**: (`run_id`, `batch_id`) ensures one execution per batch per run
- **Index**: On `status` field for filtered queries

### [ItemExecutionModel]
Tracks execution of individual items with retry support.

**Purpose**: Provides granular tracking of each item's execution, including results, errors, and retry attempts.

**Key characteristics:**
- **run_id**: Foreign key to parent run (cascade delete)
- **batch_execution_id**: Foreign key to batch execution (cascade delete)
- **item_id**: Foreign key to the item being executed (cascade delete)
- **result_payload**: `JSONB` output from successful execution
- **error_message**: `String` error details if failed
- **Retry capabilities**: Inherits `RetryableMixin` (`attempt_count`, `max_attempts`)
- **Status tracking**: Complete lifecycle status with timestamps
- **Full audit**: All audit fields and version control
- **is_active**: Soft delete flag

**Relationships / Rules:**
- **Many-to-One** with `RunModel` (back_populates="item_executions")
- **Many-to-One** with `BatchExecutionModel` (back_populates="item_executions")
- **Many-to-One** with `ItemModel` (back_populates="executions")
- **One-to-Many** with `ItemStateHistoryModel` (cascade delete)
- **Indexes**: On `run_id`, `batch_execution_id`, `status`, `item_id` for query performance
- **Unique constraint**: (`run_id`, `item_id`) ensures one execution per item per run

### [ItemStateHistoryModel]
Audit trail of state changes for item executions.

**Purpose**: Provides complete history of status transitions for debugging, compliance, and audit requirements.

**Key characteristics**:
- **item_execution_id**: UUID reference to `ItemExecution` (indexed, cascade delete)
- **previous_status**: Optional previous `ExecutionStatus`
- **new_status**: Current `ExecutionStatus` (required)
- **changed_at**: Timestamp of state transition (defaults to `func.now()`)
- **created_at**: Timestamp of record creation (automatically set)
- **created_by**: Optional user who triggered the transition
- **No version control**: This model does **not** use `VersionMixin` because history records are immutable.
- **No soft delete**: History records are never soft‑deleted.
- **Not a `DomainEntity`**: This model is purely for audit and does not implement entity lifecycle methods.

**Relationships / Rules**:
- **Many-to-One** with `ItemExecutionModel` (back_populates="state_history")
- **Compound index**: (`item_execution_id`, `changed_at`) for efficient history queries
- Automatic timestamp on creation
- **Immutable**: The corresponding repository (`ItemStateHistoryRepository`) disables versioning (`use_versioning = False`) and raises `NotImplementedError` for `update()` and `delete()`.

## **Domain: Orchestration Models**

### [EngineModel]
Represents external orchestration systems (Jenkins, Argo, etc.).

**Purpose**: Manages connections to different workflow engines that can execute automations, providing abstraction over external systems.

**Key characteristics:**
- **name**: Unique identifier for the engine (`String(100)`, unique)
- **type**: Engine type classification (`String(50)`)
- **Full audit**: Timestamps and user tracking
- **Version control**: Optimistic locking
- **is_active**: Soft delete flag

**Relationships / Rules:**
- **One-to-Many** with `OrchestrationInstanceModel` (cascade delete)
- Unique constraint on `name` ensures no duplicate engines

### [OrchestrationInstanceModel]
Represents a specific workflow instance in an external engine.

**Purpose**: Tracks external workflow executions linked to our system, enabling cross-system traceability.

**Key characteristics:**
- **engine_id**: Foreign key to parent engine (cascade delete)
- **external_id**: External system's identifier (`String(200)`)
- **duration_seconds**: Execution duration if known (`Integer`)
- **instance_metadata**: Additional `JSONB` data from external system (renamed from `metadata`)
- **Status tracking**: Complete lifecycle status (`StatusTrackingMixin`)
- **Audit fields**: Full audit trail
- **is_active**: Soft delete flag
- **Version control**: Optimistic locking

**Relationships / Rules:**
- **Many-to-One** with `EngineModel` (back_populates="instances")
- **One-to-Many** with `RunOrchestrationModel` (cascade delete)
- **Unique constraint**: (`engine_id`, `external_id`) ensures no duplicates
- **Compound index**: (`status`, `started_at`) for monitoring

### [RunOrchestrationModel]
Link table connecting runs to orchestration instances.

**Purpose**: Creates many-to-many relationship between runs and orchestration instances, enabling complex orchestration scenarios.

**Key characteristics:**
- **run_id**: Foreign key to run (cascade delete)
- **orchestration_instance_id**: Foreign key to orchestration instance (cascade delete)
- **attached_at**: When the link was established (`DateTime`, required)
- **Audit fields**: Complete tracking (`TimestampMixin`, `AuditMixin`, `VersionMixin`)
- **is_active**: Soft delete flag

**Relationships / Rules:**
- **Many-to-One** with `RunModel` (back_populates="orchestration")
- **Many-to-One** with `OrchestrationInstanceModel` (back_populates="runs")
- **Unique constraint**: (`run_id`, `orchestration_instance_id`) prevents duplicate links

## **Mixins (Reusable Components)**

### [TimestampMixin]
Adds creation and modification timestamps.

**Purpose**: Provides automatic time tracking for all records with timezone support.

**Key characteristics:**
- **created_at**: `DateTime(timezone=True)`, server default `func.now()`, non-nullable
- **updated_at**: `DateTime(timezone=True)`, server default `func.now()`, onupdate `func.now()`, non-nullable

### [AuditMixin]
Adds user tracking fields.

**Purpose**: Identifies who created/modified records for audit trails and compliance.

**Key characteristics:**
- **created_by**: Optional `String(100)` identifying creator
- **updated_by**: Optional `String(100)` identifying last modifier

### [VersionMixin]
Adds optimistic locking support.

**Purpose**: Prevents concurrent modification conflicts in distributed systems.

**Key characteristics:**
- **version**: `Integer`, default 1, nullable=False, incremented on each update
- Throws `StaleDataError` on concurrent modification

### [StatusTrackingMixin]
Standard execution status fields.

**Purpose**: Provides consistent status tracking across all executable entities.

**Key characteristics:**
- **status**: `Enum(ExecutionStatus)`, indexed for performance, nullable=False
- **started_at**: `DateTime(timezone=True)`, optional
- **finished_at**: `DateTime(timezone=True)`, optional
- **duration**: Property calculating execution time automatically (`finished_at - started_at` if both present)

### [RetryableMixin]
Adds retry capability for executable items.

**Purpose**: Supports fault tolerance through automatic retries with configurable attempts.

**Key characteristics:**
- **attempt_count**: `Integer`, default 0, nullable=False
- **max_attempts**: `Integer`, optional

## **Database Configuration**

### [DatabaseConfig]
Central database configuration and session management.

**Purpose**: Manages database connections, connection pooling, and session lifecycle.

**Key characteristics**:
- **Connection pooling**: `QueuePool` with configurable `pool_size` and `max_overflow`
- **Pool pre-ping**: Verifies connections before use (`pool_pre_ping=True`)
- **Session factory**: Thread-local sessions with `autocommit=False`, `autoflush=False`
- **Context manager**: `get_session()` yields a session that is automatically closed.
- **Graceful shutdown**: `dispose_engine()` closes the connection pool (call during application shutdown).

**Configuration parameters**:
- `database_url`: PostgreSQL connection string (required)
- `pool_size`: Size of the connection pool (default 5)
- `max_overflow`: Maximum overflow connections (default 10)
- `engine_kwargs`: Additional keyword arguments passed to `create_engine` (e.g., `{'echo': True}` for SQL logging)

**Examples**:
```python
db_config = DatabaseConfig(
    database_url="postgresql://user:pass@localhost/db",
    pool_size=10,
    engine_kwargs={"echo": True}
)

with db_config.get_session() as session:
    result = session.execute("SELECT 1")

# On application shutdown:
db_config.dispose_engine()
```

## **Indexing Strategy**

| Model | Indexed Fields | Purpose |
|-------|---------------|---------|
| AutomationModel | `name`, `is_active` | Fast lookup by name and active filtering |
| BatchModel | `automation_id`, `is_active` | Filter batches by automation |
| ItemModel | `batch_id`, `is_active` | Filter items by batch |
| RunModel | `automation_id`, `correlation_id`, (`started_at`, `status`), `is_active` | Multi-purpose querying |
| BatchExecutionModel | `status`, `is_active` | Filter by execution status |
| ItemExecutionModel | `run_id`, `batch_execution_id`, `status`, `item_id`, `is_active` | Multiple query paths |
| ItemStateHistoryModel | `item_execution_id`, (`item_execution_id`, `changed_at`) | History traversal |
| EngineModel | `is_active` | Filter active engines |
| OrchestrationInstanceModel | `engine_id`, (`status`, `started_at`), `is_active` | Monitoring queries |
| RunOrchestrationModel | `run_id`, `orchestration_instance_id`, `is_active` | Link lookups |

## **Cascade Rules Summary**

| Parent | Child | Cascade Type |
|--------|-------|--------------|
| AutomationModel | BatchModel | ALL, DELETE-ORPHAN |
| AutomationModel | RunModel | ALL, DELETE-ORPHAN |
| BatchModel | ItemModel | ALL, DELETE-ORPHAN |
| BatchModel | BatchExecutionModel | ALL, DELETE-ORPHAN |
| RunModel | BatchExecutionModel | ALL, DELETE-ORPHAN |
| RunModel | ItemExecutionModel | ALL, DELETE-ORPHAN |
| RunModel | RunOrchestrationModel | ALL, DELETE-ORPHAN |
| ItemExecutionModel | ItemStateHistoryModel | ALL, DELETE-ORPHAN |
| EngineModel | OrchestrationInstanceModel | ALL, DELETE-ORPHAN |
| OrchestrationInstanceModel | RunOrchestrationModel | ALL, DELETE-ORPHAN |

## **Best Practices Implemented**

1. **Domain Separation**: Clear boundaries between definition, execution, and orchestration
2. **Audit Readiness**: Every model has complete audit trail (`TimestampMixin`, `AuditMixin`)
3. **Optimistic Locking**: Version fields prevent data corruption in concurrent environments (except immutable history)
4. **Index Strategy**: Indexes on all foreign keys and frequently queried fields
5. **Cascade Rules**: Consistent cascade delete policies across aggregates
6. **Type Safety**: Full Python type hints and SQLAlchemy 2.0 `Mapped` syntax
7. **Enum Usage**: Status fields use `ExecutionStatus` enum for type safety and state machine
8. **JSONB Support**: Flexible schema-less fields where appropriate (payloads, schemas)
9. **Connection Pooling**: Production-ready database configuration with `pool_pre_ping`
10. **Import Resolution**: `TYPE_CHECKING` used to prevent circular imports in relationships
11. **Soft Delete**: All models include `is_active` flag, and repositories handle filtering (except immutable history)
12. **Consistent Naming**: Model classes suffixed with `Model`, clear singular table names

## Core Architecture Diagram

```mermaid
classDiagram
    %% Domain: Definition Models
    class AutomationModel {
        +UUID id
        +String name
        +String description
        +Boolean is_active
        +JSONB batch_schema
        +JSONB item_schema
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class BatchModel {
        +UUID id
        +UUID automation_id
        +String name
        +JSONB payload
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class ItemModel {
        +UUID id
        +UUID batch_id
        +Int sequence_number
        +JSONB payload
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    %% Domain: Execution Models
    class RunModel {
        +UUID id
        +UUID automation_id
        +String correlation_id
        +String cancellation_reason
        +String error_summary
        +ExecutionStatus status
        +DateTime started_at
        +DateTime finished_at
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
        +get_duration()
    }

    class BatchExecutionModel {
        +UUID id
        +UUID run_id
        +UUID batch_id
        +ExecutionStatus status
        +DateTime started_at
        +DateTime finished_at
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class ItemExecutionModel {
        +UUID id
        +UUID run_id
        +UUID batch_execution_id
        +UUID item_id
        +JSONB result_payload
        +String error_message
        +Int attempt_count
        +Int max_attempts
        +ExecutionStatus status
        +DateTime started_at
        +DateTime finished_at
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class ItemStateHistoryModel {
        +UUID id
        +UUID item_execution_id
        +ExecutionStatus previous_status
        +ExecutionStatus new_status
        +DateTime changed_at
        +DateTime created_at
        +String created_by
    }

    %% Domain: Orchestration Models
    class EngineModel {
        +UUID id
        +String name
        +String type
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class OrchestrationInstanceModel {
        +UUID id
        +UUID engine_id
        +String external_id
        +Int duration_seconds
        +JSONB instance_metadata
        +ExecutionStatus status
        +DateTime started_at
        +DateTime finished_at
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    class RunOrchestrationModel {
        +UUID id
        +UUID run_id
        +UUID orchestration_instance_id
        +DateTime attached_at
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +String created_by
        +String updated_by
        +Int version
    }

    %% Relationships
    AutomationModel "1" -- "many" BatchModel : contains
    AutomationModel "1" -- "many" RunModel : defines
    BatchModel "1" -- "many" ItemModel : groups
    BatchModel "1" -- "many" BatchExecutionModel : tracks
    RunModel "1" -- "many" BatchExecutionModel : contains
    RunModel "1" -- "many" ItemExecutionModel : contains
    RunModel "1" -- "many" RunOrchestrationModel : links to
    BatchExecutionModel "1" -- "many" ItemExecutionModel : groups
    ItemExecutionModel "1" -- "many" ItemStateHistoryModel : histories
    EngineModel "1" -- "many" OrchestrationInstanceModel : runs
    OrchestrationInstanceModel "1" -- "many" RunOrchestrationModel : linked from
```