"""Core merge logic and conflict resolution engine."""

import copy
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from .diff_analyzer import DiffAnalyzer
    from .network_preservation import NetworkPreservationEngine
except ImportError:
    from diff_analyzer import DiffAnalyzer
    from network_preservation import NetworkPreservationEngine


class ConflictResolution(Enum):
    """Types of conflict resolution actions."""

    OVERWRITE = "OVERWRITE"
    DELETED = "DELETED"
    ADDED = "ADDED"
    STRUCTURAL_MISMATCH = "STRUCTURAL_MISMATCH"
    MIGRATED = "MIGRATED"


class MergeEngine:
    """Core logic for merging configurations and resolving conflicts."""

    def __init__(self, rules_file_path: Optional[str] = None) -> None:
        """Initialize merge engine with diff analyzer and network preservation.

        Args:
            rules_file_path: Optional path to network migration rules JSON file.
        """
        self.diff_analyzer = DiffAnalyzer()
        self.network_engine = NetworkPreservationEngine(rules_file_path)

    def merge_configurations(
        self,
        golden_config: Dict[str, Any],
        template_old: Dict[str, Any],
        template_new: Dict[str, Any],
        migration_map: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Perform complete configuration merge with conflict resolution.

        Args:
            golden_config: V_OLD golden configuration with custom values.
            template_old: V_OLD template baseline.
            template_new: V_NEW template target.
            migration_map: Optional mapping of old paths to new paths.

        Returns:
            Tuple containing merged configuration and conflict log entries.
        """
        # Step 1: Extract custom data from golden config
        custom_data = self.extract_custom_data(golden_config, template_old)

        # Step 2: Apply migrations if provided
        if migration_map:
            custom_data = self.apply_migrations(custom_data, migration_map)

        # Step 3: Resolve conflicts and merge
        final_config, conflict_log = self.resolve_conflicts(
            custom_data, template_new, template_old
        )

        # Step 4: Apply network-aware preservation to maintain connectivity
        final_config = self.network_engine.preserve_network_config(
            golden_config, template_new, final_config
        )

        # Step 5: Log network preservation actions
        network_summary = self.network_engine.get_network_critical_summary(final_config)
        self._add_network_preservation_logs(conflict_log, network_summary)

        return final_config, conflict_log

    def extract_custom_data(
        self, golden_config: Dict[str, Any], template_old: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract custom configuration data by comparing golden config with old template.

        Args:
            golden_config: The V_OLD golden configuration with custom values.
            template_old: The V_OLD template baseline.

        Returns:
            Dictionary mapping paths to custom values.
        """
        return self.diff_analyzer.extract_custom_data(golden_config, template_old)

    def resolve_conflicts(
        self,
        custom_data: Dict[str, Any],
        template_new: Dict[str, Any],
        template_old: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Resolve conflicts between custom data and new template structure.

        Args:
            custom_data: Dictionary of custom configuration values.
            template_new: New template configuration structure.
            template_old: Old template for comparison context.

        Returns:
            Tuple containing merged configuration and list of conflict log entries.
        """
        # Start with a deep copy of the new template
        final_config = copy.deepcopy(template_new)
        conflict_log: List[Dict[str, Any]] = []

        # Find structural changes for context
        deleted_paths = self.diff_analyzer.find_deleted_paths(
            template_old, template_new
        )
        structural_changes = self.diff_analyzer.find_structural_changes(
            template_old, template_new
        )

        # Process each custom data entry
        for path, custom_value in custom_data.items():
            # Check if this path should be deleted first, before applying
            if path in deleted_paths:
                # Don't apply deleted values, just log
                log_entry = self._create_log_entry(
                    path=path,
                    action_type=ConflictResolution.DELETED,
                    source_value=custom_value,
                    target_value=None,
                    new_default_value=None,
                    reason=f"Key '{path}' was removed in new template version",
                    manual_review=True,
                )
                conflict_log.append(log_entry)
                continue

            log_entry = self._resolve_single_conflict(
                path,
                custom_value,
                final_config,
                template_new,
                template_old,
                deleted_paths,
                structural_changes,
            )
            if log_entry:
                conflict_log.append(log_entry)

        return final_config, conflict_log

    def _resolve_single_conflict(
        self,
        path: str,
        custom_value: Any,
        final_config: Dict[str, Any],
        template_new: Dict[str, Any],
        template_old: Dict[str, Any],
        deleted_paths: List[str],
        structural_changes: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Resolve a single configuration conflict.

        Args:
            path: Configuration path.
            custom_value: Custom value from golden config.
            final_config: Configuration being built.
            template_new: New template for reference.
            template_old: Old template for reference.
            deleted_paths: List of paths deleted in new template.
            structural_changes: Dictionary of structural changes.

        Returns:
            Conflict log entry if any action was taken, None otherwise.
        """
        # Case 1: Structural mismatch
        if path in structural_changes:
            # Check if we can safely apply the value despite structural changes
            try:
                if self.diff_analyzer.path_exists(template_new, path):
                    new_default = self.diff_analyzer.get_nested_value(
                        template_new, path
                    )
                    old_default = (
                        self.diff_analyzer.get_nested_value(template_old, path)
                        if self.diff_analyzer.path_exists(template_old, path)
                        else None
                    )

                    # Check type compatibility
                    if type(custom_value) == type(new_default):
                        # Types match, we can apply the value
                        self.diff_analyzer.set_nested_value(
                            final_config, path, custom_value
                        )
                        return self._create_log_entry(
                            path=path,
                            action_type=ConflictResolution.OVERWRITE,
                            source_value=custom_value,
                            target_value=custom_value,
                            new_default_value=new_default,
                            reason=f"Custom value applied despite structural change: {structural_changes[path]}",
                            manual_review=True,
                        )
                    else:
                        # Type mismatch, cannot apply safely - keep new template value
                        return self._create_log_entry(
                            path=path,
                            action_type=ConflictResolution.STRUCTURAL_MISMATCH,
                            source_value=custom_value,
                            target_value=new_default,
                            new_default_value=new_default,
                            reason=f"Cannot apply custom value due to type change: {structural_changes[path]}",
                            manual_review=True,
                        )
            except (KeyError, TypeError):
                pass

            # If we can't determine compatibility, don't apply the value
            try:
                new_default = (
                    self.diff_analyzer.get_nested_value(template_new, path)
                    if self.diff_analyzer.path_exists(template_new, path)
                    else None
                )
            except (KeyError, TypeError):
                new_default = None

            return self._create_log_entry(
                path=path,
                action_type=ConflictResolution.STRUCTURAL_MISMATCH,
                source_value=custom_value,
                target_value=new_default,
                new_default_value=new_default,
                reason=f"Structural mismatch prevents applying custom value: {structural_changes[path]}",
                manual_review=True,
            )

        # Case 2: Simple overwrite (path exists in new template)
        if self.diff_analyzer.path_exists(template_new, path):
            try:
                new_default = self.diff_analyzer.get_nested_value(template_new, path)
                self.diff_analyzer.set_nested_value(final_config, path, custom_value)

                # Only log if the custom value differs from new default
                if custom_value != new_default:
                    return self._create_log_entry(
                        path=path,
                        action_type=ConflictResolution.OVERWRITE,
                        source_value=custom_value,
                        target_value=custom_value,
                        new_default_value=new_default,
                        reason="Custom value preserved from old configuration",
                        manual_review=False,
                    )
            except (KeyError, TypeError) as e:
                return self._create_log_entry(
                    path=path,
                    action_type=ConflictResolution.STRUCTURAL_MISMATCH,
                    source_value=custom_value,
                    target_value=None,
                    new_default_value=None,
                    reason=f"Failed to apply custom value: {e}",
                    manual_review=True,
                )

        # Case 3: Path doesn't exist in new template (not in deleted_paths)
        else:
            return self._create_log_entry(
                path=path,
                action_type=ConflictResolution.DELETED,
                source_value=custom_value,
                target_value=None,
                new_default_value=None,
                reason=f"Custom path '{path}' does not exist in new template",
                manual_review=True,
            )

        return None

    def apply_migrations(
        self, custom_data: Dict[str, Any], migration_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply path migrations to custom data.

        Args:
            custom_data: Dictionary of custom configuration values.
            migration_map: Mapping of old paths to new paths.

        Returns:
            Updated custom data with migrated paths.
        """
        migrated_data: Dict[str, Any] = {}

        for old_path, custom_value in custom_data.items():
            if old_path in migration_map:
                new_path = migration_map[old_path]
                migrated_data[new_path] = custom_value
                # Note: Migration logging will be handled in resolve_conflicts
            else:
                migrated_data[old_path] = custom_value

        return migrated_data

    def _create_log_entry(
        self,
        path: str,
        action_type: ConflictResolution,
        source_value: Any,
        target_value: Any,
        new_default_value: Any,
        reason: str,
        manual_review: bool = False,
    ) -> Dict[str, Any]:
        """Create a standardized conflict log entry.

        Args:
            path: Configuration path.
            action_type: Type of resolution action taken.
            source_value: Original value from golden config.
            target_value: Final value in merged config.
            new_default_value: Default value from new template.
            reason: Human-readable explanation.
            manual_review: Whether manual review is required.

        Returns:
            Formatted log entry dictionary.
        """
        return {
            "path": path,
            "action_type": action_type.value,
            "source_value": source_value,
            "target_value": target_value,
            "new_default_value": new_default_value,
            "reason": reason,
            "manual_review": manual_review,
        }

    def validate_migration_map(self, migration_map: Dict[str, str]) -> List[str]:
        """Validate migration map for circular references and format issues.

        Args:
            migration_map: Dictionary mapping old paths to new paths.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        # Check for circular references
        visited = set()
        for old_path in migration_map:
            current_path = old_path
            path_chain = [current_path]

            while current_path in migration_map:
                next_path = migration_map[current_path]
                if next_path in path_chain:
                    errors.append(
                        f"Circular migration detected: {' -> '.join(path_chain)} -> {next_path}"
                    )
                    break
                if next_path in visited:
                    break
                path_chain.append(next_path)
                current_path = next_path

            visited.add(old_path)

        # Check for invalid path formats
        all_paths = list(migration_map.keys()) + list(migration_map.values())
        for path in all_paths:
            if not path or not isinstance(path, str):
                errors.append(f"Invalid path format: {path}")
                continue
            if path.startswith(".") or path.endswith(".") or ".." in path:
                errors.append(
                    f"Invalid path format: '{path}' (cannot start/end with '.' or contain '..')"
                )

        return errors

    def get_merge_statistics(
        self, conflict_log: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate statistics about the merge operation.

        Args:
            conflict_log: List of conflict log entries.

        Returns:
            Dictionary containing merge statistics.
        """
        if not conflict_log:
            return {
                "total_conflicts": 0,
                "by_action_type": {},
                "manual_review_required": 0,
                "successful_overwrites": 0,
            }

        by_action_type: Dict[str, int] = {}
        manual_review_count = 0
        successful_overwrites = 0

        for entry in conflict_log:
            action_type = entry["action_type"]
            by_action_type[action_type] = by_action_type.get(action_type, 0) + 1

            if entry.get("manual_review", False):
                manual_review_count += 1

            if action_type == ConflictResolution.OVERWRITE.value and not entry.get(
                "manual_review", False
            ):
                successful_overwrites += 1

        return {
            "total_conflicts": len(conflict_log),
            "by_action_type": by_action_type,
            "manual_review_required": manual_review_count,
            "successful_overwrites": successful_overwrites,
        }

    def _add_network_preservation_logs(
        self, conflict_log: List[Dict[str, Any]], network_summary: Dict[str, List[str]]
    ) -> None:
        """Add network preservation information to conflict log.

        Args:
            conflict_log: Existing conflict log to enhance.
            network_summary: Summary of network-critical configurations.
        """
        # Add a summary entry about network preservation
        total_network_paths = sum(len(paths) for paths in network_summary.values())

        if total_network_paths > 0:
            network_log_entry = self._create_log_entry(
                path="__NETWORK_PRESERVATION_SUMMARY__",
                action_type=ConflictResolution.OVERWRITE,
                source_value=f"Preserved {total_network_paths} network-critical configurations",
                target_value=f"Network categories: {', '.join(network_summary.keys())}",
                new_default_value=None,
                reason="Automatically preserved network-critical labels and annotations to maintain connectivity",
                manual_review=False,
            )
            conflict_log.append(network_log_entry)
