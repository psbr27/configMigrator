"""
Tests for CLI commands and user interface.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cvpilot.cli.commands import migrate
from cvpilot.core.parser import YAMLParser


class TestCLICommands:
    """Test CLI commands and user interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

        # Create test YAML files
        self.nsprev_file = os.path.join(self.temp_dir, "nsprev.yaml")
        self.engprev_file = os.path.join(self.temp_dir, "engprev.yaml")
        self.engnew_file = os.path.join(self.temp_dir, "engnew.yaml")

        # Sample NSPREV data (namespace previous - site-specific)
        nsprev_data = {
            "global": {
                "sitename": "rcnltxekvzwcslf-y-or-x-004",
                "version": "25.1.102",
                "image": {"tag": "25.1.102"},
            },
            "site": "test-site",
            "config": {
                "database": {
                    "host": "nsprev-db.example.com",
                    "port": 5432,
                },
            },
        }

        # Sample ENGPREV data (engineering previous - base template)
        engprev_data = {
            "global": {
                "sitename": "cndbtiersitename",
                "version": "25.1.102",
                "image": {"tag": "25.1.102"},
            },
            "config": {
                "database": {
                    "host": "engprev-db.example.com",
                    "port": 5432,
                    "ssl": True,
                },
                "cache": {
                    "enabled": True,
                },
            },
        }

        # Sample ENGNEW data (engineering new - new template with updates)
        engnew_data = {
            "global": {
                "version": "25.1.200",
                "image": {"tag": "25.1.200"},
            },
            "config": {
                "database": {
                    "host": "engnew-db.example.com",
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
        parser.save_yaml_file(nsprev_data, self.nsprev_file)
        parser.save_yaml_file(engprev_data, self.engprev_file)
        parser.save_yaml_file(engnew_data, self.engnew_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_migrate_basic_usage(self):
        """Test basic migrate command usage with new naming."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
            ],
        )

        assert result.exit_code == 0
        assert "CVPilot Migration Workflow Successful!" in result.output
        # Should auto-generate filename from nsprev + engnew version
        assert "nsprev_25.1.200.yaml" in result.output

    def test_migrate_with_custom_output(self):
        """Test migrate command with custom output file."""
        output_file = os.path.join(self.temp_dir, "custom_output.yaml")

        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "-o",
                output_file,
            ],
        )

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        # Verify output file content
        parser = YAMLParser()
        output_data = parser.load_yaml_file(output_file)
        # NSPREV should have highest precedence
        assert (
            output_data["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
        )  # From NSPREV
        assert output_data["site"] == "test-site"  # From NSPREV
        # ENGNEW should provide new version
        assert output_data["global"]["version"] == "25.1.200"  # From ENGNEW

    def test_migrate_filename_generation(self):
        """Test automatic filename generation from nsprev + engnew version."""
        # Create a test file with version in filename
        nsprev_versioned_file = os.path.join(self.temp_dir, "site-config_25.1.102.yaml")
        parser = YAMLParser()
        parser.save_yaml_file(
            {
                "global": {
                    "sitename": "test-site",
                    "image": {"tag": "25.1.102"},
                },
            },
            nsprev_versioned_file,
        )

        result = self.runner.invoke(
            migrate,
            [
                nsprev_versioned_file,
                self.engprev_file,
                self.engnew_file,
            ],
        )

        assert result.exit_code == 0
        # Should generate filename: site-config_25.1.200.yaml (removes old version, adds engnew version)
        assert "site-config_25.1.200.yaml" in result.output

    def test_migrate_diff_file_creation(self):
        """Test that Stage 1 diff file is created."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        # Check that diff file creation is mentioned
        assert "diff_nsprev_engprev.yaml" in result.output

        # Verify diff file exists in current directory
        diff_file_path = "diff_nsprev_engprev.yaml"
        if os.path.exists(diff_file_path):
            parser = YAMLParser()
            diff_data = parser.load_yaml_file(diff_file_path)
            # Should only contain differences
            assert "global" in diff_data
            assert diff_data["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"

    def test_migrate_with_verbose_flag(self):
        """Test migrate command with verbose flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        assert "Step 1: Validating all input files" in result.output
        assert "Stage 1: Merging NSPREV and ENGPREV" in result.output
        assert "Stage 2: Merging with ENGNEW" in result.output

    def test_migrate_with_debug_flag(self):
        """Test migrate command with debug flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "--debug",
            ],
        )

        assert result.exit_code == 0
        assert "Loading NSPREV file:" in result.output
        assert "Loading ENGPREV file:" in result.output
        assert "Loading ENGNEW file:" in result.output

    def test_migrate_with_summary_flag(self):
        """Test migrate command with summary flag."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
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
                self.engprev_file,
                self.engnew_file,
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
                self.engprev_file,
                self.engnew_file,
            ],
        )

        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_migrate_help(self):
        """Test migrate command help."""
        result = self.runner.invoke(migrate, ["--help"])

        assert result.exit_code == 0
        assert "CVPilot Configuration Migration - Complete Workflow" in result.output
        assert "NSPREV_FILE" in result.output
        assert "ENGPREV_FILE" in result.output
        assert "ENGNEW_FILE" in result.output
        assert "-o, --output" in result.output
        assert "-v, --verbose" in result.output
        assert "--debug" in result.output
        assert "--summary" in result.output

    @patch("cvpilot.cli.commands.setup_logging")
    def test_logging_setup_called(self, mock_setup_logging):
        """Test that logging setup is called with correct level."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "--debug",
            ],
        )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("DEBUG")

    @patch("cvpilot.cli.commands.setup_logging")
    def test_logging_setup_verbose(self, mock_setup_logging):
        """Test that logging setup is called with INFO level for verbose."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "-v",
            ],
        )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once_with("INFO")

    @patch("cvpilot.cli.commands.setup_logging")
    def test_logging_setup_default(self, mock_setup_logging):
        """Test that logging setup is called with WARNING level by default."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
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
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
                "-o",
                output_file,
            ],
        )

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        # Verify the merged content
        parser = YAMLParser()
        output_data = parser.load_yaml_file(output_file)

        # Should have NSPREV site value
        assert output_data["site"] == "test-site"

        # Should have ENGNEW version (precedence: ENGNEW > ENGPREV when NSPREV doesn't override)
        assert output_data["global"]["version"] == "25.1.200"

        # Should have NSPREV database host (precedence: NSPREV > ENGNEW > ENGPREV)
        assert output_data["config"]["database"]["host"] == "nsprev-db.example.com"

        # Should have ENGNEW pool_size (new feature)
        assert output_data["config"]["database"]["pool_size"] == 10

        # Should have ENGNEW monitoring (new feature)
        assert "monitoring" in output_data["config"]
        assert output_data["config"]["monitoring"]["enabled"] is True

    def test_migrate_error_handling(self):
        """Test error handling in migrate command."""
        # Test with non-existent file
        result = self.runner.invoke(
            migrate,
            [
                "nonexistent.yaml",
                self.engprev_file,
                self.engnew_file,
            ],
        )

        assert result.exit_code == 2  # Click returns 2 for missing arguments
        assert "does not exist" in result.output

    def test_migrate_progress_display(self):
        """Test that progress is displayed during processing."""
        result = self.runner.invoke(
            migrate,
            [
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
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
                self.nsprev_file,
                self.engprev_file,
                self.engnew_file,
            ],
        )

        assert result.exit_code == 0
        assert "CVPilot Migration Workflow Successful" in result.output
        assert "Stage 1: NSPREV + ENGPREV" in result.output
        assert "Stage 2: diff + ENGNEW" in result.output
