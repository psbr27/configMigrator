"""
Tests for helper utility functions.
"""

import os
import tempfile
from pathlib import Path

from cvpilot.utils.helpers import (
    format_file_size,
    get_file_info,
    validate_file_paths,
)


class TestHelperFunctions:
    """Test helper utility functions."""

    def test_get_file_info_existing_file(self):
        """Test get_file_info with existing file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_file = f.name

        try:
            info = get_file_info(temp_file)

            assert info["name"] == os.path.basename(temp_file)
            assert info["size"] > 0
            assert info["exists"] is True
            assert info["is_file"] is True
        finally:
            os.unlink(temp_file)

    def test_get_file_info_nonexistent_file(self):
        """Test get_file_info with non-existent file."""
        info = get_file_info("nonexistent_file.txt")

        assert info["name"] == "nonexistent_file.txt"
        assert info["size"] == 0
        assert info["exists"] is False
        assert info["is_file"] is False

    def test_get_file_info_directory(self):
        """Test get_file_info with directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            info = get_file_info(temp_dir)

            assert info["name"] == os.path.basename(temp_dir)
            assert info["size"] > 0
            assert info["exists"] is True
            assert info["is_file"] is False

    def test_get_file_info_empty_file(self):
        """Test get_file_info with empty file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            info = get_file_info(temp_file)

            assert info["name"] == os.path.basename(temp_file)
            assert info["size"] == 0
            assert info["exists"] is True
            assert info["is_file"] is True
        finally:
            os.unlink(temp_file)

    def test_format_file_size_bytes(self):
        """Test format_file_size with bytes."""
        assert format_file_size(0) == "0.0 B"
        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_format_file_size_kilobytes(self):
        """Test format_file_size with kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(2048) == "2.0 KB"
        assert format_file_size(10240) == "10.0 KB"

    def test_format_file_size_megabytes(self):
        """Test format_file_size with megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1.5) == "1.5 MB"
        assert format_file_size(1024 * 1024 * 10) == "10.0 MB"

    def test_format_file_size_gigabytes(self):
        """Test format_file_size with gigabytes."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1024 * 1024 * 1024 * 2.5) == "2.5 GB"

    def test_format_file_size_terabytes(self):
        """Test format_file_size with terabytes."""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"
        assert format_file_size(1024 * 1024 * 1024 * 1024 * 5) == "5.0 TB"

    def test_format_file_size_large_values(self):
        """Test format_file_size with very large values."""
        # Test values that would overflow to TB
        large_value = 1024 * 1024 * 1024 * 1024 * 10
        result = format_file_size(large_value)
        assert "TB" in result

    def test_validate_file_paths_all_valid(self):
        """Test validate_file_paths with all valid files."""
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            temp_file1 = f1.name
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            temp_file2 = f2.name

        try:
            is_valid, errors = validate_file_paths([temp_file1, temp_file2])

            assert is_valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_file1)
            os.unlink(temp_file2)

    def test_validate_file_paths_some_invalid(self):
        """Test validate_file_paths with some invalid files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            is_valid, errors = validate_file_paths(
                [
                    temp_file,
                    "nonexistent1.txt",
                    "nonexistent2.txt",
                ]
            )

            assert is_valid is False
            assert len(errors) == 2
            assert "File not found: nonexistent1.txt" in errors
            assert "File not found: nonexistent2.txt" in errors
        finally:
            os.unlink(temp_file)

    def test_validate_file_paths_all_invalid(self):
        """Test validate_file_paths with all invalid files."""
        is_valid, errors = validate_file_paths(
            [
                "nonexistent1.txt",
                "nonexistent2.txt",
                "nonexistent3.txt",
            ]
        )

        assert is_valid is False
        assert len(errors) == 3
        assert all("File not found:" in error for error in errors)

    def test_validate_file_paths_directory_instead_of_file(self):
        """Test validate_file_paths with directory instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_valid, errors = validate_file_paths([temp_dir])

            assert is_valid is False
            assert len(errors) == 1
            assert "Not a file:" in errors[0]

    def test_validate_file_paths_mixed_validity(self):
        """Test validate_file_paths with mixed valid and invalid files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                is_valid, errors = validate_file_paths(
                    [
                        temp_file,  # Valid file
                        "nonexistent.txt",  # Invalid file
                        temp_dir,  # Directory (invalid)
                    ]
                )

                assert is_valid is False
                assert len(errors) == 2
                assert "File not found: nonexistent.txt" in errors
                assert any("Not a file:" in error for error in errors)
        finally:
            os.unlink(temp_file)

    def test_validate_file_paths_empty_list(self):
        """Test validate_file_paths with empty list."""
        is_valid, errors = validate_file_paths([])

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_file_paths_single_valid_file(self):
        """Test validate_file_paths with single valid file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            is_valid, errors = validate_file_paths([temp_file])

            assert is_valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_file)

    def test_validate_file_paths_single_invalid_file(self):
        """Test validate_file_paths with single invalid file."""
        is_valid, errors = validate_file_paths(["nonexistent.txt"])

        assert is_valid is False
        assert len(errors) == 1
        assert "File not found: nonexistent.txt" in errors[0]

    def test_get_file_info_with_path_object(self):
        """Test get_file_info with Path object."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            # Test with string path
            info1 = get_file_info(temp_file)

            # Test with Path object
            path_obj = Path(temp_file)
            info2 = get_file_info(str(path_obj))

            assert info1 == info2
        finally:
            os.unlink(temp_file)

    def test_format_file_size_edge_cases(self):
        """Test format_file_size with edge cases."""
        # Test exactly 1 KB
        assert format_file_size(1024) == "1.0 KB"

        # Test just under 1 KB
        assert format_file_size(1023) == "1023.0 B"

        # Test exactly 1 MB
        assert format_file_size(1024 * 1024) == "1.0 MB"

        # Test just under 1 MB
        assert format_file_size(1024 * 1024 - 1) == "1024.0 KB"

    def test_get_file_info_unicode_filename(self):
        """Test get_file_info with unicode filename."""
        unicode_name = "测试文件.txt"
        info = get_file_info(unicode_name)

        assert info["name"] == unicode_name
        assert info["exists"] is False
        assert info["is_file"] is False

    def test_validate_file_paths_unicode_filenames(self):
        """Test validate_file_paths with unicode filenames."""
        unicode_files = ["测试文件1.txt", "测试文件2.txt"]
        is_valid, errors = validate_file_paths(unicode_files)

        assert is_valid is False
        assert len(errors) == 2
        assert all("File not found:" in error for error in errors)
