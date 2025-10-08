"""
Test cases for YAMLParser.
"""

import os
import tempfile

import pytest

from cvpilot.core.parser import YAMLParser


class TestYAMLParser:
    """Test cases for YAMLParser."""

    def test_load_valid_yaml(self):
        """Test loading a valid YAML file."""
        test_data = {
            "global": {
                "sitename": "test-site",
                "version": "25.1.102",
            },
            "api": {
                "replicas": 2,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(test_data, f)
            temp_file = f.name

        try:
            parser = YAMLParser()
            result = parser.load_yaml_file(temp_file)
            assert result == test_data
        finally:
            os.unlink(temp_file)

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file."""
        parser = YAMLParser()
        with pytest.raises(FileNotFoundError):
            parser.load_yaml_file("nonexistent.yaml")

    def test_load_invalid_yaml(self):
        """Test loading an invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name

        try:
            parser = YAMLParser()
            with pytest.raises(ValueError):
                parser.load_yaml_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_validate_yaml_syntax_valid(self):
        """Test validating valid YAML syntax."""
        test_data = {"key": "value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(test_data, f)
            temp_file = f.name

        try:
            parser = YAMLParser()
            assert parser.validate_yaml_syntax(temp_file) is True
        finally:
            os.unlink(temp_file)

    def test_validate_yaml_syntax_invalid(self):
        """Test validating invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name

        try:
            parser = YAMLParser()
            assert parser.validate_yaml_syntax(temp_file) is False
        finally:
            os.unlink(temp_file)

    def test_validate_all_files_success(self):
        """Test validating multiple valid files."""
        test_data = {"key": "value"}

        temp_files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    import yaml

                    yaml.dump(test_data, f)
                    temp_files.append(f.name)

            parser = YAMLParser()
            is_valid, error = parser.validate_all_files(temp_files)
            assert is_valid is True
            assert error is None
        finally:
            for temp_file in temp_files:
                os.unlink(temp_file)

    def test_validate_all_files_failure(self):
        """Test validating files with one invalid file."""
        test_data = {"key": "value"}

        temp_files = []
        try:
            # Create 2 valid files
            for i in range(2):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    import yaml

                    yaml.dump(test_data, f)
                    temp_files.append(f.name)

            # Create 1 invalid file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write("invalid: yaml: content: [")
                temp_files.append(f.name)

            parser = YAMLParser()
            is_valid, error = parser.validate_all_files(temp_files)
            assert is_valid is False
            assert "Invalid YAML syntax" in error
        finally:
            for temp_file in temp_files:
                os.unlink(temp_file)

    def test_save_yaml_file(self):
        """Test saving YAML data to file."""
        test_data = {
            "global": {
                "sitename": "test-site",
                "version": "25.1.102",
            },
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            temp_file = f.name

        try:
            parser = YAMLParser()
            parser.save_yaml_file(test_data, temp_file)

            # Verify the file was created and contains the data
            assert os.path.exists(temp_file)

            # Load and verify content
            with open(temp_file) as f:
                content = f.read()
                assert "sitename" in content
                assert "test-site" in content
        finally:
            os.unlink(temp_file)
