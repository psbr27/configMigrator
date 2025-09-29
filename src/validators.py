"""Input validation and output verification utilities."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .yaml_processor import YAMLProcessor
except ImportError:
    from yaml_processor import YAMLProcessor


class ConfigValidator:
    """Validate configuration files and migration inputs."""

    def __init__(self) -> None:
        """Initialize validator with YAML processor."""
        self.yaml_processor = YAMLProcessor()

    def validate_input_files(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str,
        migration_map_path: Optional[str] = None
    ) -> List[str]:
        """Validate all input files for migration.

        Args:
            golden_old_path: Path to V_OLD golden configuration.
            template_old_path: Path to V_OLD template.
            template_new_path: Path to V_NEW template.
            migration_map_path: Optional path to migration mapping file.

        Returns:
            List of validation error messages. Empty list if all valid.
        """
        errors: List[str] = []

        # Validate required YAML files
        yaml_files = {
            "Golden Config (V_OLD)": golden_old_path,
            "Template (V_OLD)": template_old_path,
            "Template (V_NEW)": template_new_path
        }

        for file_type, file_path in yaml_files.items():
            file_errors = self._validate_yaml_file(file_path, file_type)
            errors.extend(file_errors)

        # Validate optional migration map
        if migration_map_path:
            migration_errors = self._validate_migration_map_file(migration_map_path)
            errors.extend(migration_errors)

        # Validate file relationships if individual files are valid
        if not errors:
            relationship_errors = self._validate_file_relationships(
                golden_old_path, template_old_path, template_new_path
            )
            errors.extend(relationship_errors)

        return errors

    def validate_output_paths(self, output_config_path: str, output_log_path: str) -> List[str]:
        """Validate output file paths for writability.

        Args:
            output_config_path: Path for output configuration.
            output_log_path: Path for output log.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        for file_type, file_path in [("Output Config", output_config_path), ("Output Log", output_log_path)]:
            if not file_path:
                errors.append(f"{file_type} path cannot be empty")
                continue

            # Check if parent directory exists or can be created
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                try:
                    Path(parent_dir).mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError):
                    errors.append(f"Cannot create directory for {file_type}: {parent_dir}")
                    continue

            # Check write permissions
            if not self.yaml_processor.check_file_permissions(file_path, 'w'):
                errors.append(f"No write permission for {file_type}: {file_path}")

        return errors

    def validate_output_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate final merged configuration.

        Args:
            config: Final configuration dictionary to validate.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        try:
            # Validate basic structure
            self.yaml_processor.validate_yaml_structure(config)
        except (TypeError, ValueError) as e:
            errors.append(f"Invalid configuration structure: {e}")
            return errors

        # Check for empty configuration
        if not config:
            errors.append("Configuration is empty")

        # Validate configuration depth (prevent excessive nesting)
        max_depth = self._get_max_depth(config)
        if max_depth > 20:  # Arbitrary reasonable limit
            errors.append(f"Configuration nesting too deep ({max_depth} levels). Maximum recommended: 20")

        # Check for suspicious patterns
        suspicious_errors = self._check_suspicious_patterns(config)
        errors.extend(suspicious_errors)

        return errors

    def check_file_permissions(self, file_path: str, mode: str = 'r') -> bool:
        """Check file permissions wrapper.

        Args:
            file_path: Path to check.
            mode: Access mode ('r' for read, 'w' for write).

        Returns:
            True if file has required permissions.
        """
        return self.yaml_processor.check_file_permissions(file_path, mode)

    def validate_migration_map(self, migration_map: Dict[str, str]) -> List[str]:
        """Validate migration map structure and content.

        Args:
            migration_map: Dictionary mapping old paths to new paths.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        if not isinstance(migration_map, dict):
            errors.append("Migration map must be a dictionary")
            return errors

        # Validate path formats
        for old_path, new_path in migration_map.items():
            if not isinstance(old_path, str) or not isinstance(new_path, str):
                errors.append(f"Migration paths must be strings: {old_path} -> {new_path}")
                continue

            if not old_path or not new_path:
                errors.append(f"Migration paths cannot be empty: '{old_path}' -> '{new_path}'")
                continue

            # Check path format
            for path_type, path in [("old", old_path), ("new", new_path)]:
                if path.startswith('.') or path.endswith('.') or '..' in path:
                    errors.append(f"Invalid {path_type} path format: '{path}'")

        # Check for circular references
        circular_errors = self._check_circular_migrations(migration_map)
        errors.extend(circular_errors)

        return errors

    def _validate_yaml_file(self, file_path: str, file_type: str) -> List[str]:
        """Validate a single YAML file.

        Args:
            file_path: Path to the YAML file.
            file_type: Description of the file type for error messages.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        if not file_path:
            errors.append(f"{file_type} path cannot be empty")
            return errors

        # Check file existence
        if not os.path.exists(file_path):
            errors.append(f"{file_type} file not found: {file_path}")
            return errors

        if not os.path.isfile(file_path):
            errors.append(f"{file_type} path is not a file: {file_path}")
            return errors

        # Check read permissions
        if not self.check_file_permissions(file_path, 'r'):
            errors.append(f"No read permission for {file_type}: {file_path}")
            return errors

        # Validate YAML content
        try:
            data = self.yaml_processor.load_yaml_file(file_path)
            # Additional validation for specific file types
            if "template" in file_type.lower():
                template_errors = self._validate_template_structure(data, file_type)
                errors.extend(template_errors)
        except (FileNotFoundError, PermissionError, ValueError, TypeError) as e:
            errors.append(f"Invalid {file_type}: {e}")

        return errors

    def _validate_migration_map_file(self, migration_map_path: str) -> List[str]:
        """Validate migration map JSON file.

        Args:
            migration_map_path: Path to migration map file.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        if not os.path.exists(migration_map_path):
            errors.append(f"Migration map file not found: {migration_map_path}")
            return errors

        if not self.check_file_permissions(migration_map_path, 'r'):
            errors.append(f"No read permission for migration map: {migration_map_path}")
            return errors

        try:
            with open(migration_map_path, encoding='utf-8') as file:
                migration_data = json.load(file)

            # Validate structure
            if not isinstance(migration_data, dict):
                errors.append("Migration map must be a JSON object")
                return errors

            # Extract migration mappings (support both simple and complex formats)
            if "migrations" in migration_data:
                migration_map = migration_data["migrations"]
            else:
                migration_map = migration_data

            validation_errors = self.validate_migration_map(migration_map)
            errors.extend(validation_errors)

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in migration map: {e}")
        except OSError as e:
            errors.append(f"Cannot read migration map file: {e}")

        return errors

    def _validate_file_relationships(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str
    ) -> List[str]:
        """Validate relationships between input files.

        Args:
            golden_old_path: Path to golden config.
            template_old_path: Path to old template.
            template_new_path: Path to new template.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        try:
            golden_config = self.yaml_processor.load_yaml_file(golden_old_path)
            template_old = self.yaml_processor.load_yaml_file(template_old_path)
            template_new = self.yaml_processor.load_yaml_file(template_new_path)

            # Check if golden config is compatible with old template
            compatibility_errors = self._check_template_compatibility(golden_config, template_old)
            if compatibility_errors:
                errors.append(
                    f"Golden config incompatible with old template: {'; '.join(compatibility_errors)}"
                )

            # Check if templates have reasonable structural similarity
            similarity_errors = self._check_template_similarity(template_old, template_new)
            errors.extend(similarity_errors)

        except Exception as e:
            errors.append(f"Cannot validate file relationships: {e}")

        return errors

    def _validate_template_structure(self, data: Dict[str, Any], file_type: str) -> List[str]:
        """Validate template-specific structure requirements.

        Args:
            data: Template data to validate.
            file_type: Type of template for context.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        # Check for minimum expected structure
        if not data:
            errors.append(f"{file_type} cannot be empty")
            return errors

        # Templates should have some reasonable complexity
        if len(data) < 2:
            errors.append(f"{file_type} appears too simple (less than 2 top-level keys)")

        # Check for extremely large configurations
        total_paths = len(self._get_all_paths_simple(data))
        if total_paths > 10000:  # Arbitrary reasonable limit
            errors.append(f"{file_type} is extremely large ({total_paths} paths). Consider simplification.")

        return errors

    def _check_template_compatibility(self, golden_config: Dict[str, Any], template_old: Dict[str, Any]) -> List[str]:
        """Check basic compatibility between golden config and old template.

        Args:
            golden_config: Golden configuration data.
            template_old: Old template data.

        Returns:
            List of compatibility error messages.
        """
        errors: List[str] = []

        golden_paths = self._get_all_paths_simple(golden_config)
        template_paths = self._get_all_paths_simple(template_old)

        # Check if golden config has paths not in template
        extra_paths = golden_paths - template_paths
        if len(extra_paths) > len(golden_paths) * 0.5:  # More than 50% extra paths
            errors.append(f"Golden config has many paths not in template ({len(extra_paths)} extra)")

        return errors

    def _check_template_similarity(self, template_old: Dict[str, Any], template_new: Dict[str, Any]) -> List[str]:
        """Check structural similarity between template versions.

        Args:
            template_old: Old template data.
            template_new: New template data.

        Returns:
            List of similarity warning messages.
        """
        errors: List[str] = []

        old_paths = self._get_all_paths_simple(template_old)
        new_paths = self._get_all_paths_simple(template_new)

        # Calculate similarity
        common_paths = old_paths & new_paths
        total_unique_paths = len(old_paths | new_paths)

        if total_unique_paths > 0:
            similarity_ratio = len(common_paths) / total_unique_paths
            if similarity_ratio < 0.3:  # Less than 30% similarity
                errors.append(
                    f"Templates have low similarity ({similarity_ratio:.1%}). "
                    "Verify these are compatible versions."
                )

        return errors

    def _check_circular_migrations(self, migration_map: Dict[str, str]) -> List[str]:
        """Check for circular references in migration map.

        Args:
            migration_map: Migration mapping dictionary.

        Returns:
            List of circular reference error messages.
        """
        errors: List[str] = []
        visited = set()

        for start_path in migration_map:
            if start_path in visited:
                continue

            current_path = start_path
            path_chain: List[str] = []

            while current_path in migration_map:
                if current_path in path_chain:
                    cycle_start = path_chain.index(current_path)
                    cycle = path_chain[cycle_start:] + [current_path]
                    errors.append(f"Circular migration detected: {' -> '.join(cycle)}")
                    break

                path_chain.append(current_path)
                current_path = migration_map[current_path]

            visited.update(path_chain)

        return errors

    def _check_suspicious_patterns(self, config: Dict[str, Any]) -> List[str]:
        """Check for suspicious patterns in configuration.

        Args:
            config: Configuration to check.

        Returns:
            List of warning messages about suspicious patterns.
        """
        warnings: List[str] = []

        # Check for potential sensitive data
        sensitive_paths = self._find_sensitive_paths(config)
        if sensitive_paths:
            warnings.append(f"Potential sensitive data found in paths: {', '.join(sensitive_paths[:5])}")

        return warnings

    def _find_sensitive_paths(self, config: Dict[str, Any], prefix: str = "") -> List[str]:
        """Find paths that might contain sensitive data.

        Args:
            config: Configuration to scan.
            prefix: Current path prefix.

        Returns:
            List of potentially sensitive paths.
        """
        sensitive_keywords = ["password", "secret", "key", "token", "credential", "auth"]
        sensitive_paths: List[str] = []

        for key, value in config.items():
            current_path = f"{prefix}.{key}" if prefix else key

            # Check if key name suggests sensitive data
            if any(keyword in key.lower() for keyword in sensitive_keywords):
                sensitive_paths.append(current_path)

            # Recursively check nested dictionaries
            if isinstance(value, dict):
                nested_sensitive = self._find_sensitive_paths(value, current_path)
                sensitive_paths.extend(nested_sensitive)

        return sensitive_paths

    def _get_all_paths_simple(self, data: Dict[str, Any], prefix: str = "") -> set:
        """Get all paths in a dictionary (simplified version).

        Args:
            data: Dictionary to traverse.
            prefix: Current prefix.

        Returns:
            Set of all paths.
        """
        paths = set()
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)
            if isinstance(value, dict):
                paths.update(self._get_all_paths_simple(value, current_path))
        return paths

    def _get_max_depth(self, data: Dict[str, Any], current_depth: int = 1) -> int:
        """Get maximum nesting depth of a dictionary.

        Args:
            data: Dictionary to analyze.
            current_depth: Current depth level.

        Returns:
            Maximum depth found.
        """
        if not isinstance(data, dict):
            return current_depth

        max_depth = current_depth
        for value in data.values():
            if isinstance(value, dict):
                depth = self._get_max_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth
