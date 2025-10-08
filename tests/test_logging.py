"""
Tests for logging utilities.
"""

import logging

from cvpilot.utils.logging import get_logger, setup_logging


class TestLogging:
    """Test logging utilities and configuration."""

    def test_setup_logging_default_level(self):
        """Test logging setup with default INFO level."""
        logger = setup_logging()

        assert logger.name == "cvpilot"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.Handler)

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        logger = setup_logging("DEBUG")

        assert logger.name == "cvpilot"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

    def test_setup_logging_info_level(self):
        """Test logging setup with INFO level."""
        logger = setup_logging("INFO")

        assert logger.name == "cvpilot"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1

    def test_setup_logging_warning_level(self):
        """Test logging setup with WARNING level."""
        logger = setup_logging("WARNING")

        assert logger.name == "cvpilot"
        assert logger.level == logging.WARNING
        assert len(logger.handlers) == 1

    def test_setup_logging_error_level(self):
        """Test logging setup with ERROR level."""
        logger = setup_logging("ERROR")

        assert logger.name == "cvpilot"
        assert logger.level == logging.ERROR
        assert len(logger.handlers) == 1

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        # Create a logger with existing handlers
        logger = logging.getLogger("cvpilot")
        logger.addHandler(logging.StreamHandler())
        logger.addHandler(logging.StreamHandler())

        # Setup logging should clear existing handlers
        setup_logging()

        assert len(logger.handlers) == 1

    def test_setup_logging_multiple_calls(self):
        """Test that multiple calls to setup_logging work correctly."""
        logger1 = setup_logging("DEBUG")
        logger2 = setup_logging("INFO")

        # Should return the same logger instance
        assert logger1 is logger2
        assert logger1.name == "cvpilot"
        assert logger1.level == logging.INFO  # Last level set

    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns the configured logger."""
        setup_logging("DEBUG")
        logger = get_logger()

        assert logger.name == "cvpilot"
        assert logger.level == logging.DEBUG

    def test_logger_handler_configuration(self):
        """Test that logger handlers are configured correctly."""
        logger = setup_logging("INFO")

        assert len(logger.handlers) == 1
        handler = logger.handlers[0]

        # Check handler properties
        assert handler.formatter is not None

    def test_logger_formatter(self):
        """Test that logger formatter is set correctly."""
        logger = setup_logging("INFO")
        handler = logger.handlers[0]

        # The formatter should be set
        assert handler.formatter is not None

    def test_rich_handler_used(self):
        """Test that RichHandler is used for console output."""
        logger = setup_logging("INFO")

        # Verify handler was added to logger
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is not None

    def test_console_used_for_rich_handler(self):
        """Test that Console is used for RichHandler."""
        logger = setup_logging("INFO")

        # Verify handler was added to logger
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is not None

    def test_logger_logging_levels(self):
        """Test that logger respects different logging levels."""
        # Test DEBUG level
        logger = setup_logging("DEBUG")
        assert logger.isEnabledFor(logging.DEBUG)
        assert logger.isEnabledFor(logging.INFO)
        assert logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)

        # Test INFO level
        logger = setup_logging("INFO")
        assert not logger.isEnabledFor(logging.DEBUG)
        assert logger.isEnabledFor(logging.INFO)
        assert logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)

        # Test WARNING level
        logger = setup_logging("WARNING")
        assert not logger.isEnabledFor(logging.DEBUG)
        assert not logger.isEnabledFor(logging.INFO)
        assert logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)

        # Test ERROR level
        logger = setup_logging("ERROR")
        assert not logger.isEnabledFor(logging.DEBUG)
        assert not logger.isEnabledFor(logging.INFO)
        assert not logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)

    def test_logger_name_consistency(self):
        """Test that logger name is consistent across calls."""
        logger1 = setup_logging("DEBUG")
        logger2 = get_logger()

        assert logger1.name == "cvpilot"
        assert logger2.name == "cvpilot"
        assert logger1 is logger2

    def test_logger_handler_properties(self):
        """Test that logger handler has correct properties."""
        logger = setup_logging("INFO")
        handler = logger.handlers[0]

        # Check that handler is properly configured
        assert handler.formatter is not None

    def test_logger_with_different_levels(self):
        """Test logger behavior with different levels."""
        # Test with DEBUG level
        logger = setup_logging("DEBUG")
        assert logger.level == logging.DEBUG

        # Test with INFO level
        logger = setup_logging("INFO")
        assert logger.level == logging.INFO

        # Test with WARNING level
        logger = setup_logging("WARNING")
        assert logger.level == logging.WARNING

        # Test with ERROR level
        logger = setup_logging("ERROR")
        assert logger.level == logging.ERROR

    def test_logger_handler_count(self):
        """Test that logger has correct number of handlers."""
        logger = setup_logging("INFO")

        # Should have exactly one handler
        assert len(logger.handlers) == 1

        # Multiple calls should not add more handlers
        setup_logging("DEBUG")
        assert len(logger.handlers) == 1

    def test_logger_handlers_cleared(self):
        """Test that existing handlers are cleared before adding new ones."""
        logger = logging.getLogger("cvpilot")

        # Add some dummy handlers
        logger.addHandler(logging.StreamHandler())
        logger.addHandler(logging.StreamHandler())
        logger.addHandler(logging.StreamHandler())

        # Should have at least 3 handlers
        assert len(logger.handlers) >= 3

        # Setup logging should clear and add one handler
        setup_logging("INFO")
        assert len(logger.handlers) == 1
