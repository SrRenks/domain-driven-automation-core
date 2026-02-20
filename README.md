# Automation Platform Core

A robust, domain‑driven core for building automation platforms. It provides the essential building blocks to define, execute, and track automated processes, batches, and items, with full auditability and support for external orchestration engines.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Core Concepts](#core-concepts)
- [Documentation Structure](#documentation-structure)
  - [How to Navigate the Docs](#how-to-navigate-the-docs)
  - [Domain Layer](#domain-layer)
  - [Infrastructure Layer](#infrastructure-layer)
- [Quick Start Example](#quick-start-example)
- [Configuration & Setup](#configuration--setup)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

## Architecture Overview

The project follows **Domain‑Driven Design (DDD)** principles, with a clear separation between domain, infrastructure, and application layers.

- **`project/domain/`** – Contains all domain logic: entities, value objects, enums, exceptions, and repository interfaces.
- **`project/infrastructure/`** – Implements persistence (SQLAlchemy models, repositories, Unit of Work), logging, and other technical concerns.
- **`project/utils/`** – Utility modules like the custom Rich‑compatible logger.
- **`docs/`** – Detailed documentation of the domain and infrastructure components.

## Core Concepts

- **Automation** – The root aggregate; defines a process with optional JSON schemas for batch and item payloads.
- **Batch** – A logical group of items within an automation.
- **Item** – An atomic unit of work inside a batch.
- **Run** – A single execution instance of an automation, tracking overall lifecycle.
- **BatchExecution** / **ItemExecution** – Track execution status of batches and items, including retries.
- **ItemStateHistory** – Immutable audit trail of item execution status changes.
- **Engine** / **OrchestrationInstance** – Represent external workflow engines (Jenkins, Argo, etc.) and link them to runs.

For a deep dive, refer to the [Domain Entities](docs/domain/entities.md) documentation.

## Documentation Structure

The documentation is split into two main sections: **Domain** and **Infrastructure**. Each file focuses on a specific aspect of the system, providing definitions, purpose, key characteristics, relationships, and examples.

### How to Navigate the Docs

If you are new to the project, we recommend reading the documentation in the following order:

1. **Start with the Domain Base Classes** – Understand the building blocks: [`ValueObject`](docs/domain/base.md#valueobject) and [`DomainEntity`](docs/domain/base.md#domainentity).
2. **Explore Value Objects** – Learn about immutable types like [`Schema`](docs/domain/value_objects.md#schema) and [`AuditInfo`](docs/domain/value_objects.md#auditinfo).
3. **Study the Core Entities** – Read [`Automation`](docs/domain/entities.md#automation), [`Batch`](docs/domain/entities.md#batch), [`Item`](docs/domain/entities.md#item), and then move to execution entities ([`Run`](docs/domain/entities.md#run), [`BatchExecution`](docs/domain/entities.md#batchexecution), [`ItemExecution`](docs/domain/entities.md#itemexecution)). Pay special attention to [`ItemStateHistory`](docs/domain/entities.md#itemstatehistory) – an immutable audit record.
4. **Understand Orchestration** – See how external systems are represented via [`Engine`](docs/domain/entities.md#engine) and [`OrchestrationInstance`](docs/domain/entities.md#orchestrationinstance).
5. **Review Enums and Exceptions** – [`ExecutionStatus`](docs/domain/enums.md) defines the state machine; [domain exceptions](docs/domain/exceptions.md) are used throughout.
6. **Move to Infrastructure** – Start with the [database models](docs/infrastructure/database/models.md) to see how entities are persisted, then dive into [repositories](docs/infrastructure/repositories.md) and the [Unit of Work](docs/infrastructure/unit_of_work.md).
7. **Check Logging and Infrastructure Exceptions** – [Logging](docs/infrastructure/logging.md) and [infrastructure exceptions](docs/infrastructure/exceptions.md) are useful for integration.

### Domain Layer

| File | Description |
|------|-------------|
| [`docs/domain/base.md`](docs/domain/base.md) | Base classes `ValueObject` (immutable) and `DomainEntity` (common fields and behaviors, event handling). |
| [`docs/domain/entities.md`](docs/domain/entities.md) | All domain entities: Automation, Batch, Item, Run, BatchExecution, ItemExecution, ItemStateHistory, Engine, OrchestrationInstance, RunOrchestration. |
| [`docs/domain/value_objects.md`](docs/domain/value_objects.md) | Value objects: AuditInfo, VersionInfo, Schema, SchemaValidationResult. |
| [`docs/domain/enums.md`](docs/domain/enums.md) | `ExecutionStatus` enum with state transition rules and helper properties. |
| [`docs/domain/events.md`](docs/domain/events.md) | Domain events raised by entities (ItemExecutionFailed, RunCompleted, etc.). |
| [`docs/domain/exceptions.md`](docs/domain/exceptions.md) | Domain‑specific exceptions: `DomainError`, `ValidationError`, `InvalidStateError`. |

### Infrastructure Layer

| File | Description |
|------|-------------|
| [`docs/infrastructure/database/models.md`](docs/infrastructure/database/models.md) | SQLAlchemy models, mixins (Timestamp, Audit, Version, StatusTracking, Retryable), indexes, cascade rules, and the core architecture diagram. |
| [`docs/infrastructure/repositories.md`](docs/infrastructure/repositories.md) | Repository implementations: `BaseRepository` (generic CRUD with optimistic locking and soft delete) and all concrete repositories. |
| [`docs/infrastructure/unit_of_work.md`](docs/infrastructure/unit_of_work.md) | Unit of Work pattern and `EventBus` for transaction‑scoped operations and event dispatch. |
| [`docs/infrastructure/exceptions.md`](docs/infrastructure/exceptions.md) | Infrastructure‑layer exceptions: `RepositoryError`, `EntityNotFoundError`, `DuplicateEntityError`, `ConcurrencyError`. |
| [`docs/infrastructure/logging.md`](docs/infrastructure/logging.md) | Custom logger with Rich formatting and tqdm integration for CLI applications. |

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

For more advanced usage (item executions, retries, orchestration), refer to the entity documentation and repository examples.

## Configuration & Setup

### Requirements
- Python 3.11+
- PostgreSQL (for JSONB support; other databases may work with modifications)
- Dependencies: SQLAlchemy, Pydantic, Rich, tqdm, jsonschema, etc. (see `pyproject.toml`)

### Database Setup
1. Create a PostgreSQL database.
2. Set the `DATABASE_URL` environment variable or pass it directly to `DatabaseConfig`.
3. Run database migrations (not included – you may use Alembic or create tables manually). The models are defined in `infrastructure/database/models/`.

Example database URL:
```
postgresql://user:password@localhost/automation_db
```

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | (required) |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | `INFO` |

## Running Tests

The project uses **pytest** with the `pytest-postgresql` plugin to handle test database setup. The test suite expects a running PostgreSQL server with the following credentials (as defined in `conftest.py`):

- Host: `localhost`
- User: `postgres`
- Password: `mysecretpassword`

You can either:
- Run a local PostgreSQL instance with those exact credentials, or
- Modify the `postgresql_proc` fixture in `conftest.py` to match your environment.

### Step-by-step

1. **Install dependencies** (preferably in a virtual environment using Poetry):
   ```bash
   poetry install
   ```

2. **Ensure PostgreSQL is running** and accessible with the credentials above. If you prefer to use different credentials, edit `conftest.py` accordingly.

3. **Run tests** from the project root:
   ```bash
   poetry run pytest
   ```
   Or activate the virtual environment and run `pytest` directly.

   To run with coverage:
   ```bash
   poetry run pytest --cov=project
   ```

4. **Test discovery**: Tests are located in the root directory (e.g., `test_*.py`) and are automatically discovered by pytest.

### Troubleshooting

- **ModuleNotFoundError: No module named 'src'**: Ensure you run tests with the correct Python path. You can either install the package in editable mode (`pip install -e .` or `poetry install`) or set `PYTHONPATH=.` before running pytest.
- **Database connection errors**: Verify that PostgreSQL is running and the credentials match those in `conftest.py`. If you need to change them, update the `postgresql_proc` fixture.

For more details on pytest-postgresql configuration, see the [official documentation](https://pytest-postgresql.readthedocs.io/).

## Contributing

We welcome contributions! Please follow these guidelines:

- Maintain the domain‑driven design principles.
- Update documentation for any changes (especially the `docs/` files).
- Write tests for new functionality.
- Ensure code passes linting (e.g., `ruff`, `mypy`).

## License

[MIT License](LICENSE)