from contextlib import contextmanager
from typing import Generator, Optional, List, Tuple, Callable, Dict, Type, Any
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from ..database.database import DatabaseConfig
from ..database.repositories.definition import (
    AutomationRepository, BatchRepository, ItemRepository
)
from ..database.repositories.execution import (
    RunRepository, BatchExecutionRepository,
    ItemExecutionRepository, ItemStateHistoryRepository
)
from ..database.repositories.orchestration import (
    EngineRepository, OrchestrationInstanceRepository, RunOrchestrationRepository
)

from ...domain.base import DomainEntity
from ...domain.events import DomainEvent
from ...utils.logger import setup_logger

logger = setup_logger(__name__)


class EventBus:
    """Simple in‑memory event dispatcher.

    Allows registering handlers for domain events and dispatching events after
    a successful transaction commit. Supports synchronous or asynchronous
    (thread‑pool) execution of handlers.

    Attributes:
        handlers (Dict[type, List[Callable]]): Registered handlers per event type.
        use_async (bool): Whether to dispatch asynchronously.
        executor (Optional[ThreadPoolExecutor]): Executor for async dispatch.
        _futures (List): List of pending futures when using async.
    """
    def __init__(self, use_async: bool = False, max_workers: int = 4):
        """Initialize the event bus.

        Args:
            use_async (bool): If True, dispatch handlers in a thread pool.
            max_workers (int): Maximum number of worker threads for async dispatch.
        """
        self.handlers: Dict[type, List[Callable]] = {}
        self.use_async = use_async
        if use_async:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            self._futures = []

    def register(self, event_type: type, handler: Callable) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type (type): The event class (e.g., RunCompleted).
            handler (Callable): The handler function/callable.
        """
        self.handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, events: List[DomainEvent]):
        """Dispatch a list of events to their registered handlers.

        If async mode is enabled, handlers are submitted to the thread pool.
        Otherwise, they are executed synchronously.

        Args:
            events (List[DomainEvent]): The events to dispatch.
        """
        if not self.use_async:
            for event in events:
                for handler in self.handlers.get(type(event), []):
                    handler(event)
        else:
            for event in events:
                for handler in self.handlers.get(type(event), []):
                    future = self.executor.submit(handler, event)
                    self._futures.append(future)

    def shutdown(self, wait: bool = True):
        """Shut down the executor, optionally waiting for pending tasks.

        Args:
            wait (bool): If True, wait for pending futures to complete.
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=wait)
            if not wait:
                for f in self._futures:
                    f.cancel()

            self._futures.clear()

