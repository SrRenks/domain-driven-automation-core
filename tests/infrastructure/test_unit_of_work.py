import pytest

from src.project.infrastructure.uow import UnitOfWork, EventBus
from src.project.domain.entities import Automation, Run
from src.project.domain.events import RunCompleted


@pytest.fixture
def event_bus():
    """Provide an EventBus instance for testing."""
    return EventBus()


def test_uow_commit(db_config, event_bus):
    """Test that UnitOfWork commits changes when exiting context successfully."""
    uow = UnitOfWork(db_config, event_bus)
    with uow:
        auto = Automation(name="test")
        uow.automations.create(auto)

    with UnitOfWork(db_config, event_bus) as uow2:
        fetched = uow2.automations.get_by_name("test")
        assert fetched is not None


def test_uow_rollback_on_exception(db_config, event_bus):
    """Test that UnitOfWork rolls back changes when an exception occurs."""
    uow = UnitOfWork(db_config, event_bus)
    with pytest.raises(ValueError):
        with uow:
            auto = Automation(name="test")
            uow.automations.create(auto)
            raise ValueError("force rollback")

    with UnitOfWork(db_config, event_bus) as uow2:
        fetched = uow2.automations.get_by_name("test")
        assert fetched is None


def test_event_collection_and_dispatch(db_config):
    """Test that events are collected and dispatched on commit."""
    collected = []

    def handler(event):
        collected.append(event)

    event_bus = EventBus()
    event_bus.register(RunCompleted, handler)

    uow = UnitOfWork(db_config, event_bus)
    with uow:
        auto = Automation(name="test")
        uow.automations.create(auto)
        run = Run(automation_id=auto.id)
        uow.runs.create(run)
        run.start()
        run.complete()
    assert len(collected) == 1
    assert isinstance(collected[0], RunCompleted)