import pytest

from src.project.domain.entities.orchestration import Engine, OrchestrationInstance
from src.project.domain.enums import ExecutionStatus
from src.project.infrastructure.database.repositories.orchestration import (
    EngineRepository,
    OrchestrationInstanceRepository,
)


class TestEngineRepositoryExtra:
    """Additional tests for EngineRepository."""
    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_type_pagination(self, test_uow, limit, offset, expected):
        """Test pagination of list_by_type."""
        repo = EngineRepository(test_uow.session, test_uow)
        for i in range(5):
            engine = Engine(name=f"engine{i}", type="docker")
            repo.create(engine)
        test_uow.commit()
        result = repo.list_by_type("docker", limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_type_include_soft_deleted(self, test_uow):
        """Test include_soft_deleted for list_by_type."""
        repo = EngineRepository(test_uow.session, test_uow)
        engine = Engine(name="engine1", type="docker")
        repo.create(engine)
        test_uow.commit()
        repo.delete(engine.id, soft=True)
        test_uow.commit()
        assert len(repo.list_by_type("docker")) == 0
        assert len(repo.list_by_type("docker", include_soft_deleted=True)) == 1


class TestOrchestrationInstanceRepositoryFilters:
    """Test filter methods of OrchestrationInstanceRepository."""
    @pytest.fixture
    def setup_instances(self, test_uow, engine_entity):
        """Create multiple instances for pagination tests."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        instances = []
        for i in range(5):
            inst = OrchestrationInstance(
                engine_id=engine_entity.id,
                external_id=f"ext{i}",
                status=ExecutionStatus.PENDING,
                instance_metadata={},
                duration_seconds=0,
            )
            inst = repo.create(inst)
            instances.append(inst)
        test_uow.commit()
        return instances

    @pytest.mark.parametrize("status,expected", [(ExecutionStatus.PENDING, 5), (ExecutionStatus.COMPLETED, 0)])
    def test_list_by_status(self, test_uow, setup_instances, status, expected):
        """Test list_by_status returns only instances with given status."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        instances = repo.list_by_status(status)
        assert len(instances) == expected

    @pytest.mark.parametrize("limit,offset,expected_count", [(0, 0, 0), (2, 2, 2), (10, 0, 5), (2, 10, 0)])
    def test_list_by_engine_pagination(self, test_uow, engine_entity, setup_instances, limit, offset, expected_count):
        """Test pagination of list_by_engine."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        instances = repo.list_by_engine(engine_entity.id, limit=limit, offset=offset)
        assert len(instances) == expected_count

    def test_list_running_with_soft_deleted(self, test_uow, engine_entity):
        """Test list_running respects include_soft_deleted."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        inst = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext",
            status=ExecutionStatus.PROCESSING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst = repo.create(inst)
        test_uow.commit()
        repo.delete(inst.id, soft=True)
        test_uow.commit()

        running = repo.list_running()
        assert len(running) == 0
        running = repo.list_running(include_soft_deleted=True)
        assert len(running) == 1
        assert running[0].is_active is False


class TestOrchestrationInstanceRepositoryExtra:
    """Additional tests for OrchestrationInstanceRepository."""
    def test_get_by_engine_and_external_include_soft_deleted(self, test_uow, engine_entity):
        """Test get_by_engine_and_external with include_soft_deleted flag."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        inst = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo.create(inst)
        test_uow.commit()
        repo.delete(inst.id, soft=True)
        test_uow.commit()
        assert repo.get_by_engine_and_external(engine_entity.id, "ext") is None
        found = repo.get_by_engine_and_external(engine_entity.id, "ext", include_soft_deleted=True)
        assert found is not None
        assert found.is_active is False

    @pytest.mark.parametrize(
        "status,include_soft_deleted,expected_count",
        [(ExecutionStatus.PENDING, False, 4), (ExecutionStatus.PENDING, True, 5)],
    )
    def test_list_by_status_filter_combinations(
        self, test_uow, engine_entity, status, include_soft_deleted, expected_count
    ):
        """Test combination of status filter and soft-deleted inclusion."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        for i in range(5):
            inst = OrchestrationInstance(
                engine_id=engine_entity.id,
                external_id=f"ext{i}",
                status=ExecutionStatus.PENDING,
                instance_metadata={},
                duration_seconds=0,
            )
            repo.create(inst)
        instances = repo.list()
        repo.delete(instances[0].id, soft=True)
        test_uow.commit()
        result = repo.list_by_status(status, include_soft_deleted=include_soft_deleted)
        assert len(result) == expected_count

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_engine_pagination(self, test_uow, engine_entity, limit, offset, expected):
        """Test pagination of list_by_engine."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        for i in range(5):
            inst = OrchestrationInstance(
                engine_id=engine_entity.id,
                external_id=f"ext{i}",
                status=ExecutionStatus.PENDING,
                instance_metadata={},
                duration_seconds=0,
            )
            repo.create(inst)
        test_uow.commit()
        result = repo.list_by_engine(engine_entity.id, limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_engine_include_soft_deleted(self, test_uow, engine_entity):
        """Test list_by_engine with include_soft_deleted."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        inst = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo.create(inst)
        test_uow.commit()
        repo.delete(inst.id, soft=True)
        test_uow.commit()
        assert len(repo.list_by_engine(engine_entity.id)) == 0
        assert len(repo.list_by_engine(engine_entity.id, include_soft_deleted=True)) == 1

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_by_status_pagination(self, test_uow, engine_entity, limit, offset, expected):
        """Test pagination of list_by_status."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        for i in range(5):
            inst = OrchestrationInstance(
                engine_id=engine_entity.id,
                external_id=f"ext{i}",
                status=ExecutionStatus.PENDING,
                instance_metadata={},
                duration_seconds=0,
            )
            repo.create(inst)
        test_uow.commit()
        result = repo.list_by_status(ExecutionStatus.PENDING, limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_running_include_soft_deleted(self, test_uow, engine_entity):
        """Test list_running with include_soft_deleted."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        inst = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext",
            status=ExecutionStatus.PROCESSING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo.create(inst)
        test_uow.commit()
        repo.delete(inst.id, soft=True)
        test_uow.commit()
        assert len(repo.list_running()) == 0
        assert len(repo.list_running(include_soft_deleted=True)) == 1

    @pytest.mark.parametrize("limit,offset,expected", [(0, 0, 0), (2, 0, 2), (2, 2, 2), (2, 10, 0)])
    def test_list_running_pagination(self, test_uow, engine_entity, limit, offset, expected):
        """Test pagination of list_running."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        for i in range(5):
            inst = OrchestrationInstance(
                engine_id=engine_entity.id,
                external_id=f"ext{i}",
                status=ExecutionStatus.PROCESSING,
                instance_metadata={},
                duration_seconds=0,
            )
            repo.create(inst)
        test_uow.commit()
        result = repo.list_running(limit=limit, offset=offset)
        assert len(result) == expected

    def test_list_by_engine(self, test_uow, engine_entity):
        """Test list_by_engine returns all instances for an engine."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        inst1 = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext1",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst2 = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext2",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo.create(inst1)
        repo.create(inst2)
        test_uow.commit()

        results = repo.list_by_engine(engine_entity.id)
        assert len(results) == 2
        assert {i.external_id for i in results} == {"ext1", "ext2"}

    def test_list_by_status(self, test_uow):
        """Test list_by_status returns instances with given status."""
        repo_engine = EngineRepository(test_uow.session, test_uow)
        repo_instance = OrchestrationInstanceRepository(test_uow.session, test_uow)

        engine1 = Engine(name="engine1", type="test")
        engine1 = repo_engine.create(engine1)
        engine2 = Engine(name="engine2", type="test")
        engine2 = repo_engine.create(engine2)

        inst1 = OrchestrationInstance(
            engine_id=engine1.id,
            external_id="ext1",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst2 = OrchestrationInstance(
            engine_id=engine2.id,
            external_id="ext2",
            status=ExecutionStatus.PROCESSING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst3 = OrchestrationInstance(
            engine_id=engine1.id,
            external_id="ext3",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo_instance.create(inst1)
        repo_instance.create(inst2)
        repo_instance.create(inst3)
        test_uow.commit()

        pending = repo_instance.list_by_status(ExecutionStatus.PENDING)
        assert len(pending) == 2
        processing = repo_instance.list_by_status(ExecutionStatus.PROCESSING)
        assert len(processing) == 1
        assert processing[0].external_id == "ext2"

    def test_list_running(self, test_uow):
        """Test list_running returns instances with PROCESSING or RETRYING status."""
        repo_engine = EngineRepository(test_uow.session, test_uow)
        repo_instance = OrchestrationInstanceRepository(test_uow.session, test_uow)

        engine1 = Engine(name="engine1", type="test")
        engine1 = repo_engine.create(engine1)
        engine2 = Engine(name="engine2", type="test")
        engine2 = repo_engine.create(engine2)

        inst1 = OrchestrationInstance(
            engine_id=engine1.id,
            external_id="ext1",
            status=ExecutionStatus.PROCESSING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst2 = OrchestrationInstance(
            engine_id=engine2.id,
            external_id="ext2",
            status=ExecutionStatus.RETRYING,
            instance_metadata={},
            duration_seconds=0,
        )
        inst3 = OrchestrationInstance(
            engine_id=engine1.id,
            external_id="ext3",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        repo_instance.create(inst1)
        repo_instance.create(inst2)
        repo_instance.create(inst3)
        test_uow.commit()

        running = repo_instance.list_running()
        assert len(running) == 2
        assert {i.external_id for i in running} == {"ext1", "ext2"}