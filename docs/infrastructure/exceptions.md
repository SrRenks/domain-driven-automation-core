## Infrastructure Exceptions

### [RepositoryError]
**Definition**: Base exception for all repository errors.

**Purpose**: Provide a common ancestor for infrastructure-layer exceptions.

**Key characteristics**:
- **message**: Error description.
- **original_error**: Optional original exception for chaining.

### [EntityNotFoundError]
**Definition**: Raised when an entity is not found in the database.

**Purpose**: Signal that a requested entity does not exist.

**Key characteristics**:
- **entity_name**: Name of the entity type.
- **entity_id**: UUID that was not found.

**Examples**:
```python
raise EntityNotFoundError("Automation", automation_id)
```

### [DuplicateEntityError]
**Definition**: Raised when attempting to create an entity that violates a unique constraint.

**Purpose**: Indicate that an entity with the same unique fields already exists.

**Key characteristics**:
- **entity_name**: Name of the entity type.
- **constraint_info**: Description of the violated constraint.

**Examples**:
```python
raise DuplicateEntityError("Batch", "automation_id and name must be unique")
```

### [ConcurrencyError]
**Definition**: Raised when optimistic locking version mismatch occurs.

**Purpose**: Indicate that the entity was modified by another process since it was read.

**Key characteristics**:
- **entity_name**: Name of the entity type.
- **entity_id**: UUID of the entity.
- **expected_version**: Version the caller expected.
- **actual_version**: Current version in the database.
- **extra**: Optional string for additional context (e.g., “Entity not tracked; retrieve it via get() first”).

**Examples**:
```python
raise ConcurrencyError("Run", run.id, 3, 5)
```