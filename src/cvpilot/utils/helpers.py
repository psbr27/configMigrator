"""
Helper utility functions for config migrator.
"""

from pathlib import Path
from typing import Any, Dict, List


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    return {
        "name": path.name,
        "size": path.stat().st_size if path.exists() else 0,
        "exists": path.exists(),
        "is_file": path.is_file(),
    }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def validate_file_paths(file_paths: List[str]) -> tuple[bool, List[str]]:
    """
    Validate that all file paths exist and are files.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Tuple of (all_valid, error_messages)
    """
    errors = []

    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            errors.append(f"File not found: {file_path}")
        elif not path.is_file():
            errors.append(f"Not a file: {file_path}")

    return len(errors) == 0, errors
