import logging

import pytest

from src.project.utils.logger import setup_logger, RichTqdmHandler


@pytest.fixture
def clean_logger():
    """Provide a logger instance and ensure handlers are cleaned up after test.

    The fixture creates a logger using `setup_logger` with name "test_logger".
    After the test, it clears all handlers and restores propagation to avoid
    interfering with other tests.

    Yields:
        logging.Logger: The configured logger instance.
    """
    logger = setup_logger("test_logger")
    yield logger
    logger.handlers.clear()
    logger.propagate = True


def test_setup_logger_defaults(clean_logger):
    """Test that `setup_logger` creates a logger with default settings.

    Verifies that the logger has INFO level, exactly one handler of type
    `RichTqdmHandler`, and propagation is disabled.
    """
    logger = clean_logger
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], RichTqdmHandler)
    assert logger.propagate is False


def test_setup_logger_with_custom_level():
    """Test that `setup_logger` respects a custom logging level.

    Creates a logger with DEBUG level and asserts its level is set correctly.
    """
    logger = setup_logger("custom_level", level=logging.DEBUG)
    assert logger.level == logging.DEBUG
    logger.handlers.clear()


def test_logger_does_not_duplicate_handlers():
    """Test that calling `setup_logger` twice on the same name does not add duplicate handlers.

    Ensures the second call does not increase the number of handlers attached to the logger.
    """
    logger1 = setup_logger("dup_test")
    handler_count = len(logger1.handlers)
    logger2 = setup_logger("dup_test")
    assert len(logger2.handlers) == handler_count
    logger1.handlers.clear()
    logger2.handlers.clear()


def test_logger_emits_messages(caplog):
    """Test that the logger actually logs messages.

    Uses `caplog` to capture log records and verifies that an INFO message appears.
    """
    caplog.set_level(logging.INFO)
    logger = setup_logger("test_emit")
    logger.propagate = True
    test_message = "hello world"
    logger.info(test_message)
    assert any(test_message in record.message for record in caplog.records)
    logger.handlers.clear()


def test_logger_propagate_false_by_default():
    """Test that logger.propagate is set to False by default.

    Checks that newly created loggers do not propagate messages to parent loggers.
    """
    logger = setup_logger("prop_test")
    assert logger.propagate is False
    logger.handlers.clear()


def test_custom_format_passed_to_handler():
    """Test that a custom format string is correctly passed to the handler.

    Creates a logger with a custom format and verifies that the handler's formatter
    uses that exact format string.
    """
    custom_fmt = "%(levelname)s - %(message)s"
    logger = setup_logger("fmt_test", fmt=custom_fmt)
    handler = logger.handlers[0]
    assert handler.formatter._fmt == custom_fmt
    logger.handlers.clear()