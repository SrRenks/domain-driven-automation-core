## Domain Exceptions

### [DomainError]
**Definition**: Base exception for all domain errors.

**Purpose**: Provide a common ancestor for domain-specific exceptions, allowing catch-all handling if needed.

**Key characteristics**:
- **message**: Error description.
- **original_error**: Optional original exception for chaining.

### [ValidationError]
**Definition**: Raised when domain validation fails (e.g., invalid field value).

**Purpose**: Signal that an entity or value object was constructed with invalid data.

**Key characteristics**:
- **entity_name**: Name of the entity or value object.
- **field**: Specific field that failed validation.
- **reason**: Explanation of why validation failed.

**Examples**:
```python
raise ValidationError("Automation", "name", "cannot be empty")
```

### [InvalidStateError]
**Definition**: Raised when an operation is attempted on an entity in an inappropriate state.

**Purpose**: Prevent illegal state transitions (e.g., completing an already completed run).

**Key characteristics**:
- **entity_name**: Type of entity.
- **entity_id**: UUID of the entity.
- **current_state**: Current state value (e.g., status).
- **operation**: Name of the operation attempted.

**Examples**:
```python
raise InvalidStateError("Run", run.id, run.status.value, "complete")
```

**Note**: `ConcurrencyError` is **not** defined in the domain layer. It is raised by the infrastructure layer (repositories) when an optimistic locking conflict occurs. Application services should catch and handle it appropriately.