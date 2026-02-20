## Value Objects

### [AuditInfo]
**Definition**: Immutable container for audit-related timestamps and user information.

**Purpose**: Encapsulate audit metadata for entities that need to track creation and modification.

**Key characteristics**:
- **created_at**: Optional `datetime`.
- **created_by**: Optional `str`.
- **updated_at**: Optional `datetime`.
- **updated_by**: Optional `str`.
- Frozen dataclass, thus immutable.

**Relationships / Rules**:
- Used within domain entities that require audit trails.
- Typically populated from `DomainEntity` fields.

**Examples**:
```python
audit = AuditInfo(created_at=datetime.now(), created_by="admin")
```

### [VersionInfo]
**Definition**: Immutable value object representing version number for optimistic locking.

**Purpose**: Encapsulate versioning logic and provide increment operation.

**Key characteristics**:
- **version**: Integer (default 1).
- `increment()` returns a new `VersionInfo` with version+1.
- Frozen dataclass.

**Relationships / Rules**:
- Used in conjunction with `VersionMixin` in database models.
- Domain entities have a `version` field directly (not a value object) for simplicity, but this object can be used where needed.

**Examples**:
```python
v1 = VersionInfo(version=1)
v2 = v1.increment()  # version=2
```

### [Schema]
**Definition**: JSON schema definition for validating batch or item payloads.

**Purpose**: Provide a reusable, immutable schema object with validation capabilities.

**Key characteristics**:
- **definition**: `Dict[str, Any]` representing a JSON schema.
- `validate(data)` method uses `jsonschema` to validate input data.
- Returns `SchemaValidationResult`.
- Raises `ValidationError` if definition is not a dict.

**Relationships / Rules**:
- Used by `Automation` entity to validate batch/item payloads during execution.
- Can be stored as JSONB in the database.

**Examples**:
```python
schema = Schema(definition={"type": "object", "properties": {"name": {"type": "string"}}})
result = schema.validate({"name": "John"})  # valid=True, errors=[]
```

### [SchemaValidationResult]
**Definition**: Result of schema validation containing validity status and error messages.

**Purpose**: Provide a structured way to return validation outcomes.

**Key characteristics**:
- **valid**: Boolean indicating success.
- **errors**: List of error strings.
- Frozen dataclass.

**Relationships / Rules**:
- Returned by `Schema.validate()`.

**Examples**:
```python
result = SchemaValidationResult(valid=False, errors=["'name' is a required property"])
```