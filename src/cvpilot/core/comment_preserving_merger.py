"""
Comment-preserving YAML merger.

This module implements a merger that preserves ENGNEW comments and structure
while applying only specific NSPREV values that differ from ENGPREV.
"""

import copy
from typing import Any, Dict, Optional
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq


class CommentPreservingMerger:
    """Merger that preserves comments and structure from ENGNEW while applying NSPREV values."""
    
    def __init__(self):
        """Initialize the merger."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 1000
        self.yaml.indent(mapping=2, sequence=4, offset=2)
    
    def merge_with_comments(
        self,
        engnew_file: str,
        diff_file: Dict[str, Any],
        output_file: str
    ) -> None:
        """
        Merge ENGNEW with DIFF while preserving comments and structure.
        
        Args:
            engnew_file: Path to ENGNEW YAML file (source of comments/structure)
            diff_file: DIFF data (NSPREV customizations to apply)
            output_file: Path to output file
        """
        # Load ENGNEW with comments preserved
        with open(engnew_file, encoding="utf-8") as f:
            engnew_data = self.yaml.load(f)
        
        # Apply DIFF values to ENGNEW structure
        result = self._apply_diff_to_engnew(engnew_data, diff_file)
        
        # Save with comments preserved
        with open(output_file, "w", encoding="utf-8") as f:
            self.yaml.dump(result, f)
    
    def _apply_diff_to_engnew(
        self,
        engnew_data: CommentedMap,
        diff_data: Dict[str, Any]
    ) -> CommentedMap:
        """
        Apply DIFF values to ENGNEW structure while preserving comments.
        
        Args:
            engnew_data: ENGNEW data with comments
            diff_data: DIFF data to apply
            
        Returns:
            ENGNEW data with DIFF values applied and comments preserved
        """
        result = copy.deepcopy(engnew_data)
        
        # Apply DIFF values recursively
        self._apply_diff_recursive(result, diff_data, "")
        
        return result
    
    def _apply_diff_recursive(
        self,
        engnew_obj: Any,
        diff_obj: Any,
        path: str
    ) -> None:
        """
        Recursively apply DIFF values to ENGNEW structure.
        
        Args:
            engnew_obj: ENGNEW object (CommentedMap/CommentedSeq)
            diff_obj: DIFF object to apply
            path: Current path for debugging
        """
        if isinstance(diff_obj, dict) and isinstance(engnew_obj, (CommentedMap, dict)):
            # Both are dictionaries - merge recursively
            for key, diff_value in diff_obj.items():
                if key in engnew_obj:
                    # Key exists in ENGNEW - apply DIFF value
                    if isinstance(diff_value, dict) and isinstance(engnew_obj[key], (CommentedMap, dict)):
                        # Both are dicts - recurse
                        self._apply_diff_recursive(engnew_obj[key], diff_value, f"{path}.{key}")
                    else:
                        # Apply DIFF value (scalar or different type)
                        engnew_obj[key] = copy.deepcopy(diff_value)
                else:
                    # Key doesn't exist in ENGNEW - add from DIFF
                    engnew_obj[key] = copy.deepcopy(diff_value)
        
        elif isinstance(diff_obj, list) and isinstance(engnew_obj, (CommentedSeq, list)):
            # Both are lists - apply DIFF values by index
            for i, diff_item in enumerate(diff_obj):
                if i < len(engnew_obj):
                    # Index exists in ENGNEW - apply DIFF item
                    if isinstance(diff_item, dict) and isinstance(engnew_obj[i], (CommentedMap, dict)):
                        # Both are dicts - recurse
                        self._apply_diff_recursive(engnew_obj[i], diff_item, f"{path}[{i}]")
                    else:
                        # Apply DIFF item (scalar or different type)
                        engnew_obj[i] = copy.deepcopy(diff_item)
                else:
                    # Index doesn't exist in ENGNEW - add from DIFF
                    engnew_obj.append(copy.deepcopy(diff_item))
        
        # For scalar values or type mismatches, DIFF value is already applied above
    
    def load_with_comments(self, file_path: str):
        """Load YAML file with comments preserved."""
        with open(file_path, encoding="utf-8") as f:
            return self.yaml.load(f)
    
    def save_with_comments(self, data, file_path: str) -> None:
        """Save YAML data with comments preserved."""
        with open(file_path, "w", encoding="utf-8") as f:
            self.yaml.dump(data, f)
