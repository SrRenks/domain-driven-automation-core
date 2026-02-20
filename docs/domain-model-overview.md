# Automation Platform Core – Domain Overview

A robust, domain‑driven core for building automation platforms. It provides the essential building blocks to define, execute, and track automated processes, batches, and items, with full auditability and support for external orchestration engines.

## Architecture Overview

The project follows **Domain‑Driven Design (DDD)** principles, with a clear separation between domain, infrastructure, and application layers.

- **`project/domain/`** – Contains all domain logic: entities, value objects, enums, exceptions, and repository interfaces.
- **`project/infrastructure/`** – Implements persistence (SQLAlchemy models, repositories, Unit of Work), logging, and other technical concerns.
- **`project/utils/`** – Utility modules like the custom Rich‑compatible logger.
- **`docs/`** – Detailed documentation of the domain and infrastructure components (this folder).

## Core Concepts

- **Automation** – The root aggregate; defines a process with optional JSON schemas for batch and item payloads.
- **Batch** – A logical group of items within an automation.
- **Item** – An atomic unit of work inside a batch.
- **Run** – A single execution instance of an automation, tracking overall lifecycle.
- **BatchExecution** / **ItemExecution** – Track execution status of batches and items, including retries.
- **ItemStateHistory** – Immutable audit trail of item execution status changes.
- **Engine** / **OrchestrationInstance** – Represent external workflow engines (Jenkins, Argo, etc.) and link them to runs.

For a deep dive, refer to the [Domain Entities](domain/entities.md) documentation.

## Documentation Structure

The documentation is split into two main sections: **Domain** and **Infrastructure**. Each file focuses on a specific aspect of the system, providing definitions, purpose, key characteristics, relationships, and examples.

### How to Navigate the Docs

If you are new to the project, we recommend reading the documentation in the following order:

1. **Start with the Domain Base Classes** – Understand the building blocks: [`ValueObject`](domain/base.md#valueobject) and [`DomainEntity`](domain/base.md#domainentity).  
2. **Explore Value Objects** – Learn about immutable types like [`Schema`](domain/value_objects.md#schema) and [`AuditInfo`](domain/value_objects.md#auditinfo).  
3. **Study the Core Entities** – Read [`Automation`](domain/entities.md#automation), [`Batch`](domain/entities.md#batch), [`Item`](domain/entities.md#item), and then move to execution entities ([`Run`](domain/entities.md#run), [`BatchExecution`](domain/entities.md#batchexecution), [`ItemExecution`](domain/entities.md#itemexecution)). Pay special attention to [`ItemStateHistory`](domain/entities.md#itemstatehistory) – an immutable audit record.  
4. **Understand Orchestration** – See how external systems are represented via [`Engine`](domain/entities.md#engine) and [`OrchestrationInstance`](domain/entities.md#orchestrationinstance).  
5. **Review Enums and Exceptions** – [`ExecutionStatus`](domain/enums.md) defines the state machine; [domain exceptions](domain/exceptions.md) are used throughout.  
6. **Move to Infrastructure** – Start with the [database models](infrastructure/database/models.md) to see how entities are persisted, then dive into [repositories](infrastructure/repositories.md) and the [Unit of Work](infrastructure/unit_of_work.md).  
7. **Check Logging and Infrastructure Exceptions** – [Logging](infrastructure/logging.md) and [infrastructure exceptions](infrastructure/exceptions.md) are useful for integration.

### Domain Layer

| File | Description |
|------|-------------|
| [`domain/base.md`](domain/base.md) | Base classes `ValueObject` (immutable) and `DomainEntity` (common fields and behaviors, event handling). |
| [`domain/entities.md`](domain/entities.md) | All domain entities: Automation, Batch, Item, Run, BatchExecution, ItemExecution, ItemStateHistory, Engine, OrchestrationInstance, RunOrchestration. |
| [`domain/value_objects.md`](domain/value_objects.md) | Value objects: AuditInfo, VersionInfo, Schema, SchemaValidationResult. |
| [`domain/enums.md`](domain/enums.md) | `ExecutionStatus` enum with state transition rules and helper properties. |
| [`domain/events.md`](domain/events.md) | Domain events raised by entities (ItemExecutionFailed, RunCompleted, etc.). |
| [`domain/exceptions.md`](domain/exceptions.md) | Domain‑specific exceptions: `DomainError`, `ValidationError`, `InvalidStateError`. |

### Infrastructure Layer

| File | Description |
|------|-------------|
| [`infrastructure/database/models.md`](infrastructure/database/models.md) | SQLAlchemy models, mixins (Timestamp, Audit, Version, StatusTracking, Retryable), indexes, cascade rules, and the core architecture diagram. |
| [`infrastructure/repositories.md`](infrastructure/repositories.md) | Repository implementations: `BaseRepository` (generic CRUD with optimistic locking and soft delete) and all concrete repositories. |
| [`infrastructure/unit_of_work.md`](infrastructure/unit_of_work.md) | Unit of Work pattern and `EventBus` for transaction‑scoped operations and event dispatch. |
| [`infrastructure/exceptions.md`](infrastructure/exceptions.md) | Infrastructure‑layer exceptions: `RepositoryError`, `EntityNotFoundError`, `DuplicateEntityError`, `ConcurrencyError`. |
| [`infrastructure/logging.md`](infrastructure/logging.md) | Custom logger with Rich formatting and tqdm integration for CLI applications. |

## Quick Start Example

Here’s a minimal example to create an automation, add a batch, and start a run.

```python
from project.infrastructure.database import DatabaseConfig
from project.infrastructure.uow import UnitOfWork, EventBus
from project.domain.entities import Automation, Batch, Run

# Setup database and event bus
db_config = DatabaseConfig("postgresql://user:pass@localhost/automation_db")
event_bus = EventBus()

# Use Unit of Work for atomic operations
with UnitOfWork(db_config, event_bus) as uow:
    # 1. Create an automation
    automation = Automation(name="Data Import", description="Import customer data")
    uow.automations.create(automation, user="admin")

    # 2. Create a batch under that automation
    batch = Batch(automation_id=automation.id, name="Q1-2024")
    uow.batches.create(batch, user="admin")

    # 3. Start a run
    run = Run(automation_id=automation.id, correlation_id="ext-123")
    uow.runs.create(run, user="admin")
    run.start()                     # transition to PROCESSING
    uow.runs.update(run.id, run, user="admin")

    # Commit everything
    uow.commit()
```