"""
Tests for CLI commands and user interface.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from config_migrator.cli.commands import migrate
from config_migrator.core.parser import YAMLParser


class TestCLICommands:
    """Test CLI commands and user interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

        # Create test YAML files
        self.nstf_file = os.path.join(self.temp_dir, "nstf.yaml")
        self.etf_file = os.path.join(self.temp_dir, "etf.yaml")
        self.newtf_file = os.path.join(self.temp_dir, "newtf.yaml")

        # Sample NSTF data
        nstf_data = {
            "version": "25.1.102",
            "site": "test-site",
            "config": {
                "database": {
                    "host": "nstf-db.example.com",
                    "port": 5432,
                },
            },
        }

        # Sample ETF data
        etf_data = {
            "version": "25.1.102",
            "config": {
                "database": {
                    "host": "etf-db.example.com",
                    "port": 5432,
                    "ssl": True,
                },
                "cache": {
                    "enabled": True,
                },
            },
        }

        # Sample NEWTF data
        newtf_data = {
            "version": "25.1.200",
            "config": {
                "database": {
                    "host": "newtf-db.example.com",
                    "port": 5432,
                    "ssl": True,
                    "pool_size": 10,
                },
                "cache": {
                    "enabled": True,
                    "ttl": 3600,
                },
                "monitoring": {
                    "enabled": True,
                },
            },
        }

        # Write test files
        parser = YAMLParser()
        parser.save_yaml_file(nstf_data, self.nstf_file)
        parser.save_yaml_file(etf_data, self.etf_file)
        parser.save_yaml_file(newtf_data, self.newtf_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_migrate_basic_usage(self):
        """Test basic migrate command usage."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 0
        assert "Complete Migration Workflow Successful" in result.output
        assert "migrated_new_eng_template.yml" in result.output

    def test_migrate_with_custom_output(self):
        """Test migrate command with custom output file."""
        output_file = os.path.join(self.temp_dir, "custom_output.yaml")

        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "-o",
                output_file,
            ],
        )

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        # Verify output file content
        parser = YAMLParser()
        output_data = parser.load_yaml_file(output_file)
        assert output_data["version"] == "25.1.102"  # From NSTF (precedence)
        assert output_data["site"] == "test-site"  # From NSTF

    def test_migrate_with_verbose_flag(self):
        """Test migrate command with verbose flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        assert "Step 1: Validating all input files" in result.output
        assert "Stage 1: Merging NSTF and ETF" in result.output
        assert "Stage 2: Merging with NEWTF" in result.output

    def test_migrate_with_debug_flag(self):
        """Test migrate command with debug flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "--debug",
            ],
        )

        assert result.exit_code == 0
        assert "Loading NSTF file:" in result.output
        assert "Loading ETF file:" in result.output
        assert "Loading NEWTF file:" in result.output

    def test_migrate_with_summary_flag(self):
        """Test migrate command with summary flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "--summary",
            ],
        )

        assert result.exit_code == 0
        assert "Complete Workflow Summary" in result.output
        assert "Complete Workflow Precedence Rules" in result.output

    def test_migrate_file_not_found(self):
        """Test migrate command with non-existent file."""
        result = self.runner.invoke(
            migrate,
            [
                "nonexistent.yaml",
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 2  # Click returns 2 for missing arguments
        assert "does not exist" in result.output

    def test_migrate_invalid_yaml(self):
        """Test migrate command with invalid YAML file."""
        invalid_file = os.path.join(self.temp_dir, "invalid.yaml")
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [")

        result = self.runner.invoke(
            migrate,
            [
                invalid_file,
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_migrate_help(self):
        """Test migrate command help."""
        result = self.runner.invoke(migrate, ["--help"])

        assert result.exit_code == 0
        assert "Config Migration Tool - Complete Workflow" in result.output
        assert "NSTF_FILE" in result.output
        assert "ETF_FILE" in result.output
        assert "NEWTF_FILE" in result.output
        assert "-o, --output" in result.output
        assert "-v, --verbose" in result.output
        assert "--debug" in result.output
        assert "--summary" in result.output

    @patch("config_migrator.cli.commands.setup_logging")
    def test_logging_setup_called(self, mock_setup_logging):
        """Test that logging setup is called with correct level."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "--debug",
            ],
        )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("DEBUG")

    @patch("config_migrator.cli.commands.setup_logging")
    def test_logging_setup_verbose(self, mock_setup_logging):
        """Test that logging setup is called with INFO level for verbose."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("INFO")

    @patch("config_migrator.cli.commands.setup_logging")
    def test_logging_setup_default(self, mock_setup_logging):
        """Test that logging setup is called with WARNING level by default."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("WARNING")

    def test_migrate_output_file_creation(self):
        """Test that output file is created with correct content."""
        output_file = os.path.join(self.temp_dir, "test_output.yaml")

        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "-o",
                output_file,
            ],
        )

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        # Verify the merged content
        parser = YAMLParser()
        output_data = parser.load_yaml_file(output_file)

        # Should have NSTF site value
        assert output_data["site"] == "test-site"

        # Should have NSTF version (precedence)
        assert output_data["version"] == "25.1.102"

        # Should have NSTF database host (precedence)
        assert output_data["config"]["database"]["host"] == "nstf-db.example.com"

        # Should have NEWTF pool_size (new feature)
        assert output_data["config"]["database"]["pool_size"] == 10

        # Should have NEWTF monitoring (new feature)
        assert "monitoring" in output_data["config"]
        assert output_data["config"]["monitoring"]["enabled"] is True

    def test_migrate_error_handling(self):
        """Test error handling in migrate command."""
        # Test with non-existent file
        result = self.runner.invoke(
            migrate,
            [
                "nonexistent.yaml",
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 2  # Click returns 2 for missing arguments
        assert "does not exist" in result.output

    def test_migrate_progress_display(self):
        """Test that progress is displayed during processing."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        # Progress should be shown in verbose mode
        assert "Step 1: Validating all input files" in result.output

    def test_migrate_success_panel(self):
        """Test that success panel is displayed."""
        result = self.runner.invoke(
            migrate,
            [
                self.nstf_file,
                self.etf_file,
                self.newtf_file,
            ],
        )

        assert result.exit_code == 0
        assert "Complete Migration Workflow Successful" in result.output
        assert "Stage 1: NSTF + ETF" in result.output
        assert "Stage 2: diff + NEWTF" in result.output
