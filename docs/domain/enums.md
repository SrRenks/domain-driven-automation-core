## Enums

### [ExecutionStatus]
**Definition**: Enumeration of possible execution states for runs, batches, items, and orchestration instances.

**Purpose**: Provide a finite set of states and define allowed transitions, active/finished states, and query helpers.

**Key characteristics**:
- Values: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`, `SKIPPED`, `RETRYING`.
- Inherits from `str, Enum` for easy serialization.
- **Properties**:
  - `is_finished`: True for `COMPLETED`, `FAILED`, `CANCELLED`, `SKIPPED`.
  - `is_active`: True for `PENDING`, `PROCESSING`, `RETRYING`.
  - `is_running`: True for `PROCESSING`, `RETRYING`.
- **Method** `can_transition_to(new_status)`: Checks validity based on a predefined transition matrix.

**Relationships / Rules**:
- Used by all execution-related entities to enforce state machines.
- The transition matrix ensures no illegal state changes.

**Transition Matrix**:
| Current       | Allowed New States                                      |
|---------------|--------------------------------------------------------|
| PENDING       | PROCESSING, CANCELLED, SKIPPED                         |
| PROCESSING    | COMPLETED, FAILED, RETRYING, CANCELLED                 |
| RETRYING      | PROCESSING, FAILED, CANCELLED                          |
| COMPLETED     | (none)                                                 |
| FAILED        | PENDING, RETRYING                                      |
| CANCELLED     | (none)                                                 |
| SKIPPED       | (none)                                                 |

**Examples**:
```python
if new_status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
    assert new_status.is_finished
assert ExecutionStatus.PENDING.can_transition_to(ExecutionStatus.PROCESSING)  # True
```