import pytest

from src.project.infrastructure.uow import UnitOfWork, EventBus
from src.project.domain.entities import Automation
from src.project.infrastructure.exceptions.repository import ConcurrencyError


def test_update_with_stale_version(db_config):
    """Test that updating an entity with a stale version raises ConcurrencyError."""
    event_bus = EventBus()
    uow_create = UnitOfWork(db_config, event_bus)
    with uow_create:
        auto = Automation(name="test")
        uow_create.automations.create(auto)
        auto_id = auto.id

    uow1 = UnitOfWork(db_config, event_bus)
    uow1.__enter__()
    auto1 = uow1.automations.get(auto_id)
    auto1.name = "updated by other"
    uow1.automations.update(auto1.id, auto1)

    uow2 = UnitOfWork(db_config, event_bus)
    uow2.__enter__()
    auto2 = uow2.automations.get(auto_id)
    auto2.name = "my update"

    uow1.commit()

    with pytest.raises(ConcurrencyError):
        uow2.automations.update(auto2.id, auto2)
        uow2.commit()
    uow2.__exit__(None, None, None)


def test_soft_delete_with_stale_version(db_config):
    """Test that soft-deleting an entity with a stale version raises ConcurrencyError."""
    event_bus = EventBus()
    uow_create = UnitOfWork(db_config, event_bus)
    with uow_create:
        auto = Automation(name="soft-del")
        uow_create.automations.create(auto)
        auto_id = auto.id

    uow1 = UnitOfWork(db_config, event_bus)
    uow1.__enter__()
    auto1 = uow1.automations.get(auto_id)
    auto1.name = "changed"
    uow1.automations.update(auto1.id, auto1)

    uow2 = UnitOfWork(db_config, event_bus)
    uow2.__enter__()
    auto2 = uow2.automations.get(auto_id)

    uow1.commit()

    with pytest.raises(ConcurrencyError):
        uow2.automations.delete(auto_id, soft=True)
    uow2.__exit__(None, None, None)


def test_hard_delete_with_stale_version(db_config):
    """Test that hard-deleting an entity with a stale version raises ConcurrencyError."""
    event_bus = EventBus()
    uow_create = UnitOfWork(db_config, event_bus)
    with uow_create:
        auto = Automation(name="hard-del")
        uow_create.automations.create(auto)
        auto_id = auto.id

    uow1 = UnitOfWork(db_config, event_bus)
    uow1.__enter__()
    auto1 = uow1.automations.get(auto_id)
    auto1.name = "changed"
    uow1.automations.update(auto1.id, auto1)

    uow2 = UnitOfWork(db_config, event_bus)
    uow2.__enter__()
    auto2 = uow2.automations.get(auto_id)

    uow1.commit()

    with pytest.raises(ConcurrencyError):
        uow2.automations.delete(auto_id, soft=False)
    uow2.__exit__(None, None, None)