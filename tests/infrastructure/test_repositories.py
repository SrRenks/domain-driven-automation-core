import pytest

from src.project.infrastructure.database.repositories.definition import AutomationRepository
from src.project.infrastructure.database.repositories.execution import RunRepository
from src.project.domain.entities import Automation, Run
from src.project.domain.enums import ExecutionStatus


class TestAutomationRepository:
    def test_create_automation(self, db_session, uow_mock):
        repo = AutomationRepository(db_session, uow_mock)
        auto = Automation(name="test-auto", description="desc")
        created = repo.create(auto, user="tester")
        assert created.id is not None
        assert created.created_by == "tester"
        assert created.version == 1

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.name == "test-auto"

    def test_get_by_name(self, db_session, uow_mock):
        repo = AutomationRepository(db_session, uow_mock)
        auto = Automation(name="unique-name")
        repo.create(auto)
        found = repo.get_by_name("unique-name")
        assert found is not None
        assert found.name == "unique-name"
        not_found = repo.get_by_name("nonexistent")
        assert not_found is None

    def test_update_automation(self, db_session, uow_mock):
        repo = AutomationRepository(db_session, uow_mock)
        auto = Automation(name="old")
        created = repo.create(auto)
        original_version = created.version
        created.name = "new"
        updated = repo.update(created.id, created, user="updater")
        assert updated.name == "new"
        assert updated.updated_by == "updater"
        assert updated.version == original_version + 1

    def test_delete_soft(self, db_session, uow_mock):
        repo = AutomationRepository(db_session, uow_mock)
        auto = Automation(name="to-delete")
        created = repo.create(auto)
        deleted = repo.delete(created.id, soft=True)
        assert deleted is True
        assert repo.get(created.id) is None

        soft = repo.get(created.id, include_soft_deleted=True)
        assert soft is not None
        assert soft.is_active is False


class TestRunRepository:
    def test_find_running(self, db_session, uow_mock, automation):
        auto_repo = AutomationRepository(db_session, uow_mock)
        auto1 = automation
        auto2 = Automation(name="test-auto-2")
        auto2 = auto_repo.create(auto2)

        repo = RunRepository(db_session, uow_mock)
        run1 = Run(automation_id=auto1.id)
        run1.start()
        run2 = Run(automation_id=auto1.id)
        run2.status = ExecutionStatus.COMPLETED
        run3 = Run(automation_id=auto2.id)
        run3.start()

        repo.create(run1)
        repo.create(run2)
        repo.create(run3)

        running = repo.find_running()
        assert len(running) == 2
        assert {r.id for r in running} == {run1.id, run3.id}

        running_for_auto = repo.find_running(automation_id=auto1.id)
        assert len(running_for_auto) == 1
        assert running_for_auto[0].id == run1.id