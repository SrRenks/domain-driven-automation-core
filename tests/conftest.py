import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from src.project.infrastructure.database import Base, DatabaseConfig
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
from src.project.infrastructure.database.repositories.orchestration import (
    EngineRepository,
    OrchestrationInstanceRepository,
)
from src.project.domain.entities.definition import Automation, Batch, Item
from src.project.domain.entities.execution import Run, BatchExecution, ItemExecution
from src.project.domain.entities.orchestration import Engine, OrchestrationInstance
from src.project.domain.enums import ExecutionStatus


postgresql_proc = factories.postgresql_proc(
    host="localhost",
    port=None,
    user="postgres",
    password="mysecretpassword",
)


@pytest.fixture
def engine(postgresql):
    """Create a SQLAlchemy engine connected to the test database.

    Drops and recreates all tables defined in `Base` metadata to ensure a clean
    schema for each test run.

    Args:
        postgresql: pytest-postgresql fixture providing a running PostgreSQL process.

    Yields:
        sqlalchemy.engine.Engine: Engine connected to the test database.
    """
    url = URL.create(
        drivername="postgresql",
        username=postgresql.info.user,
        password=postgresql.info.password,
        host=postgresql.info.host,
        port=postgresql.info.port,
        database=postgresql.info.dbname,
    )
    engine = create_engine(url, echo=True)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Provide a database session that is rolled back after the test.

    Args:
        engine (sqlalchemy.engine.Engine): The database engine.

    Yields:
        sqlalchemy.orm.Session: A session that will be closed after the test.
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def db_config(engine):
    """Provide a DatabaseConfig instance configured for the test database.

    Args:
        engine (sqlalchemy.engine.Engine): The database engine.

    Returns:
        DatabaseConfig: Configuration object for database connection.
    """
    url_str = engine.url.render_as_string(hide_password=False)
    return DatabaseConfig(url_str)

class UoWHelper:
    """Minimal unit of work with identity map, for testing repositories.

    This helper mimics the interface of a real UoW, providing commit, rollback,
    flush, and identity map methods. It does not track changes automatically;
    the test must manually call commit/flush.

    Attributes:
        session (sqlalchemy.orm.Session): The database session.
        _identity_map (dict): Dictionary storing tracked entities by class and ID.
    """
    def __init__(self, session):
        """Initialize the UoW helper with a session.

        Args:
            session (sqlalchemy.orm.Session): The session to use.
        """
        self.session = session
        self._identity_map = {}

    def commit(self):
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self):
        """Roll back the current transaction."""
        self.session.rollback()

    def flush(self):
        """Flush pending changes to the database without committing."""
        self.session.flush()

    def has_entity(self, cls, id):
        """Check if an entity of a given class and ID is in the identity map.

        Args:
            cls (type): The entity class.
            id (UUID): The entity ID.

        Returns:
            bool: True if the entity is present, False otherwise.
        """
        return id in self._identity_map.get(cls, {})

    def get_entity(self, cls, id):
        """Retrieve an entity from the identity map.

        Args:
            cls (type): The entity class.
            id (UUID): The entity ID.

        Returns:
            object or None: The entity instance if found, else None.
        """
        return self._identity_map.get(cls, {}).get(id)

    def register_entity(self, entity, entity_id=None):
        """Register an entity in the identity map.

        Args:
            entity (DomainEntity): The entity to register.
            entity_id (UUID, optional): The ID to use. If None, uses `entity.id`.
        """
        if entity_id is None:
            entity_id = entity.id
        cls = type(entity)
        if cls not in self._identity_map:
            self._identity_map[cls] = {}
        self._identity_map[cls][entity_id] = entity

    def unregister_entity(self, cls, id):
        """Remove an entity from the identity map.

        Args:
            cls (type): The entity class.
            id (UUID): The entity ID.
        """
        if cls in self._identity_map and id in self._identity_map[cls]:
            del self._identity_map[cls][id]


@pytest.fixture
def test_uow(db_session):
    """Provide a UoWHelper instance for repository tests.

    Args:
        db_session (sqlalchemy.orm.Session): The database session.

    Returns:
        UoWHelper: The unit of work helper.
    """
    return UoWHelper(db_session)

