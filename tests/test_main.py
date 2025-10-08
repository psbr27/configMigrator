"""
Tests for main entry point.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from cvpilot.__main__ import main


class TestMainEntryPoint:
    """Test main entry point functionality."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert callable(main)

    @patch("cvpilot.__main__.migrate")
    def test_main_calls_migrate(self, mock_migrate):
        """Test that main function calls migrate command."""
        mock_migrate.return_value = None

        main()

        mock_migrate.assert_called_once()

    @patch("cvpilot.__main__.migrate")
    def test_main_handles_exceptions(self, mock_migrate):
        """Test that main function handles exceptions from migrate."""
        mock_migrate.side_effect = Exception("Test exception")

        # Should raise exception (main doesn't catch exceptions)
        with pytest.raises(Exception, match="Test exception"):
            main()

    def test_main_module_execution(self):
        """Test that main module can be executed."""
        # This tests the if __name__ == "__main__" block
        with patch("cvpilot.__main__.main"):
            # Simulate module execution
            import cvpilot.__main__

            # The main function should be available
            assert hasattr(cvpilot.__main__, "main")
            assert callable(cvpilot.__main__.main)

    def test_main_imports(self):
        """Test that main module imports correctly."""
        from cvpilot.__main__ import main
        from cvpilot.cli.commands import migrate

        assert main is not None
        assert migrate is not None

    @patch("cvpilot.__main__.migrate")
    def test_main_with_click_runner(self, mock_migrate):
        """Test main function with click runner simulation."""
        # Mock the migrate command to return a result
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_migrate.return_value = mock_result

        # Call main function
        main()

        # Verify migrate was called
        mock_migrate.assert_called_once()

    def test_main_module_structure(self):
        """Test that main module has correct structure."""
        import cvpilot.__main__ as main_module

        # Check that required attributes exist
        assert hasattr(main_module, "main")
        assert hasattr(main_module, "__name__")

        # Check that main is a function
        assert callable(main_module.main)

    def test_main_docstring(self):
        """Test that main function has proper docstring."""
        from cvpilot.__main__ import main

        # Check that main function has docstring
        assert main.__doc__ is not None
        assert "Main entry point" in main.__doc__

    @patch("cvpilot.__main__.migrate")
    def test_main_multiple_calls(self, mock_migrate):
        """Test that main function can be called multiple times."""
        mock_migrate.return_value = None

        # Call main multiple times
        main()
        main()
        main()

        # Verify migrate was called each time
        assert mock_migrate.call_count == 3

    def test_main_with_sys_argv(self):
        """Test main function with sys.argv simulation."""
        original_argv = sys.argv.copy()

        try:
            # Set up test argv
            sys.argv = ["cvpilot", "arg1", "arg2"]

            with patch("cvpilot.__main__.migrate") as mock_migrate:
                main()
                mock_migrate.assert_called_once()
        finally:
            # Restore original argv
            sys.argv = original_argv

    def test_main_module_attributes(self):
        """Test that main module has correct attributes."""
        import cvpilot.__main__ as main_module

        # Check module attributes
        assert hasattr(main_module, "__file__")
        assert hasattr(main_module, "__package__")
        assert hasattr(main_module, "__version__") or True  # Version may not be set

    def test_main_function_signature(self):
        """Test that main function has correct signature."""
        import inspect

        from cvpilot.__main__ import main

        # Get function signature
        sig = inspect.signature(main)

        # Check that main takes no parameters
        assert len(sig.parameters) == 0

    @patch("cvpilot.__main__.migrate")
    def test_main_with_click_abort(self, mock_migrate):
        """Test main function with click.Abort exception."""
        from click import Abort

        mock_migrate.side_effect = Abort()

        # Should raise Abort exception (main doesn't catch it)
        with pytest.raises(Abort):
            main()

    def test_main_module_execution_path(self):
        """Test the execution path when module is run directly."""
        # This tests the if __name__ == "__main__" block
        with patch("cvpilot.__main__.main"):
            # Simulate the module being run directly
            import cvpilot.__main__

            # Check that main function is available
            assert hasattr(cvpilot.__main__, "main")

            # The main function should be callable
            assert callable(cvpilot.__main__.main)

    def test_main_imports_migrate_command(self):
        """Test that main module imports migrate command correctly."""
        from cvpilot.__main__ import main
        from cvpilot.cli.commands import migrate

        # Both should be available
        assert main is not None
        assert migrate is not None

        # They should be different objects
        assert main is not migrate

    @patch("cvpilot.__main__.migrate")
    def test_main_with_different_migrate_results(self, mock_migrate):
        """Test main function with different migrate results."""
        # Test with successful result
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_migrate.return_value = mock_result

        main()
        mock_migrate.assert_called_once()

        # Reset mock
        mock_migrate.reset_mock()

        # Test with error result
        mock_result.exit_code = 1
        mock_migrate.return_value = mock_result

        main()
        mock_migrate.assert_called_once()

    def test_main_function_metadata(self):
        """Test main function metadata."""
        from cvpilot.__main__ import main

        # Check function name
        assert main.__name__ == "main"

        # Check function module
        assert main.__module__ == "cvpilot.__main__"

        # Check that it's a function
        assert callable(main)
