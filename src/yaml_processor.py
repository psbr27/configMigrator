"""YAML processing utilities with format preservation."""

import os
from pathlib import Path
from typing import Any, Dict

from ruamel.yaml import YAML


class YAMLProcessor:
    """Handle YAML file operations with error handling and format preservation."""

    def __init__(self) -> None:
        """Initialize YAML processor with ruamel.yaml for format preservation."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.map_indent = 2
        self.yaml.sequence_indent = 4
        self.yaml.sequence_dash_offset = 2

    def load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load YAML file into dictionary with comprehensive error handling.

        Args:
            file_path: Path to the YAML file to load.

        Returns:
            Dictionary containing the parsed YAML data.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            PermissionError: If file cannot be read due to permissions.
            ValueError: If YAML syntax is invalid or file is empty.
            TypeError: If file content is not a dictionary.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with open(path, encoding="utf-8") as file:
                data = self.yaml.load(file)
        except PermissionError as e:
            raise PermissionError(f"Cannot read file {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Invalid YAML syntax in {file_path}: {e}") from e

        if data is None:
            raise ValueError(f"YAML file is empty: {file_path}")

        if not isinstance(data, dict):
            raise TypeError(
                f"YAML root must be a dictionary, got {type(data).__name__}: {file_path}"
            )

        return data

    def save_yaml_file(self, data: Dict[str, Any], file_path: str) -> None:
        """Save dictionary to YAML file with format preservation.

        Args:
            data: Dictionary to save as YAML.
            file_path: Output file path.

        Raises:
            PermissionError: If file cannot be written due to permissions.
            OSError: If there are other file system issues.
            ValueError: If data cannot be serialized to YAML.
        """
        path = Path(file_path)

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as file:
                self.yaml.dump(data, file)
        except PermissionError as e:
            raise PermissionError(f"Cannot write to file {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to serialize data to YAML: {e}") from e

    def validate_yaml_structure(self, data: Dict[str, Any]) -> bool:
        """Validate basic YAML structure requirements.

        Args:
            data: Dictionary to validate.

        Returns:
            True if structure is valid.

        Raises:
            TypeError: If data is not a dictionary.
            ValueError: If structure contains unsupported types.
        """
        if not isinstance(data, dict):
            raise TypeError(f"Data must be a dictionary, got {type(data).__name__}")

        # Recursively validate structure
        self._validate_nested_structure(data, "root")
        return True

    def _validate_nested_structure(self, obj: Any, path: str) -> None:
        """Recursively validate nested YAML structure.

        Args:
            obj: Object to validate.
            path: Current path in the structure for error reporting.

        Raises:
            ValueError: If unsupported types are found.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, (str, int, float, bool)):
                    raise ValueError(
                        f"Unsupported key type {type(key).__name__} at {path}.{key}"
                    )
                self._validate_nested_structure(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._validate_nested_structure(item, f"{path}[{i}]")
        elif not isinstance(obj, (str, int, float, bool, type(None))):
            raise ValueError(f"Unsupported value type {type(obj).__name__} at {path}")

    def check_file_permissions(self, file_path: str, mode: str = "r") -> bool:
        """Check if file has required permissions.

        Args:
            file_path: Path to check.
            mode: Access mode ('r' for read, 'w' for write).

        Returns:
            True if file can be accessed with the specified mode.
        """
        try:
            if mode == "r":
                return os.access(file_path, os.R_OK)
            elif mode == "w":
                # Check if file exists and is writable, or if parent dir is writable
                if os.path.exists(file_path):
                    return os.access(file_path, os.W_OK)
                else:
                    parent_dir = os.path.dirname(file_path)
                    return os.access(parent_dir, os.W_OK) if parent_dir else True
            else:
                return False
        except OSError:
            return False


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Convenience function to load a YAML file.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Dictionary containing the parsed YAML data.
    """
    processor = YAMLProcessor()
    return processor.load_yaml_file(file_path)


def save_yaml_file(data: Dict[str, Any], file_path: str) -> None:
    """Convenience function to save data to a YAML file.

    Args:
        data: Dictionary to save.
        file_path: Output file path.
    """
    processor = YAMLProcessor()
    processor.save_yaml_file(data, file_path)


def validate_yaml_structure(data: Dict[str, Any]) -> bool:
    """Convenience function to validate YAML structure.

    Args:
        data: Dictionary to validate.

    Returns:
        True if structure is valid.
    """
    processor = YAMLProcessor()
    return processor.validate_yaml_structure(data)
