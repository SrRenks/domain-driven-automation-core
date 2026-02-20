## Event Bus

### [EventBus]
**Definition**: Simple in‑memory event dispatcher that allows registering handlers for domain events and dispatching them after a successful transaction commit.

**Purpose**: Decouple domain logic from side effects (e.g., sending emails, updating caches) by collecting events during the unit of work and dispatching them only after the database transaction is committed.

**Key characteristics**:
- **Handlers dictionary**: Maps event types to lists of callable handlers.
- **register(event_type, handler)**: Adds a handler for a specific event class.
- **dispatch(events)**: Iterates over a list of domain events and calls each registered handler for the event’s type.
- **Asynchronous option**: If `use_async=True` is passed to the constructor, handlers are executed in a `ThreadPoolExecutor` (max_workers configurable), preventing slow handlers from blocking the commit thread.
- **Executor lifecycle**: The thread pool is created at initialization. A `shutdown(wait=True)` method should be called on application exit to gracefully shut down the executor and optionally wait for pending tasks.

**Relationships / Rules**:
- Used exclusively by `UnitOfWork` to dispatch events after commit.
- Events are collected from entities via `pop_events()`.

**Examples**:
```python
event_bus = EventBus(use_async=True)
event_bus.register(RunCompleted, send_notification_handler)

uow = UnitOfWork(db_config, event_bus)
with uow.transaction():
    run.complete()   # registers RunCompleted event
# After commit, handler is executed asynchronously
# On application exit
event_bus.shutdown(wait=True)
```

## Unit of Work

### [UnitOfWork]
**Definition**: Context manager that coordinates database transactions and provides access to all repositories. It also maintains an identity map and tracks entities to collect domain events.

**Purpose**: Ensure atomic operations across multiple repositories; manage session lifecycle, commit/rollback, identity map, and event dispatch.

**Key characteristics**:
- Initialized with a `DatabaseConfig` and an `EventBus`.
- On `__enter__`, creates a new SQLAlchemy session and initializes all repositories.
- Repositories are exposed as attributes (`uow.automations`, `uow.runs`, etc.).
- **Identity map**:
  - `_identity_map`: dict mapping entity classes to dicts of ID → entity instance.
  - `register_entity(entity, entity_id=None)`: adds an entity to the identity map.
  - `unregister_entity(entity_class, entity_id)`: removes an entity.
  - `has_entity(entity_class, entity_id)`, `get_entity(entity_class, entity_id)`: query methods.
- **Entity tracking**:
  - `_tracked_entities`: dict of (class, id) → entity, used to collect events.
  - `register_entity` also adds to tracked entities.
  - `unregister_entity` removes from both.
- **commit()**: After a successful database commit, collects events from all tracked entities via `_collect_events()`, clears the identity map, and dispatches events via the event bus.
- **rollback()**: Rolls back the transaction, clears the identity map and tracked entities, **and resets all repository attributes to `None`** to ensure no stale state is kept if the same UoW instance is reused.
- **close()**: Closes the session.
- **transaction()**: Context manager that yields the UoW and commits on success, rolls back on exception.
- **is_active()**: Checks if session exists.

**Relationships / Rules**:
- Only one session per UoW instance.
- Repositories share the same session and are given a reference to the UoW to access the identity map.
- The identity map ensures that within a single UoW, the same database row is represented by a single entity instance.
- Events are dispatched only after a successful commit.

**Examples**:
```python
with UnitOfWork(db_config, event_bus) as uow:
    automation = uow.automations.create(new_automation)
    batch = uow.batches.create(new_batch)
    uow.commit()

# Or using transaction context:
with uow.transaction():
    uow.automations.create(automation)
    uow.batches.create(batch)
```