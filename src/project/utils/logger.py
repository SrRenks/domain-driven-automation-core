from rich.console import Console
from typing import Optional
from rich.text import Text
from io import StringIO
from tqdm import tqdm
import logging
import time
import sys


class RichTqdmHandler(logging.StreamHandler):
    """Custom logging handler that renders rich text logs compatible with tqdm progress bars.

    This handler formats log records with Rich (timestamps, log levels, source info) and
    writes them using `tqdm.write` to avoid interfering with progress bars. It supports
    optional grouping of consecutive logs with the same timestamp.

    Attributes:
        group_by_ts (bool): Whether to group log messages by timestamp.
        _last_ts_raw (Optional[str]): Last raw timestamp string for grouping.
        _last_prefix (Optional[Text]): Last formatted prefix for grouping.
        console (Console): Rich console for terminal output.
        _buffer (StringIO): Buffer for ANSI text generation.
        ansi_console (Console): Rich console writing to buffer.
    """

    def __init__(self, group_by_ts: bool = False, *args, **kwargs) -> None:
        """
        Args:
            group_by_ts (bool, optional): Whether to group log messages by timestamp.
                Defaults to False.
            *args: Variable length argument list for logging.StreamHandler.
            **kwargs: Arbitrary keyword arguments for logging.StreamHandler.
        """
        super().__init__(*args, **kwargs)
        self.group_by_ts = group_by_ts
        self._last_ts_raw: Optional[str] = None
        self._last_prefix: Optional[Text] = None

        self.console = Console(force_terminal=True, color_system="truecolor")
        self._buffer = StringIO()
        self.ansi_console = Console(file=self._buffer, force_terminal=True, color_system="truecolor")

    def emit(self, record: logging.LogRecord) -> None:
        """Render a log record using Rich and safely print it alongside tqdm bars.

        Args:
            record (logging.LogRecord): The log record to emit.

        Raises:
            Exception: If formatting fails, the error is printed to stderr and
                `handleError` is called.
        """
        try:
            msg = self.format(record)

            level_style = f"logging.level.{record.levelname.lower()}"
            level_text = f"[{level_style}]{record.levelname.ljust(8)}[/]"
            ts_raw = time.strftime("[%m/%d/%y %H:%M:%S]", time.localtime(record.created))
            ts_markup = f"[dim]{ts_raw}[/dim]"

            if not self.group_by_ts or self._last_ts_raw != ts_raw or self._last_prefix is None:
                prefix = Text.from_markup(f"{ts_markup} {level_text}")
                self._last_ts_raw = ts_raw
                self._last_prefix = prefix
            else:
                ts_width = 21
                prefix = Text.from_markup(f"{' ' * ts_width} {level_text}")

            file_line = f"{record.filename}:{record.lineno}"
            suffix = Text.from_markup(f"[dim]{file_line}[/dim]")
            message = Text.from_markup(msg)

            full = Text.assemble(prefix, " ", message, " ", suffix)

            self._buffer.seek(0)
            self._buffer.truncate(0)
            self.ansi_console.print(full)
            ansi_text = self._buffer.getvalue()
            if ansi_text.endswith('\n'):
                ansi_text = ansi_text[:-1]
            tqdm.write(ansi_text, file=sys.stderr)

        except Exception as e:
            print(f"RichTqdmHandler failed to format log record: {e}", file=sys.stderr)
            self.handleError(record)

def setup_logger(name: str, level: int = logging.INFO, fmt: Optional[str] = None) -> logging.Logger:
    """Configure a logger with RichTqdmHandler for rich console output compatible with tqdm.

    Args:
        name (str): Logger name.
        level (int, optional): Logging level. Defaults to logging.INFO.
        fmt (Optional[str], optional): Log message format. Defaults to '%(message)s'.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not any(isinstance(h, RichTqdmHandler) for h in logger.handlers):
        handler = RichTqdmHandler()
        formatter = logging.Formatter(fmt or "%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger