## Logging Utilities

### [RichTqdmHandler]
**Definition**: Custom logging handler that renders log records with Rich formatting and writes them using `tqdm.write` to avoid interfering with progress bars.

**Purpose**: Provide visually appealing, color‑coded logs that integrate seamlessly with `tqdm` progress bars in CLI applications.

**Key characteristics**:
- Inherits from `logging.StreamHandler`.
- Uses `rich.console.Console` to generate ANSI‑styled output.
- Builds a log line with timestamp, log level, message, and source file/line.
- **Supports grouping by timestamp**: When `group_by_ts=True`, consecutive logs with the same timestamp are aligned using a fixed width of 21 characters (the exact length of the timestamp `"[MM/DD/YY HH:MM:SS]"`). This avoids expensive terminal measurement calls.
- Writes the final ANSI string via `tqdm.write` to preserve progress bar rendering.

**Relationships / Rules**:
- Used by `setup_logger` to create loggers for application modules.
- Expects log formatter to output only the message (no extra decorations) – the handler adds all decorations.

**Examples**:
```python
logger = setup_logger(__name__)
logger.info("Processing batch %s", batch_id)   # Rich‑formatted output
```

### [setup_logger]
**Definition**: Utility function to configure a logger with `RichTqdmHandler`.

**Purpose**: Simplify logger creation and ensure consistent, tqdm‑compatible logging across the application.

**Key characteristics**:
- Accepts logger name, log level, and optional custom format string (defaults to `"%(message)s"`).
- Creates a logger and adds a `RichTqdmHandler` if not already present.
- Disables propagation to avoid duplicate logs.

**Relationships / Rules**:
- Called in each module to obtain a logger instance.
- The handler’s formatter must be set to `"%(message)s"` to avoid duplication.

**Examples**:
```python
logger = setup_logger("myapp", level=logging.DEBUG)
```