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
            # Normalize data to fix annotations formatting issues
            normalized_data = self._normalize_annotations_lists(data)
            with open(file_path, "w", encoding="utf-8") as file:
                self.yaml.dump(normalized_data, file)
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

    def _normalize_annotations_lists(self, data):
        """
        Normalize annotations lists to ensure proper YAML formatting.

        Splits multi-key dictionaries in annotations lists into separate single-key dictionaries
        to prevent YAML formatting issues where list items lose their dash prefixes.

        Args:
            data: Data structure to normalize

        Returns:
            Normalized data structure
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key == "annotations" and isinstance(value, list):
                    # Normalize annotations list
                    result[key] = self._normalize_annotation_list(value)
                else:
                    # Recursively process nested structures
                    result[key] = self._normalize_annotations_lists(value)
            return result
        elif isinstance(data, list):
            return [self._normalize_annotations_lists(item) for item in data]
        else:
            return data

    def _normalize_annotation_list(self, annotations_list):
        """
        Normalize a single annotations list.

        Args:
            annotations_list: List of annotation dictionaries

        Returns:
            Normalized list with single-key dictionaries
        """
        if not isinstance(annotations_list, list):
            return annotations_list

        normalized = []
        for item in annotations_list:
            if isinstance(item, dict):
                # Split multi-key dictionaries into separate single-key dictionaries
                for key, value in item.items():
                    normalized.append({key: value})
            else:
                normalized.append(item)

        return normalized
