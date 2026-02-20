import pytest

from src.project.domain.entities.definition import Automation, Batch
from src.project.domain.entities.execution import Run, BatchExecution
from src.project.domain.enums import ExecutionStatus
from src.project.infrastructure.database.repositories.definition import AutomationRepository, BatchRepository
from src.project.infrastructure.database.repositories.execution import RunRepository, BatchExecutionRepository


class TestRunRepository:
    def test_get_by_correlation_id(self, test_uow, run):
        repo = RunRepository(test_uow.session, test_uow)
        found = repo.get_by_correlation_id(run.correlation_id)
        assert found is not None
        assert found.id == run.id

    def test_get_by_correlation_id_not_found(self, test_uow):
        repo = RunRepository(test_uow.session, test_uow)
        assert repo.get_by_correlation_id("missing") is None

    def test_list_by_status(self, test_uow, run):
        repo = RunRepository(test_uow.session, test_uow)
        runs = repo.list_by_status(ExecutionStatus.PENDING)
        assert len(runs) >= 1
        assert any(r.id == run.id for r in runs)

    def test_list_by_automation(self, test_uow, run, automation):
        repo = RunRepository(test_uow.session, test_uow)
        runs = repo.list_by_automation(automation.id)
        assert len(runs) == 1
        assert runs[0].id == run.id

    def test_update_run_status(self, test_uow, run):
        repo = RunRepository(test_uow.session, test_uow)
        run = repo.get(run.id)
        original_version = run.version
        run.status = ExecutionStatus.COMPLETED
        repo.update(run.id, run)
        test_uow.commit()

        updated = repo.get(run.id)
        assert updated.status == ExecutionStatus.COMPLETED
        assert updated.version == original_version + 1

    def test_delete_run(self, test_uow, run):
        repo = RunRepository(test_uow.session, test_uow)
        repo.delete(run.id)
        test_uow.commit()
        assert repo.get(run.id) is None


class TestBatchExecutionRepository:
    def test_get_by_run_and_batch(self, test_uow, batch_execution, run, batch):
        repo = BatchExecutionRepository(test_uow.session, test_uow)
        found = repo.get_by_run_and_batch(run.id, batch.id)
        assert found is not None
        assert found.id == batch_execution.id

    def test_list_by_run(self, test_uow, batch_execution, run):
        repo = BatchExecutionRepository(test_uow.session, test_uow)
        results = repo.list_by_run(run.id)
        assert len(results) == 1
        assert results[0].id == batch_execution.id

    def test_update_batch_execution_status(self, test_uow, batch_execution):
        repo = BatchExecutionRepository(test_uow.session, test_uow)
        be = repo.get(batch_execution.id)
        original_version = be.version
        be.status = ExecutionStatus.COMPLETED
        repo.update(be.id, be)
        test_uow.commit()

        updated = repo.get(be.id)
        assert updated.status == ExecutionStatus.COMPLETED
        assert updated.version == original_version + 1