"""Tests for YAML processor module."""

import os
import tempfile

import pytest

from src.yaml_processor import YAMLProcessor


class TestYAMLProcessor:
    """Test cases for YAMLProcessor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = YAMLProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_valid_yaml_file(self) -> None:
        """Test loading a valid YAML file."""
        yaml_content = """
service:
  name: test-service
  port: 8080
  config:
    debug: true
    timeout: 30
"""
        file_path = os.path.join(self.temp_dir, "test.yaml")
        with open(file_path, "w") as f:
            f.write(yaml_content)

        result = self.processor.load_yaml_file(file_path)

        assert isinstance(result, dict)
        assert result["service"]["name"] == "test-service"
        assert result["service"]["port"] == 8080
        assert result["service"]["config"]["debug"] is True

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="YAML file not found"):
            self.processor.load_yaml_file("/nonexistent/file.yaml")

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises ValueError."""
        invalid_yaml = "invalid: yaml: content: ["
        file_path = os.path.join(self.temp_dir, "invalid.yaml")
        with open(file_path, "w") as f:
            f.write(invalid_yaml)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            self.processor.load_yaml_file(file_path)

    def test_load_empty_file(self) -> None:
        """Test loading empty file raises ValueError."""
        file_path = os.path.join(self.temp_dir, "empty.yaml")
        with open(file_path, "w") as f:
            f.write("")

        with pytest.raises(ValueError, match="YAML file is empty"):
            self.processor.load_yaml_file(file_path)

    def test_load_non_dict_yaml(self) -> None:
        """Test loading YAML that's not a dictionary raises TypeError."""
        list_yaml = "- item1\n- item2\n- item3"
        file_path = os.path.join(self.temp_dir, "list.yaml")
        with open(file_path, "w") as f:
            f.write(list_yaml)

        with pytest.raises(TypeError, match="YAML root must be a dictionary"):
            self.processor.load_yaml_file(file_path)

    def test_save_yaml_file(self) -> None:
        """Test saving dictionary to YAML file."""
        data = {
            "service": {
                "name": "test-service",
                "port": 8080,
                "config": {"debug": True, "timeout": 30},
            }
        }

        file_path = os.path.join(self.temp_dir, "output.yaml")
        self.processor.save_yaml_file(data, file_path)

        # Verify file exists and content
        assert os.path.exists(file_path)
        loaded_data = self.processor.load_yaml_file(file_path)
        assert loaded_data == data

    def test_save_yaml_file_creates_directories(self) -> None:
        """Test saving YAML file creates parent directories."""
        data = {"test": "value"}
        file_path = os.path.join(self.temp_dir, "subdir", "subsubdir", "output.yaml")

        self.processor.save_yaml_file(data, file_path)

        assert os.path.exists(file_path)
        loaded_data = self.processor.load_yaml_file(file_path)
        assert loaded_data == data

    def test_validate_yaml_structure_valid(self) -> None:
        """Test validating valid YAML structure."""
        valid_data = {
            "string_key": "value",
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True,
            "null_key": None,
            "nested": {"list": [1, 2, 3], "nested_dict": {"inner": "value"}},
        }

        assert self.processor.validate_yaml_structure(valid_data) is True

    def test_validate_yaml_structure_invalid_root(self) -> None:
        """Test validating non-dictionary root raises TypeError."""
        with pytest.raises(TypeError, match="Data must be a dictionary"):
            self.processor.validate_yaml_structure([1, 2, 3])  # type: ignore

    def test_validate_yaml_structure_invalid_key_type(self) -> None:
        """Test validating invalid key type raises ValueError."""
        invalid_data = {
            "valid_key": "value",
            ("invalid", "tuple", "key"): "value",  # type: ignore
        }

        with pytest.raises(ValueError, match="Unsupported key type"):
            self.processor.validate_yaml_structure(invalid_data)

    def test_check_file_permissions_read(self) -> None:
        """Test checking read permissions."""
        file_path = os.path.join(self.temp_dir, "test.yaml")
        with open(file_path, "w") as f:
            f.write("test: value")

        assert self.processor.check_file_permissions(file_path, "r") is True

    def test_check_file_permissions_write_existing(self) -> None:
        """Test checking write permissions for existing file."""
        file_path = os.path.join(self.temp_dir, "test.yaml")
        with open(file_path, "w") as f:
            f.write("test: value")

        assert self.processor.check_file_permissions(file_path, "w") is True

    def test_check_file_permissions_write_new(self) -> None:
        """Test checking write permissions for new file."""
        file_path = os.path.join(self.temp_dir, "new_file.yaml")

        assert self.processor.check_file_permissions(file_path, "w") is True
