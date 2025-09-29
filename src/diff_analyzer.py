"""Template comparison and structural difference analysis."""

from typing import Any, Dict, List, Set


class DiffAnalyzer:
    """Analyze structural differences between YAML template versions."""

    def __init__(self) -> None:
        """Initialize the diff analyzer."""
        pass

    def find_deleted_paths(self, old_template: Dict[str, Any], new_template: Dict[str, Any]) -> List[str]:
        """Find paths that exist in old template but not in new template.

        Args:
            old_template: The V_OLD template dictionary.
            new_template: The V_NEW template dictionary.

        Returns:
            List of dot-notation paths that were deleted.
        """
        old_paths = self._get_all_paths(old_template)
        new_paths = self._get_all_paths(new_template)
        deleted_paths = old_paths - new_paths
        return sorted(list(deleted_paths))

    def find_added_paths(self, old_template: Dict[str, Any], new_template: Dict[str, Any]) -> List[str]:
        """Find paths that exist in new template but not in old template.

        Args:
            old_template: The V_OLD template dictionary.
            new_template: The V_NEW template dictionary.

        Returns:
            List of dot-notation paths that were added.
        """
        old_paths = self._get_all_paths(old_template)
        new_paths = self._get_all_paths(new_template)
        added_paths = new_paths - old_paths
        return sorted(list(added_paths))

    def find_structural_changes(self, old_template: Dict[str, Any], new_template: Dict[str, Any]) -> Dict[str, str]:
        """Find paths where the data type or structure changed between templates.

        Args:
            old_template: The V_OLD template dictionary.
            new_template: The V_NEW template dictionary.

        Returns:
            Dictionary mapping path to change description.
        """
        structural_changes: Dict[str, str] = {}
        old_paths = self._get_all_paths(old_template)
        new_paths = self._get_all_paths(new_template)

        # Check common paths for type changes
        common_paths = old_paths & new_paths
        for path in common_paths:
            old_value = self.get_nested_value(old_template, path)
            new_value = self.get_nested_value(new_template, path)

            old_type = type(old_value).__name__
            new_type = type(new_value).__name__

            if old_type != new_type:
                structural_changes[path] = f"Type changed from {old_type} to {new_type}"
            elif isinstance(old_value, dict) and isinstance(new_value, dict):
                # Check for structural changes in nested dictionaries
                old_keys = set(old_value.keys())
                new_keys = set(new_value.keys())
                if old_keys != new_keys:
                    removed_keys = old_keys - new_keys
                    added_keys = new_keys - old_keys
                    if removed_keys or added_keys:
                        changes = []
                        if removed_keys:
                            changes.append(f"removed keys: {sorted(removed_keys)}")
                        if added_keys:
                            changes.append(f"added keys: {sorted(added_keys)}")
                        structural_changes[path] = f"Structure changed - {', '.join(changes)}"

        return structural_changes

    def get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value at a dot-notation path in nested dictionary.

        Args:
            data: Dictionary to traverse.
            path: Dot-notation path (e.g., 'service.api.port').

        Returns:
            Value at the specified path.

        Raises:
            KeyError: If path doesn't exist.
            TypeError: If intermediate path is not a dictionary.
        """
        if not path:
            return data

        # Try to find the value using context-aware traversal
        result = self._traverse_path_contextual(data, path)
        if result is not None:
            return result

        # Fallback to simple splitting if contextual traversal fails
        keys = path.split('.')
        current = data

        for i, key in enumerate(keys):
            if not isinstance(current, dict):
                current_path = '.'.join(keys[:i])
                raise TypeError(f"Cannot traverse path '{path}': '{current_path}' is not a dictionary")

            if key not in current:
                raise KeyError(f"Path '{path}' not found: key '{key}' missing")

            current = current[key]

        return current

    def _traverse_path_contextual(self, data: Dict[str, Any], target_path: str) -> Any:
        """Traverse path using context-aware algorithm that handles special characters.

        This method recursively searches the data structure to find the target path,
        handling keys that contain special characters like dots and slashes.

        Args:
            data: Dictionary to search.
            target_path: The path we're looking for.

        Returns:
            The value if found, None if not found.
        """
        def _search_recursive(current_data: Dict[str, Any], current_path: str = "") -> Any:
            if current_path == target_path:
                return current_data

            if not isinstance(current_data, dict):
                return None

            for key, value in current_data.items():
                new_path = f"{current_path}.{key}" if current_path else key

                # Check if this path matches our target
                if new_path == target_path:
                    return value

                # If target path starts with this path, recurse deeper
                if target_path.startswith(new_path + ".") and isinstance(value, dict):
                    result = _search_recursive(value, new_path)
                    if result is not None:
                        return result

            return None

        return _search_recursive(data)

    def set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value at a dot-notation path in nested dictionary.

        Args:
            data: Dictionary to modify.
            path: Dot-notation path (e.g., 'service.api.port').
            value: Value to set.

        Raises:
            TypeError: If intermediate path is not a dictionary.
            ValueError: If path is empty.
        """
        if not path:
            raise ValueError("Path cannot be empty")

        keys = path.split('.')
        current = data

        # Navigate to parent of target key
        for i, key in enumerate(keys[:-1]):
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current_path = '.'.join(keys[:i+1])
                raise TypeError(f"Cannot set path '{path}': '{current_path}' is not a dictionary")
            current = current[key]

        # Set the final value
        final_key = keys[-1]
        current[final_key] = value

    def path_exists(self, data: Dict[str, Any], path: str) -> bool:
        """Check if a dot-notation path exists in the dictionary.

        Args:
            data: Dictionary to check.
            path: Dot-notation path to verify.

        Returns:
            True if path exists, False otherwise.
        """
        try:
            self.get_nested_value(data, path)
            return True
        except (KeyError, TypeError):
            return False

    def extract_custom_data(self, golden_config: Dict[str, Any], template_old: Dict[str, Any]) -> Dict[str, Any]:
        """Extract custom configuration data by comparing golden config with old template.

        Args:
            golden_config: The V_OLD golden configuration with custom values.
            template_old: The V_OLD template baseline.

        Returns:
            Dictionary mapping paths to custom values that differ from template.
        """
        custom_data: Dict[str, Any] = {}
        self._extract_custom_data_recursive(golden_config, template_old, custom_data, "")
        return custom_data

    def _extract_custom_data_recursive(
        self,
        golden: Dict[str, Any],
        template: Dict[str, Any],
        custom_data: Dict[str, Any],
        prefix: str
    ) -> None:
        """Recursively extract custom data, avoiding parent/child duplication.

        Args:
            golden: Current level of golden config.
            template: Current level of template config.
            custom_data: Dictionary to populate with custom data.
            prefix: Current path prefix.
        """
        for key, golden_value in golden.items():
            current_path = f"{prefix}.{key}" if prefix else key

            if key not in template:
                # Key doesn't exist in template - it's completely custom
                custom_data[current_path] = golden_value
            elif isinstance(golden_value, dict) and isinstance(template[key], dict):
                # Both are dictionaries - recurse deeper, but also check if the dict as a whole differs
                # Only include the parent dict if it has structural differences beyond just child values
                self._extract_custom_data_recursive(golden_value, template[key], custom_data, current_path)
            else:
                # Leaf values or type mismatch - compare directly
                if golden_value != template[key]:
                    custom_data[current_path] = golden_value

    def _get_all_paths(self, data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Recursively get all dot-notation paths in a nested dictionary.

        Args:
            data: Dictionary to traverse.
            prefix: Current path prefix.

        Returns:
            Set of all paths in the dictionary.
        """
        paths: Set[str] = set()

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key

            # Always add the current path
            paths.add(current_path)

            # If value is a dict, recursively get nested paths
            if isinstance(value, dict) and value:  # Don't recurse into empty dicts
                nested_paths = self._get_all_paths(value, current_path)
                paths.update(nested_paths)

        return paths

    def compare_values_deep(self, value1: Any, value2: Any) -> bool:
        """Deep comparison of two values, handling nested structures.

        Args:
            value1: First value to compare.
            value2: Second value to compare.

        Returns:
            True if values are equivalent, False otherwise.
        """
        if type(value1) != type(value2):
            return False

        if isinstance(value1, dict) and isinstance(value2, dict):
            if set(value1.keys()) != set(value2.keys()):
                return False
            return all(self.compare_values_deep(value1[k], value2[k]) for k in value1.keys())

        elif isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return False
            return all(self.compare_values_deep(v1, v2) for v1, v2 in zip(value1, value2))

        else:
            return value1 == value2

    def get_type_description(self, value: Any) -> str:
        """Get a human-readable description of a value's type and structure.

        Args:
            value: Value to describe.

        Returns:
            String description of the value type.
        """
        if isinstance(value, dict):
            if not value:
                return "empty dictionary"
            return f"dictionary with {len(value)} key(s): {sorted(value.keys())}"
        elif isinstance(value, list):
            if not value:
                return "empty list"
            return f"list with {len(value)} item(s)"
        elif value is None:
            return "null"
        else:
            return f"{type(value).__name__}: {value}"
