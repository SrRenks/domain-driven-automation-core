from src.project.domain.entities.orchestration import Engine, OrchestrationInstance
from src.project.domain.enums import ExecutionStatus
from src.project.infrastructure.database.repositories.orchestration import EngineRepository, OrchestrationInstanceRepository


class TestEngineRepository:
    """Test suite for EngineRepository."""
    def test_create_engine(self, test_uow):
        """Test creating and retrieving an engine."""
        repo = EngineRepository(test_uow.session, test_uow)
        engine = Engine(name="test-engine", type="docker")
        created = repo.create(engine)
        test_uow.commit()

        found = repo.get(created.id)
        assert found is not None
        assert found.name == "test-engine"

    def test_get_by_name(self, test_uow):
        """Test retrieving an engine by name."""
        repo = EngineRepository(test_uow.session, test_uow)
        engine = Engine(name="unique-engine", type="k8s")
        created = repo.create(engine)
        test_uow.commit()

        found = repo.get_by_name("unique-engine")
        assert found is not None
        assert found.id == created.id

    def test_get_by_name_not_found(self, test_uow):
        """Test that a missing name returns None."""
        repo = EngineRepository(test_uow.session, test_uow)
        assert repo.get_by_name("missing") is None


class TestOrchestrationInstanceRepository:
    """Test suite for OrchestrationInstanceRepository."""
    def test_create_instance(self, test_uow, engine_entity):
        """Test creating and retrieving an orchestration instance."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        instance = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext-123",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        created = repo.create(instance)
        test_uow.commit()

        found = repo.get(created.id)
        assert found is not None
        assert found.external_id == "ext-123"

    def test_get_by_engine_and_external(self, test_uow, engine_entity):
        """Test retrieving an instance by engine_id and external_id."""
        repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
        instance = OrchestrationInstance(
            engine_id=engine_entity.id,
            external_id="ext-456",
            status=ExecutionStatus.PENDING,
            instance_metadata={},
            duration_seconds=0,
        )
        created = repo.create(instance)
        test_uow.commit()

        found = repo.get_by_engine_and_external(engine_entity.id, "ext-456")
        assert found is not None
        assert found.id == created.id