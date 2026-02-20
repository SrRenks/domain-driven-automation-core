import time
from unittest.mock import Mock, call
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.project.domain.entities.definition import Automation
from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.infrastructure.exceptions.repository import DuplicateEntityError
from src.project.infrastructure.uow.unit_of_work import UnitOfWork, EventBus


def test_async_event_dispatch():
    """Test that events are dispatched asynchronously to registered handlers."""
    bus = EventBus(use_async=True, max_workers=2)
    mock_handler = Mock()
    test_event_type = type("TestEvent", (), {})
    bus.register(test_event_type, mock_handler)

    events = [test_event_type() for _ in range(5)]
    bus.dispatch(events)
    bus.shutdown(wait=True)

    assert mock_handler.call_count == 5
    mock_handler.assert_has_calls([call(event) for event in events], any_order=True)


def test_async_dispatch_with_exception():
    """Test that exceptions in async handlers are captured but not raised."""
    bus = EventBus(use_async=True, max_workers=2)

    def failing_handler(event):
        raise ValueError("handler error")

    test_event_type = type("TestEvent", (), {})
    bus.register(test_event_type, failing_handler)

    events = [test_event_type() for _ in range(3)]
    bus.dispatch(events)
    bus.shutdown(wait=True)


def test_async_shutdown_wait_false():
    """Test shutdown with wait=False does not block and cancels pending futures."""
    bus = EventBus(use_async=True, max_workers=2)

    def slow_handler(event):
        time.sleep(1)

    test_event_type = type("TestEvent", (), {})
    bus.register(test_event_type, slow_handler)

    events = [test_event_type() for _ in range(3)]
    bus.dispatch(events)
    bus.shutdown(wait=False)


def test_async_multiple_handlers_per_event():
    """Test that multiple handlers for the same event type are all called."""
    bus = EventBus(use_async=True, max_workers=2)
    mock1 = Mock()
    mock2 = Mock()
    test_event_type = type("TestEvent", (), {})
    bus.register(test_event_type, mock1)
    bus.register(test_event_type, mock2)

    event = test_event_type()
    bus.dispatch([event])
    bus.shutdown(wait=True)

    mock1.assert_called_once_with(event)
    mock2.assert_called_once_with(event)


def test_sync_event_dispatch():
    """Test that events are dispatched synchronously."""
    bus = EventBus(use_async=False)
    mock_handler = Mock()
    test_event_type = type("TestEvent", (), {})
    bus.register(test_event_type, mock_handler)

    events = [test_event_type() for _ in range(3)]
    bus.dispatch(events)

    assert mock_handler.call_count == 3

class MockEventBus:
    """Mock EventBus that records dispatched events."""
    def __init__(self):
        self.dispatched = None

    def dispatch(self, events):
        self.dispatched = events


def test_commit_after_rollback_does_not_raise(db_config):
    """Test that calling commit after rollback does not raise an exception."""
    event_bus = MockEventBus()
    uow = UnitOfWork(db_config, event_bus)
    uow.__enter__()
    uow.rollback()
    try:
        uow.commit()
    except Exception as e:
        pytest.fail(f"commit after rollback raised: {e}")
    uow.__exit__(None, None, None)


def test_flush_after_rollback(db_config):
    """Test that flushing after rollback works (or is a no-op)."""
    event_bus = MockEventBus()
    uow = UnitOfWork(db_config, event_bus)
    uow.__enter__()
    repo = AutomationRepository(uow.session, uow)
    auto = Automation(name="test")
    repo.create(auto)
    uow.session.flush()
    uow.rollback()
    uow.session.flush()
    uow.__exit__(None, None, None)


def test_rollback_after_failed_commit(test_uow, engine):
    """Test that rollback after a failed commit restores consistency."""
    repo = AutomationRepository(test_uow.session, test_uow)
    auto = Automation(name="test")
    repo.create(auto)
    test_uow.commit()

    auto2 = Automation(name="test")
    with pytest.raises(DuplicateEntityError):
        repo.create(auto2)
    test_uow.rollback()

    new_session = Session(bind=engine)
    new_repo = AutomationRepository(new_session, test_uow)
    assert new_repo.count() == 1
    new_session.close()


def test_flush(test_uow, engine):
    """Test that flush assigns an ID but changes can be rolled back."""
    repo = AutomationRepository(test_uow.session, test_uow)
    auto = Automation(name="test")
    created = repo.create(auto)
    test_uow.flush()
    assert created.id is not None

    test_uow.rollback()
    test_uow.session.close()

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM automation WHERE id = :id"), {"id": created.id}
        ).first()
        assert result is None


def test_uow_context_manager_commits_on_success(db_config):
    """Test that the context manager commits on successful exit."""
    class MockEventBus:
        def dispatch(self, events):
            pass

    event_bus = MockEventBus()
    with UnitOfWork(db_config, event_bus) as uow:
        repo = AutomationRepository(uow.session, uow)
        auto = Automation(name="context-test")
        repo.create(auto)

    with db_config.engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM automation WHERE name = 'context-test'")
        ).first()
        assert result is not None


def test_uow_context_manager_rolls_back_on_error(db_config):
    """Test that the context manager rolls back on exception."""
    event_bus = MockEventBus()
    with pytest.raises(ValueError):
        with UnitOfWork(db_config, event_bus) as uow:
            repo = AutomationRepository(uow.session, uow)
            auto = Automation(name="rollback-test")
            repo.create(auto)
            raise ValueError("simulate error")

    with db_config.engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM automation WHERE name = 'rollback-test'")
        ).first()
        assert result is None


def test_has_entity_for_nonexistent(test_uow):
    """Test has_entity returns False for an ID not in the identity map."""
    assert test_uow.has_entity(Automation, uuid4()) is False


def test_get_entity_for_nonexistent(test_uow):
    """Test get_entity returns None for an ID not in the identity map."""
    assert test_uow.get_entity(Automation, uuid4()) is None
