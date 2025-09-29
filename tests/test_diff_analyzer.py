"""Tests for diff analyzer module."""

import pytest

from src.diff_analyzer import DiffAnalyzer


class TestDiffAnalyzer:
    """Test cases for DiffAnalyzer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.analyzer = DiffAnalyzer()

    def test_find_deleted_paths(self) -> None:
        """Test finding paths deleted between templates."""
        old_template = {
            "service": {
                "name": "test",
                "port": 8080,
                "deprecated_setting": "value"
            },
            "removed_section": {
                "config": "value"
            }
        }

        new_template = {
            "service": {
                "name": "test",
                "port": 9000
            }
        }

        deleted_paths = self.analyzer.find_deleted_paths(old_template, new_template)

        expected_deleted = [
            "removed_section",
            "removed_section.config",
            "service.deprecated_setting"
        ]
        assert sorted(deleted_paths) == sorted(expected_deleted)

    def test_find_added_paths(self) -> None:
        """Test finding paths added between templates."""
        old_template = {
            "service": {
                "name": "test",
                "port": 8080
            }
        }

        new_template = {
            "service": {
                "name": "test",
                "port": 8080,
                "new_setting": "value"
            },
            "new_section": {
                "config": "value"
            }
        }

        added_paths = self.analyzer.find_added_paths(old_template, new_template)

        expected_added = [
            "new_section",
            "new_section.config",
            "service.new_setting"
        ]
        assert sorted(added_paths) == sorted(expected_added)

    def test_find_structural_changes(self) -> None:
        """Test finding structural changes between templates."""
        old_template = {
            "service": {
                "timeout": 30,
                "config": {
                    "debug": True
                }
            }
        }

        new_template = {
            "service": {
                "timeout": "30s",  # Type change: int to str
                "config": [         # Type change: dict to list
                    {"name": "debug", "value": True}
                ]
            }
        }

        changes = self.analyzer.find_structural_changes(old_template, new_template)

        assert "service.timeout" in changes
        assert "Type changed from int to str" in changes["service.timeout"]
        assert "service.config" in changes
        assert "Type changed from dict to list" in changes["service.config"]

    def test_get_nested_value(self) -> None:
        """Test getting values from nested paths."""
        data = {
            "service": {
                "api": {
                    "port": 8080,
                    "host": "localhost"
                }
            }
        }

        assert self.analyzer.get_nested_value(data, "service.api.port") == 8080
        assert self.analyzer.get_nested_value(data, "service.api.host") == "localhost"

    def test_get_nested_value_missing_path(self) -> None:
        """Test getting value from non-existent path raises KeyError."""
        data = {"service": {"api": {"port": 8080}}}

        with pytest.raises(KeyError, match="Path 'service.api.missing' not found"):
            self.analyzer.get_nested_value(data, "service.api.missing")

    def test_get_nested_value_invalid_intermediate_path(self) -> None:
        """Test getting value through non-dict intermediate raises TypeError."""
        data = {"service": {"port": 8080}}  # port is int, not dict

        with pytest.raises(TypeError, match="is not a dictionary"):
            self.analyzer.get_nested_value(data, "service.port.invalid")

    def test_set_nested_value(self) -> None:
        """Test setting values at nested paths."""
        data = {
            "service": {
                "api": {
                    "port": 8080
                }
            }
        }

        self.analyzer.set_nested_value(data, "service.api.port", 9000)
        assert data["service"]["api"]["port"] == 9000

        # Test creating new nested path
        self.analyzer.set_nested_value(data, "service.database.host", "localhost")
        assert data["service"]["database"]["host"] == "localhost"

    def test_set_nested_value_empty_path(self) -> None:
        """Test setting value with empty path raises ValueError."""
        data = {"test": "value"}

        with pytest.raises(ValueError, match="Path cannot be empty"):
            self.analyzer.set_nested_value(data, "", "value")

    def test_path_exists(self) -> None:
        """Test checking if paths exist."""
        data = {
            "service": {
                "api": {
                    "port": 8080
                }
            }
        }

        assert self.analyzer.path_exists(data, "service") is True
        assert self.analyzer.path_exists(data, "service.api") is True
        assert self.analyzer.path_exists(data, "service.api.port") is True
        assert self.analyzer.path_exists(data, "service.missing") is False
        assert self.analyzer.path_exists(data, "missing") is False

    def test_extract_custom_data(self) -> None:
        """Test extracting custom data from golden config."""
        golden_config = {
            "service": {
                "name": "my-service",  # Custom value
                "port": 8080,         # Same as template
                "timeout": 60         # Custom value
            },
            "custom_section": {       # Completely custom
                "setting": "value"
            }
        }

        template_old = {
            "service": {
                "name": "default-service",
                "port": 8080,
                "timeout": 30
            }
        }

        custom_data = self.analyzer.extract_custom_data(golden_config, template_old)

        expected_custom = {
            "service.name": "my-service",
            "service.timeout": 60,
            "custom_section": {"setting": "value"}  # Only the parent object, not individual children
        }

        assert custom_data == expected_custom

    def test_compare_values_deep(self) -> None:
        """Test deep comparison of values."""
        # Test identical values
        assert self.analyzer.compare_values_deep(
            {"a": {"b": [1, 2, 3]}},
            {"a": {"b": [1, 2, 3]}}
        ) is True

        # Test different types
        assert self.analyzer.compare_values_deep(
            {"a": "string"},
            {"a": 123}
        ) is False

        # Test different dict keys
        assert self.analyzer.compare_values_deep(
            {"a": 1, "b": 2},
            {"a": 1, "c": 2}
        ) is False

        # Test different list lengths
        assert self.analyzer.compare_values_deep(
            [1, 2, 3],
            [1, 2]
        ) is False

    def test_get_type_description(self) -> None:
        """Test getting type descriptions."""
        assert "empty dictionary" in self.analyzer.get_type_description({})
        assert "empty list" in self.analyzer.get_type_description([])
        assert "null" in self.analyzer.get_type_description(None)
        assert "dictionary with 2 key(s)" in self.analyzer.get_type_description({"a": 1, "b": 2})
        assert "list with 3 item(s)" in self.analyzer.get_type_description([1, 2, 3])
        assert "str: hello" in self.analyzer.get_type_description("hello")