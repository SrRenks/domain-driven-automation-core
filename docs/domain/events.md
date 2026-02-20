## Domain Events

Domain events represent significant occurrences within the domain. They are raised by entities and dispatched after a successful transaction commit via the `EventBus`.

### [ItemExecutionFailed]
**Definition**: Emitted when an item execution fails permanently or enters retry state.

**Fields**:
- `item_execution_id`: UUID of the failing item execution.
- `run_id`: UUID of the parent run.
- `item_id`: UUID of the item.
- `error_message`: Details of the failure.
- `attempt_count`: Number of attempts made.
- `timestamp`: When the event occurred (defaults to current UTC time).

### [RunCompleted]
**Definition**: Emitted when a run completes successfully.

**Fields**:
- `run_id`: UUID of the completed run.
- `automation_id`: UUID of the automation.
- `finished_at`: Completion timestamp.
- `timestamp`: When the event occurred (defaults to current UTC time).

### [RunFailed]
**Definition**: Emitted when a run fails.

**Fields**:
- `run_id`: UUID of the failed run.
- `automation_id`: UUID of the automation.
- `error_summary`: High-level error description.
- `finished_at`: Failure timestamp.
- `timestamp`: When the event occurred (defaults to current UTC time).

### [RunCancelled]
**Definition**: Emitted when a run is cancelled.

**Fields**:
- `run_id`: UUID of the cancelled run.
- `automation_id`: UUID of the automation.
- `cancellation_reason`: Why it was cancelled.
- `finished_at`: Cancellation timestamp.
- `timestamp`: When the event occurred (defaults to current UTC time).

### [BatchExecutionFailed]
**Definition**: Emitted when a batch execution fails.

**Fields**:
- `batch_execution_id`: UUID of the failing batch execution.
- `run_id`: UUID of the parent run.
- `batch_id`: UUID of the batch.
- `finished_at`: Failure timestamp.
- `timestamp`: When the event occurred (defaults to current UTC time).