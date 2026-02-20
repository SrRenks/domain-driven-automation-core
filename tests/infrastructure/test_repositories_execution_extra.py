import pytest
from uuid import uuid4

from src.project.domain.entities.definition import Automation, Batch, Item
from src.project.domain.entities.execution import Run, BatchExecution, ItemExecution
from src.project.domain.enums import ExecutionStatus
from src.project.infrastructure.database.repositories.definition import (
    AutomationRepository,
    BatchRepository,
    ItemRepository,
)
from src.project.infrastructure.database.repositories.execution import (
    RunRepository,
    BatchExecutionRepository,
    ItemExecutionRepository,
)


class TestRunRepositoryFilters:
    """Test filter methods of RunRepository."""
    @pytest.fixture
    def setup_runs(self, test_uow, automation):
        """Create multiple runs for testing."""
        repo = RunRepository(test_uow.session, test_uow)
        runs = []
        for i in range(5):
            run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
            run = repo.create(run)
            runs.append(run)
        test_uow.commit()
        return runs

    @pytest.mark.parametrize("status,expected", [(ExecutionStatus.PENDING, 5), (ExecutionStatus.COMPLETED, 0), (None, 5)])
    def test_list_by_automation_status_filter(self, test_uow, automation, setup_runs, status, expected):
        """Test filtering list_by_automation by status."""
        repo = RunRepository(test_uow.session, test_uow)
        runs = repo.list_by_automation(automation.id, status=status)
        assert len(runs) == expected

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_automation_pagination(self, test_uow, automation, limit, offset, expected):
        """Test pagination of list_by_automation."""
        repo = RunRepository(test_uow.session, test_uow)
        for i in range(5):
            run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
            repo.create(run)
        test_uow.commit()
        result = repo.list_by_automation(automation.id, limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_status_with_soft_deleted(self, test_uow, automation):
        """Test list_by_status with include_soft_deleted."""
        repo = RunRepository(test_uow.session, test_uow)
        run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
        run = repo.create(run)
        test_uow.commit()
        repo.delete(run.id, soft=True)
        test_uow.commit()

        assert len(repo.list_by_status(ExecutionStatus.PENDING)) == 0
        assert len(repo.list_by_status(ExecutionStatus.PENDING, include_soft_deleted=True)) == 1


class TestRunRepositoryExtra:
    """Additional tests for RunRepository."""
    @pytest.mark.parametrize("include_soft_deleted,expected", [(False, 2), (True, 3)])
    def test_list_by_automation_include_soft_deleted(self, test_uow, automation, include_soft_deleted, expected):
        """Test include_soft_deleted for list_by_automation."""
        repo = RunRepository(test_uow.session, test_uow)
        for i in range(3):
            run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
            repo.create(run)
        test_uow.commit()
        runs = repo.list()
        repo.delete(runs[0].id, soft=True)
        test_uow.commit()
        result = repo.list_by_automation(automation.id, include_soft_deleted=include_soft_deleted)
        assert len(result) == expected

    def test_find_running_by_automation(self, test_uow, automation):
        """Test find_running filtered by automation_id."""
        repo_run = RunRepository(test_uow.session, test_uow)
        repo_auto = AutomationRepository(test_uow.session, test_uow)

        other_auto = Automation(name="other-auto")
        other_auto = repo_auto.create(other_auto)

        run1 = Run(automation_id=automation.id, status=ExecutionStatus.PROCESSING)
        run1 = repo_run.create(run1)
        run2 = Run(automation_id=automation.id, status=ExecutionStatus.RETRYING)
        run2 = repo_run.create(run2)
        run_other = Run(automation_id=other_auto.id, status=ExecutionStatus.PROCESSING)
        run_other = repo_run.create(run_other)
        test_uow.commit()

        running = repo_run.find_running(automation_id=automation.id)
        assert len(running) == 2
        assert {r.id for r in running} == {run1.id, run2.id}

    @pytest.mark.parametrize("status,include_soft_deleted,expected_count", [
        (ExecutionStatus.PENDING, False, 4),
        (ExecutionStatus.PENDING, True, 5),
        (None, False, 4),
        (None, True, 5),
    ])
    def test_list_by_automation_filter_combinations(
        self, test_uow, automation, status, include_soft_deleted, expected_count
    ):
        """Test combination of status filter and soft-deleted inclusion."""
        repo = RunRepository(test_uow.session, test_uow)
        for i in range(5):
            run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
            repo.create(run)
        runs = repo.list()
        repo.delete(runs[0].id, soft=True)
        test_uow.commit()
        result = repo.list_by_automation(automation.id, status=status, include_soft_deleted=include_soft_deleted)
        assert len(result) == expected_count


class TestBatchExecutionRepositoryExtra:
    """Additional tests for BatchExecutionRepository."""
    @pytest.fixture
    def unique_runs(self, test_uow, automation):
        """Create multiple runs for batch execution tests."""
        repo = RunRepository(test_uow.session, test_uow)
        runs = []
        for i in range(5):
            run = Run(automation_id=automation.id, status=ExecutionStatus.PENDING)
            run = repo.create(run)
            runs.append(run)
        test_uow.commit()
        return runs

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_batch_pagination(self, test_uow, batch, unique_runs, limit, offset, expected):
        """Test pagination of list_by_batch."""
        repo = BatchExecutionRepository(test_uow.session, test_uow)
        for run in unique_runs:
            be = BatchExecution(run_id=run.id, batch_id=batch.id)
            repo.create(be)
        test_uow.commit()
        result = repo.list_by_batch(batch.id, limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_batch_include_soft_deleted(self, test_uow, batch, unique_runs):
        """Test include_soft_deleted for list_by_batch."""
        repo = BatchExecutionRepository(test_uow.session, test_uow)
        be = BatchExecution(run_id=unique_runs[0].id, batch_id=batch.id)
        repo.create(be)
        test_uow.commit()
        repo.delete(be.id, soft=True)
        test_uow.commit()
        assert len(repo.list_by_batch(batch.id)) == 0
        assert len(repo.list_by_batch(batch.id, include_soft_deleted=True)) == 1


class TestItemExecutionRepositoryFilters:
    """Test filter methods of ItemExecutionRepository."""
    def test_list_pending_by_run_with_soft_deleted(self, test_uow, run, batch, batch_execution):
        """Test list_pending_by_run with include_soft_deleted."""
        item_repo = ItemRepository(test_uow.session, test_uow)
        item = Item(batch_id=batch.id, sequence_number=1)
        item = item_repo.create(item)

        ie_repo = ItemExecutionRepository(test_uow.session, test_uow)
        ie = ItemExecution(
            run_id=run.id,
            batch_execution_id=batch_execution.id,
            item_id=item.id,
            status=ExecutionStatus.PENDING,
        )
        ie = ie_repo.create(ie)
        test_uow.commit()

        ie_repo.delete(ie.id, soft=True)
        test_uow.commit()

        assert len(ie_repo.list_pending_by_run(run.id)) == 0
        assert len(ie_repo.list_pending_by_run(run.id, include_soft_deleted=True)) == 1

    def test_list_failed_by_run_pagination(self, test_uow, run, batch_execution, batch):
        """Test pagination of list_failed_by_run."""
        ie_repo = ItemExecutionRepository(test_uow.session, test_uow)
        item_repo = ItemRepository(test_uow.session, test_uow)

        items = []
        for i in range(5):
            item = Item(batch_id=batch.id, sequence_number=i)
            item = item_repo.create(item)
            items.append(item)

        for item in items:
            ie = ItemExecution(
                run_id=run.id,
                batch_execution_id=batch_execution.id,
                item_id=item.id,
                status=ExecutionStatus.FAILED,
            )
            ie_repo.create(ie)
        test_uow.commit()

        assert len(ie_repo.list_failed_by_run(run.id, limit=2)) == 2
        assert len(ie_repo.list_failed_by_run(run.id, offset=2, limit=2)) == 2
        assert len(ie_repo.list_failed_by_run(run.id, offset=10)) == 0

    def test_list_failed_by_run_include_soft_deleted(self, test_uow, run, batch_execution, batch):
        """Test include_soft_deleted for list_failed_by_run."""
        ie_repo = ItemExecutionRepository(test_uow.session, test_uow)
        item_repo = ItemRepository(test_uow.session, test_uow)

        item = Item(batch_id=batch.id, sequence_number=1)
        item = item_repo.create(item)
        ie = ItemExecution(
            run_id=run.id,
            batch_execution_id=batch_execution.id,
            item_id=item.id,
            status=ExecutionStatus.FAILED,
        )
        ie = ie_repo.create(ie)
        test_uow.commit()
        ie_repo.delete(ie.id, soft=True)
        test_uow.commit()

        assert len(ie_repo.list_failed_by_run(run.id)) == 0
        assert len(ie_repo.list_failed_by_run(run.id, include_soft_deleted=True)) == 1

    def test_count_by_status_edge_cases(self, test_uow, run, batch, batch_execution):
        """Test count_by_status with zero and one entity."""
        ie_repo = ItemExecutionRepository(test_uow.session, test_uow)
        item_repo = ItemRepository(test_uow.session, test_uow)

        assert ie_repo.count_by_status(run.id, ExecutionStatus.PENDING) == 0

        item = Item(batch_id=batch.id, sequence_number=1)
        item_repo.create(item)
        ie = ItemExecution(
            run_id=run.id,
            batch_execution_id=batch_execution.id,
            item_id=item.id,
            status=ExecutionStatus.PENDING,
        )
        ie_repo.create(ie)
        test_uow.commit()
        assert ie_repo.count_by_status(run.id, ExecutionStatus.PENDING) == 1
        assert ie_repo.count_by_status(run.id, ExecutionStatus.COMPLETED) == 0

    def test_get_by_run_and_item_not_found(self, test_uow, run):
        """Test get_by_run_and_item returns None for missing combination."""
        repo = ItemExecutionRepository(test_uow.session, test_uow)
        assert repo.get_by_run_and_item(run.id, uuid4()) is None


class TestItemExecutionRepositoryExtra:
    """Additional tests for ItemExecutionRepository."""
    @pytest.fixture
    def unique_items(self, test_uow, batch):
        """Create multiple items for testing."""
        repo = ItemRepository(test_uow.session, test_uow)
        items = []
        for i in range(5):
            item = Item(batch_id=batch.id, sequence_number=i)
            item = repo.create(item)
            items.append(item)
        test_uow.commit()
        return items

    @pytest.fixture
    def item_execution_setup(self, test_uow):
        """Create a full setup (automation, batch, run, batch_execution) for item execution tests."""
        repo_auto = AutomationRepository(test_uow.session, test_uow)
        repo_batch = BatchRepository(test_uow.session, test_uow)
        repo_run = RunRepository(test_uow.session, test_uow)
        repo_be = BatchExecutionRepository(test_uow.session, test_uow)

        auto = Automation(name="setup-auto")
        auto = repo_auto.create(auto)
        batch = Batch(automation_id=auto.id, name="setup-batch")
        batch = repo_batch.create(batch)
        run = Run(automation_id=auto.id)
        run = repo_run.create(run)
        be = BatchExecution(run_id=run.id, batch_id=batch.id)
        be = repo_be.create(be)
        test_uow.commit()

        return {"run": run, "batch_execution": be, "batch": batch, "automation": auto}

    def test_list_by_batch_execution_pagination(self, test_uow, run, batch_execution, unique_items):
        """Test pagination of list_by_batch_execution."""
        repo = ItemExecutionRepository(test_uow.session, test_uow)
        for item in unique_items:
            ie = ItemExecution(run_id=run.id, batch_execution_id=batch_execution.id, item_id=item.id)
            repo.create(ie)
        test_uow.commit()
        assert len(repo.list_by_batch_execution(batch_execution.id, limit=2)) == 2
        assert len(repo.list_by_batch_execution(batch_execution.id, offset=10)) == 0

    def test_list_by_batch_execution_include_soft_deleted(self, test_uow, run, batch_execution, unique_items):
        """Test include_soft_deleted for list_by_batch_execution."""
        repo = ItemExecutionRepository(test_uow.session, test_uow)
        ie = ItemExecution(run_id=run.id, batch_execution_id=batch_execution.id, item_id=unique_items[0].id)
        repo.create(ie)
        test_uow.commit()
        repo.delete(ie.id, soft=True)
        test_uow.commit()
        assert len(repo.list_by_batch_execution(batch_execution.id)) == 0
        assert len(repo.list_by_batch_execution(batch_execution.id, include_soft_deleted=True)) == 1

    def test_list_pending_by_run_pagination(self, test_uow, run, batch_execution, unique_items):
        """Test pagination of list_pending_by_run."""
        repo = ItemExecutionRepository(test_uow.session, test_uow)
        for item in unique_items:
            ie = ItemExecution(
                run_id=run.id,
                batch_execution_id=batch_execution.id,
                item_id=item.id,
                status=ExecutionStatus.PENDING,
            )
            repo.create(ie)
        test_uow.commit()
        assert len(repo.list_pending_by_run(run.id, limit=2)) == 2
        assert len(repo.list_pending_by_run(run.id, offset=10)) == 0