## Domain Base Classes

### [ValueObject]
**Definition**: An immutable object whose equality is based on the values of its attributes, not on identity.

**Purpose**: Represent descriptive aspects of the domain with no conceptual identity. They are interchangeable if all attributes are equal.

**Key characteristics**:
- Declared as `@dataclass(frozen=True)`.
- All attributes must be hashable; validation in `__post_init__` ensures this.
- Equality and hash methods are automatically provided based on all fields.
- Cannot be modified after creation.

**Relationships / Rules**:
- Used within entities to encapsulate complex attributes (e.g., `AuditInfo`, `VersionInfo`, `Schema`).
- A value object can contain other value objects but should not reference entities.

**Examples**:
```python
@dataclass(frozen=True)
class AuditInfo(ValueObject):
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

@dataclass(frozen=True)
class Schema(ValueObject):
    definition: Dict[str, Any]
```

### [DomainEntity]
**Definition**: Abstract base class for all domain entities, providing common fields and behavior.

**Purpose**: Centralize shared attributes (ID, timestamps, audit, version, soft delete) and operations (`touch`, `deactivate`, `activate`, event handling) to ensure consistency across all domain entities.

**Key characteristics**:
- All fields are `init=False` (set by the database/repository).
- Provides `_bump_version()` to increment version and update `updated_at` (used in state changes).
- `touch(user)` updates timestamps without changing version.
- `deactivate()` and `activate()` toggle soft delete and bump version.
- Equality based on `id` only (two entities are considered equal if they have the same class and same id).
- **Event handling**:
  - `_events`: internal list of domain events.
  - `register_event(event)`: adds an event to the list.
  - `pop_events()`: returns and clears the list.

**Relationships / Rules**:
- All concrete domain entities that require identity, versioning, and lifecycle management inherit from `DomainEntity`.
- Immutable audit records (e.g., `ItemStateHistory`) are **not** `DomainEntity` subclasses; they are treated as immutable value objects or separate persistable records without versioning or soft delete.

**Examples**:
```python
@dataclass
class Automation(DomainEntity):
    name: str
    description: Optional[str] = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValidationError(...)
```