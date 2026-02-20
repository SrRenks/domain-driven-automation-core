import pytest

from src.project.infrastructure.uow import UnitOfWork, EventBus
from src.project.domain.entities import Automation, Run
from src.project.domain.events import RunCompleted


@pytest.fixture
def event_bus():
    """Provide an EventBus instance for testing."""
    return EventBus()


def test_identity_map_same_entity(db_config, event_bus):
    """Test that the UnitOfWork identity map returns the same instance for repeated gets."""
    uow = UnitOfWork(db_config, event_bus)
    with uow:
        auto = Automation(name="same")
        uow.automations.create(auto)
        auto2 = uow.automations.get(auto.id)
        assert auto2 is auto


def test_events_dispatched_only_on_commit(db_config):
    """Test that events are collected but not dispatched until commit."""
    collected = []

    def handler(event):
        collected.append(event)

    event_bus = EventBus()
    event_bus.register(RunCompleted, handler)

    uow = UnitOfWork(db_config, event_bus)
    with uow:
        auto = Automation(name="event-test")
        uow.automations.create(auto)
        run = Run(automation_id=auto.id)
        uow.runs.create(run)
        run.start()
        run.complete()
        assert len(collected) == 0

    assert len(collected) == 1
    assert isinstance(collected[0], RunCompleted)


def test_events_not_dispatched_on_rollback(db_config):
    """Test that events are discarded on rollback and not dispatched."""
    collected = []

    def handler(event):
        collected.append(event)

    event_bus = EventBus()
    event_bus.register(RunCompleted, handler)

    uow = UnitOfWork(db_config, event_bus)
    with pytest.raises(ValueError):
        with uow:
            auto = Automation(name="rollback")
            uow.automations.create(auto)
            run = Run(automation_id=auto.id)
            uow.runs.create(run)
            run.start()
            run.complete()
            raise ValueError("force rollback")
    assert len(collected) == 0


def test_transaction_context_manager(db_config, event_bus):
    """Test that transaction() context manager commits on success."""
    uow = UnitOfWork(db_config, event_bus)
    with uow:
        with uow.transaction():
            auto = Automation(name="tx")
            uow.automations.create(auto)

    with UnitOfWork(db_config, event_bus) as uow2:
        fetched = uow2.automations.get_by_name("tx")
        assert fetched is not None


def test_transaction_rollback_on_exception(db_config, event_bus):
    """Test that transaction() rolls back on exception."""
    uow = UnitOfWork(db_config, event_bus)
    with uow:
        with pytest.raises(RuntimeError):
            with uow.transaction():
                auto = Automation(name="tx-rollback")
                uow.automations.create(auto)
                raise RuntimeError("boom")
    with UnitOfWork(db_config, event_bus) as uow2:
        fetched = uow2.automations.get_by_name("tx-rollback")
        assert fetched is None