class UnitOfWork:
    """Unit of Work context manager coordinating database transactions.

    Provides access to all repositories and manages session lifecycle,
    identity map, and event dispatch.

    Attributes:
        db_config (DatabaseConfig): Database configuration.
        event_bus (EventBus): Event bus for dispatching domain events.
        session (Optional[Session]): SQLAlchemy session (set on enter).
        automations (Optional[AutomationRepository]): Automation repository.
        batches (Optional[BatchRepository]): Batch repository.
        items (Optional[ItemRepository]): Item repository.
        runs (Optional[RunRepository]): Run repository.
        batch_executions (Optional[BatchExecutionRepository]): Batch execution repository.
        item_executions (Optional[ItemExecutionRepository]): Item execution repository.
        item_state_history (Optional[ItemStateHistoryRepository]): Item state history repository.
        engines (Optional[EngineRepository]): Engine repository.
        orchestration_instances (Optional[OrchestrationInstanceRepository]): Orchestration instance repository.
        run_orchestration (Optional[RunOrchestrationRepository]): Run orchestration repository.
        _identity_map (Dict[Type, Dict[UUID, Any]]): Identity map of loaded entities.
        _tracked_entities (Dict[Tuple[Type, UUID], DomainEntity]): Tracked entities for event collection.
    """
    def __init__(self, db_config: DatabaseConfig, event_bus: EventBus):
        self.db_config = db_config
        self.event_bus = event_bus
        self._tracked_entities: Dict[Tuple[Type, UUID], DomainEntity] = {}
        self.automations: Optional[AutomationRepository] = None
        self.batches: Optional[BatchRepository] = None
        self.items: Optional[ItemRepository] = None
        self.runs: Optional[RunRepository] = None
        self.batch_executions: Optional[BatchExecutionRepository] = None
        self.item_executions: Optional[ItemExecutionRepository] = None
        self.item_state_history: Optional[ItemStateHistoryRepository] = None
        self.engines: Optional[EngineRepository] = None
        self.orchestration_instances: Optional[OrchestrationInstanceRepository] = None
        self.run_orchestration: Optional[RunOrchestrationRepository] = None
        self._identity_map: Dict[Type, Dict[UUID, Any]] = {}

    def __enter__(self):
        """Enter context manager: create session and initialize repositories.

        Returns:
            UnitOfWork: The instance itself.
        """
        self.session = self.db_config.SessionLocal()
        self._init_repositories()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager: commit if no exception, else rollback, then close."""
        try:
            if exc_type is None:
                self.commit()
            else:
                logger.error("Exception in UOW context, rolling back",
                            exc_info=(exc_type, exc_val, exc_tb))
                self.rollback()
        finally:
            self.close()

    def register_entity(self, entity: Any, entity_id: Optional[UUID] = None) -> None:
        """Register an entity for identity map and event tracking.

        Args:
            entity (Any): The entity instance.
            entity_id (Optional[UUID]): ID of the entity (defaults to entity.id).
        """
        if entity_id is None:
            entity_id = entity.id
        entity_class = type(entity)
        key = (entity_class, entity_id)

        if entity_class not in self._identity_map:
            self._identity_map[entity_class] = {}
        self._identity_map[entity_class][entity_id] = entity

        self._tracked_entities[key] = entity

    def unregister_entity(self, entity_class: Type, entity_id: UUID) -> None:
        """Remove an entity from the identity map and event tracking.

        Args:
            entity_class (Type): The class of the entity.
            entity_id (UUID): The entity ID.
        """
        if entity_class in self._identity_map:
            self._identity_map[entity_class].pop(entity_id, None)

        key = (entity_class, entity_id)
        self._tracked_entities.pop(key, None)

    def _collect_events(self) -> List[DomainEvent]:
        """Collect and clear events from all tracked entities.

        Returns:
            List[DomainEvent]: All events collected.
        """
        events = []
        for entity in self._tracked_entities.values():
            if hasattr(entity, 'pop_events'):
                events.extend(entity.pop_events())
        self._tracked_entities.clear()
        return events

    def _init_repositories(self):
        """Initialize all repositories with the current session."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        self.automations = AutomationRepository(self.session, self)
        self.batches = BatchRepository(self.session, self)
        self.items = ItemRepository(self.session, self)

        self.runs = RunRepository(self.session, self)
        self.batch_executions = BatchExecutionRepository(self.session, self)
        self.item_executions = ItemExecutionRepository(self.session, self)
        self.item_state_history = ItemStateHistoryRepository(self.session, self)

        self.engines = EngineRepository(self.session, self)
        self.orchestration_instances = OrchestrationInstanceRepository(self.session, self)
        self.run_orchestration = RunOrchestrationRepository(self.session, self)

    def commit(self):
        """Commit the current transaction and dispatch events.

        Raises:
            RuntimeError: If session not initialized.
            Exception: Any database error during commit.
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        try:
            self.session.commit()
        except Exception:
            self.rollback()
            raise
        else:
            events = self._collect_events()
            if events:
                self.event_bus.dispatch(events)
        finally:
            self.clear_identity_map()

    def rollback(self):
        """Rollback the current transaction and clear identity map."""
        if self.session:
            self.session.rollback()
        self.clear_identity_map()
        self._tracked_entities.clear()
        self.automations = None
        self.batches = None
        self.items = None
        self.runs = None
        self.batch_executions = None
        self.item_executions = None
        self.item_state_history = None
        self.engines = None
        self.orchestration_instances = None
        self.run_orchestration = None

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
            self.session = None

    @contextmanager
    def transaction(self) -> Generator['UnitOfWork', None, None]:
        """Context manager for atomic transactions.

        Usage:
            with uow.transaction():
                uow.automations.create(automation)

        Yields:
            UnitOfWork: The instance itself.

        Raises:
            Exception: Any exception inside the block triggers rollback.
        """
        try:
            yield self
            self.commit()
        except Exception as e:
            self.rollback()
            raise

    def is_active(self) -> bool:
        """Check if unit of work has an active session.

        Returns:
            bool: True if session exists and is not closed.
        """
        return self.session is not None

    def has_entity(self, entity_class: Type, entity_id: UUID) -> bool:
        """Check if an entity of given class and ID is already tracked.

        Args:
            entity_class (Type): The class of the entity.
            entity_id (UUID): The entity ID.

        Returns:
            bool: True if tracked.
        """
        return entity_id in self._identity_map.get(entity_class, {})

    def get_entity(self, entity_class: Type, entity_id: UUID) -> Optional[Any]:
        """Retrieve tracked entity from identity map.

        Args:
            entity_class (Type): The class of the entity.
            entity_id (UUID): The entity ID.

        Returns:
            Optional[Any]: The tracked entity, or None if not found.
        """
        return self._identity_map.get(entity_class, {}).get(entity_id)

    def clear_identity_map(self) -> None:
        """Clear the identity map and tracked entities (used at transaction end)."""
        self._identity_map.clear()
        self._tracked_entities.clear()