class MockUoW:
    """Mock unit of work with only an identity map (no session).

    Used for testing repository logic without database interaction.

    Attributes:
        _identity_map (dict): Dictionary storing tracked entities by class and ID.
    """
    def __init__(self):
        """Initialize an empty identity map."""
        self._identity_map = {}

    def has_entity(self, cls, id):
        """Check if an entity of a given class and ID is in the identity map.

        Args:
            cls (type): The entity class.
            id (UUID): The entity ID.

        Returns:
            bool: True if the entity is present.
        """
        return id in self._identity_map.get(cls, {})

    def get_entity(self, cls, id):
        """Retrieve an entity from the identity map.

        Args:
            cls (type): The entity class.
            id (UUID): The entity ID.

        Returns:
            object or None: The entity instance if found.
        """
        return self._identity_map.get(cls, {}).get(id)

    def register_entity(self, entity, entity_id=None):
        """Register an entity in the identity map.

        Args:
            entity (DomainEntity): The entity to register.
            entity_id (UUID, optional): The ID to use. If None, uses `entity.id`.
        """
        if entity_id is None:
            entity_id = entity.id
        cls = type(entity)
        if cls not in self._identity_map:
            self._identity_map[cls] = {}
        self._identity_map[cls][entity_id] = entity

    def unregister_entity(self, cls, id):
        if cls in self._identity_map and id in self._identity_map[cls]:
            del self._identity_map[cls][id]


@pytest.fixture
def uow_mock():
    """Provide a mock UoW (identity map only) for repository tests.

    Returns:
        MockUoW: The mock unit of work.
    """
    return MockUoW()

@pytest.fixture
def automation(test_uow):
    """Create and return a persisted Automation.

    Args:
        test_uow (UoWHelper): The unit of work helper.

    Returns:
        Automation: A persisted automation entity.
    """
    repo = AutomationRepository(test_uow.session, test_uow)
    auto = Automation(name="test-auto")
    repo.create(auto)
    test_uow.commit()
    return auto


@pytest.fixture
def batch(test_uow, automation):
    """Create and return a persisted Batch belonging to the automation fixture.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        automation (Automation): The parent automation.

    Returns:
        Batch: A persisted batch entity.
    """
    repo = BatchRepository(test_uow.session, test_uow)
    batch = Batch(automation_id=automation.id, name="test-batch")
    repo.create(batch)
    test_uow.commit()
    return batch


@pytest.fixture
def item(test_uow, batch):
    """Create and return a persisted Item belonging to the batch fixture.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        batch (Batch): The parent batch.

    Returns:
        Item: A persisted item entity.
    """
    repo = ItemRepository(test_uow.session, test_uow)
    item = Item(batch_id=batch.id, sequence_number=1)
    repo.create(item)
    test_uow.commit()
    return item


@pytest.fixture
def run(test_uow, automation):
    """Create and return a persisted Run belonging to the automation fixture.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        automation (Automation): The parent automation.

    Returns:
        Run: A persisted run entity.
    """
    repo = RunRepository(test_uow.session, test_uow)
    run = Run(automation_id=automation.id, correlation_id="corr-123")
    repo.create(run)
    test_uow.commit()
    return run


@pytest.fixture
def batch_execution(test_uow, run, batch):
    """Create and return a persisted BatchExecution for the given run and batch.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        run (Run): The parent run.
        batch (Batch): The parent batch.

    Returns:
        BatchExecution: A persisted batch execution entity.
    """
    repo = BatchExecutionRepository(test_uow.session, test_uow)
    be = BatchExecution(run_id=run.id, batch_id=batch.id, status=ExecutionStatus.PENDING)
    repo.create(be)
    test_uow.commit()
    return be


@pytest.fixture
def item_execution(test_uow, run, batch_execution, item):
    """Create and return a persisted ItemExecution.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        run (Run): The parent run.
        batch_execution (BatchExecution): The parent batch execution.
        item (Item): The associated item.

    Returns:
        ItemExecution: A persisted item execution entity.
    """
    repo = ItemExecutionRepository(test_uow.session, test_uow)
    ie = ItemExecution(
        run_id=run.id,
        batch_execution_id=batch_execution.id,
        item_id=item.id,
        status=ExecutionStatus.PENDING,
        max_attempts=3,
    )
    repo.create(ie)
    test_uow.commit()
    return ie


@pytest.fixture
def engine_entity(test_uow):
    """Create and return a persisted Engine (orchestration).

    Args:
        test_uow (UoWHelper): The unit of work helper.

    Returns:
        Engine: A persisted engine entity.
    """
    repo = EngineRepository(test_uow.session, test_uow)
    eng = Engine(name="test-engine", type="docker")
    repo.create(eng)
    test_uow.commit()
    return eng


@pytest.fixture
def orchestration_instance(test_uow, engine_entity):
    """Create and return a persisted OrchestrationInstance.

    Args:
        test_uow (UoWHelper): The unit of work helper.
        engine_entity (Engine): The parent engine.

    Returns:
        OrchestrationInstance: A persisted orchestration instance.
    """
    repo = OrchestrationInstanceRepository(test_uow.session, test_uow)
    inst = OrchestrationInstance(
        engine_id=engine_entity.id,
        external_id="ext-123",
        status=ExecutionStatus.PENDING,
        instance_metadata={},
        duration_seconds=0,
    )
    repo.create(inst)
    test_uow.commit()
    return inst