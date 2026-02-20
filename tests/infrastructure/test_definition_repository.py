import pytest

from src.project.domain.entities.definition import Automation
from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.infrastructure.exceptions.repository import DuplicateEntityError


class TestAutomationRepository:
    def test_create_automation(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        automation = Automation(name="test-auto")
        created = repo.create(automation)
        test_uow.commit()

        found = repo.get(created.id)
        assert found is not None
        assert found.name == "test-auto"
        assert found.id is not None

    def test_get_by_name(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        automation = Automation(name="unique-name")
        created = repo.create(automation)
        test_uow.commit()

        found = repo.get_by_name("unique-name")
        assert found is not None
        assert found.id == created.id

    def test_get_by_name_not_found(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        assert repo.get_by_name("non-existent") is None

    def test_update_automation(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        automation = Automation(name="old")
        created = repo.create(automation)
        test_uow.commit()
        original_version = created.version

        created.name = "new"
        repo.update(created.id, created)
        test_uow.commit()

        updated = repo.get(created.id)
        assert updated.name == "new"
        assert updated.version == original_version + 1

    def test_delete_automation(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        automation = Automation(name="to-delete")
        created = repo.create(automation)
        test_uow.commit()

        repo.delete(created.id)
        test_uow.commit()

        assert repo.get(created.id) is None

    def test_duplicate_name_raises_duplicate_error(self, test_uow):
        repo = AutomationRepository(test_uow.session, test_uow)
        a1 = Automation(name="dup")
        repo.create(a1)
        test_uow.commit()

        a2 = Automation(name="dup")
        with pytest.raises(DuplicateEntityError):
            repo.create(a2)
        test_uow.rollback()