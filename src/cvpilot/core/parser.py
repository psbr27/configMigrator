"""
YAML file parser with validation.

Handles loading and basic syntax validation of YAML files.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from ruamel.yaml import YAML


class YAMLParser:
    """Simple YAML parser with error handling using ruamel.yaml."""

    def __init__(self):
        """Initialize ruamel.yaml instance with proper settings."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 1000
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse YAML file with error handling.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed YAML data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML syntax is invalid
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                data = self.yaml.load(file)
                if data is None:
                    return {}
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Invalid YAML syntax in {file_path}: {e}")

    def validate_yaml_syntax(self, file_path: str) -> bool:
        """
        Basic YAML syntax validation.

        Args:
            file_path: Path to the YAML file

        Returns:
            True if YAML syntax is valid, False otherwise
        """
        try:
            self.load_yaml_file(file_path)
            return True
        except (ValueError, FileNotFoundError):
            return False

    def save_yaml_file(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Save data to YAML file with proper formatting.

        Args:
            data: Dictionary to save
            file_path: Output file path
        """
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                self.yaml.dump(data, file)
        except Exception as e:
            raise ValueError(f"Error writing to {file_path}: {e}")

    def validate_all_files(self, file_paths: list[str]) -> tuple[bool, Optional[str]]:
        """
        Validate syntax of all input files.

        Args:
            file_paths: List of file paths to validate

        Returns:
            Tuple of (all_valid, error_message)
        """
        for file_path in file_paths:
            if not Path(file_path).exists():
                return False, f"File not found: {file_path}"

            if not self.validate_yaml_syntax(file_path):
                return False, f"Invalid YAML syntax in: {file_path}"

        return True, None
