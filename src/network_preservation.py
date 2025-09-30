"""Network-aware configuration preservation for maintaining connectivity during migrations."""

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class NetworkPattern:
    """Represents a network-critical configuration pattern."""

    pattern: str
    category: str
    priority: int  # Higher = more critical
    description: str


class NetworkPreservationEngine:
    """Preserves network-critical configurations during template migrations."""

    def __init__(self, rules_file_path: Optional[str] = None) -> None:
        """Initialize the network preservation engine.

        Args:
            rules_file_path: Optional path to network migration rules JSON file.
        """
        self._rules = self._load_rules(rules_file_path)
        self._network_patterns = self._initialize_network_patterns()

    def _load_rules(self, rules_file_path: Optional[str]) -> Dict[str, Any]:
        """Load network migration rules from JSON file.

        Args:
            rules_file_path: Path to rules file, or None for default.

        Returns:
            Dictionary containing migration rules.
        """
        if rules_file_path is None:
            # Use default rules file in same directory as this script
            current_dir = Path(__file__).parent.parent
            rules_file_path = str(current_dir / "network_migration_rules.json")

        try:
            with open(rules_file_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback to basic rules if file not found
            return self._get_default_rules()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rules file {rules_file_path}: {e}")

    def _get_default_rules(self) -> Dict[str, Any]:
        """Get default rules when no rules file is available."""
        return {
            "target_version": "25.1.200",
            "preserve_these_paths": [],
            "preserve_these_annotations": [],
            "preserve_these_patterns": [],
            "update_version_in": [],
            "merge_strategy": "smart_merge",
            "required_labels": [],
        }

    def _initialize_network_patterns(self) -> List[NetworkPattern]:
        """Define network-critical patterns to preserve from loaded rules."""
        patterns = []

        # Load patterns from simplified rules file
        for pattern in self._rules.get("preserve_these_patterns", []):
            patterns.append(
                NetworkPattern(
                    pattern=pattern,
                    category="network_critical",
                    priority=50,  # Default priority
                    description=f"Network critical pattern: {pattern}",
                )
            )

        return patterns

    def identify_network_critical_paths(self, config: Dict[str, Any]) -> Set[str]:
        """Identify all network-critical paths in a configuration.

        Args:
            config: Configuration dictionary to analyze.

        Returns:
            Set of paths that are network-critical.
        """
        network_paths: Set[str] = set()
        all_paths = self._get_all_config_paths(config)

        for path in all_paths:
            if self._is_network_critical(path):
                network_paths.add(path)

        return network_paths

    def preserve_network_config(
        self,
        golden_old: Dict[str, Any],
        template_new: Dict[str, Any],
        merged_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Preserve network-critical configurations from golden_old into merged_result.

        Args:
            golden_old: Original production configuration.
            template_new: New template configuration.
            merged_result: Result from standard migration.

        Returns:
            Enhanced configuration with preserved network settings.
        """
        enhanced_result = merged_result.copy()

        # Identify network-critical paths from the golden config
        network_paths = self.identify_network_critical_paths(golden_old)

        for path in network_paths:
            old_value = self._get_nested_value(golden_old, path)
            if old_value is not None:
                # Check if this is a version-sensitive field that needs updating
                if self._should_update_version(path, old_value):
                    updated_value = self._update_version_fields(old_value)
                    self._set_nested_value(enhanced_result, path, updated_value)
                else:
                    # Preserve as-is for network functionality
                    self._set_nested_value(enhanced_result, path, old_value)

        # Handle special cases for annotations merging
        self._merge_network_annotations(golden_old, template_new, enhanced_result)

        # Handle array-style annotations that need special conversion
        self._fix_array_annotations(golden_old, template_new, enhanced_result)

        return enhanced_result

    def _is_network_critical(self, path: str) -> bool:
        """Check if a configuration path is network-critical.

        Args:
            path: Dot-notation configuration path.

        Returns:
            True if the path is network-critical.
        """
        # Check against explicit paths to preserve
        preserve_paths = self._rules.get("preserve_these_paths", [])
        if path in preserve_paths:
            return True

        # Check against patterns
        for pattern in self._network_patterns:
            if re.search(pattern.pattern, path, re.IGNORECASE):
                return True
        return False

    def _should_update_version(self, path: str, value: Any) -> bool:
        """Check if a network-critical field should have version updated.

        Args:
            path: Configuration path.
            value: Current value.

        Returns:
            True if version should be updated.
        """
        # Check against explicit paths that should have version updated
        update_paths = self._rules.get("update_version_in", [])
        for update_path in update_paths:
            if self._path_matches_pattern(path, update_path):
                return True

        return False

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a pattern (supports wildcards).

        Args:
            path: Configuration path to check.
            pattern: Pattern to match against (supports * wildcards).

        Returns:
            True if path matches pattern.
        """
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        return re.search(regex_pattern, path, re.IGNORECASE) is not None

    def _update_version_fields(self, value: Any) -> Any:
        """Update version fields while preserving structure.

        Args:
            value: Value to update.

        Returns:
            Updated value with new version numbers.
        """
        target_version = self._rules.get("target_version", "25.1.200")
        old_version = "25.1.102"  # This could also be configurable in rules

        if isinstance(value, dict):
            updated = value.copy()
            for key, val in updated.items():
                if (
                    "version" in key.lower()
                    and isinstance(val, str)
                    and old_version in val
                ):
                    updated[key] = val.replace(old_version, target_version)
            return updated
        elif isinstance(value, str) and old_version in value:
            return value.replace(old_version, target_version)

        return value

    def _merge_network_annotations(
        self,
        golden_old: Dict[str, Any],
        template_new: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Intelligently merge network annotations from old and new configurations.

        Args:
            golden_old: Original configuration.
            template_new: New template configuration.
            result: Configuration to enhance.
        """
        # Find all annotation-related paths (expanded to catch all annotation types)
        annotation_paths = [
            path
            for path in self._get_all_config_paths(result)
            if any(
                ann_type in path.lower()
                for ann_type in ["annotations", "egressannotations", "podannotations"]
            )
        ]

        # Also include paths explicitly listed in preserve_these_paths that contain annotations
        preserve_paths = self._rules.get("preserve_these_paths", [])
        all_config_paths = self._get_all_config_paths(result)

        for preserve_path in preserve_paths:
            if any(
                ann_type in preserve_path.lower()
                for ann_type in ["annotations", "egressannotations", "podannotations"]
            ):
                # Handle wildcard paths
                if "*" in preserve_path:
                    pattern_regex = preserve_path.replace("*", ".*")
                    import re

                    for config_path in all_config_paths:
                        if (
                            re.match(pattern_regex, config_path)
                            and config_path not in annotation_paths
                        ):
                            annotation_paths.append(config_path)
                elif preserve_path not in annotation_paths:
                    annotation_paths.append(preserve_path)

        for path in annotation_paths:
            old_annotations = self._get_nested_value(golden_old, path)
            new_annotations = self._get_nested_value(template_new, path)
            current_annotations = self._get_nested_value(result, path)

            # Merge annotations from both golden config and new template
            if old_annotations is not None or new_annotations is not None:
                merged_annotations = self._merge_annotation_sources(
                    old_annotations, new_annotations, path
                )
                if merged_annotations is not None:
                    self._set_nested_value(result, path, merged_annotations)

    def _filter_excluded_annotations(self, annotations: Any) -> Any:
        """Filter out excluded annotations from annotation data.

        Args:
            annotations: Annotation data (dict, list, or other format).

        Returns:
            Filtered annotation data with excluded annotations removed.
        """
        if annotations is None:
            return None

        # Get excluded annotations from rules
        excluded_annotations = self._rules.get("exclude_these_annotations", [])

        if isinstance(annotations, dict):
            # Dictionary format - filter out excluded keys
            return {
                key: value
                for key, value in annotations.items()
                if not self._is_annotation_excluded(key)
            }
        elif isinstance(annotations, list):
            # Array format - filter out excluded annotations
            filtered_list = []
            for item in annotations:
                if isinstance(item, dict):
                    # Filter out excluded keys from each dict item
                    filtered_item = {
                        key: value
                        for key, value in item.items()
                        if not self._is_annotation_excluded(key)
                    }
                    if filtered_item:  # Only add non-empty dict items
                        filtered_list.append(filtered_item)
                elif isinstance(item, str) and ":" in item:
                    # Handle "key: value" string format
                    key = item.split(":", 1)[0].strip()
                    if not self._is_annotation_excluded(key):
                        filtered_list.append(item)
                else:
                    # Keep other formats as-is
                    filtered_list.append(item)

            # If the original was array format but became empty, maintain array format
            # unless it was obviously meant to be a dictionary
            return filtered_list
        else:
            # Other formats - return as-is
            return annotations

    def _is_network_annotation(self, annotation_key: str) -> bool:
        """Check if an annotation key is network-critical.

        Args:
            annotation_key: Annotation key to check.

        Returns:
            True if the annotation is network-critical.
        """
        # Get patterns and critical annotations from simplified rules
        preserve_patterns = self._rules.get("preserve_these_patterns", [])
        preserve_annotations = self._rules.get("preserve_these_annotations", [])

        # Check if annotation is in preserve list
        if annotation_key in preserve_annotations:
            return True

        # Check if annotation matches preserve patterns
        for pattern in preserve_patterns:
            if re.search(pattern, annotation_key, re.IGNORECASE):
                return True

        return False

    def _is_annotation_excluded(self, annotation_key: str) -> bool:
        """Check if an annotation key should be excluded from merging.

        Args:
            annotation_key: Annotation key to check.

        Returns:
            True if the annotation should be excluded.
        """
        excluded_annotations = self._rules.get("exclude_these_annotations", [])
        return annotation_key in excluded_annotations

    def _should_use_dict_format_for_path(self, path: str) -> bool:
        """Determine if a path should use dictionary format for annotations.

        Args:
            path: Configuration path.

        Returns:
            True if path should use dictionary format by default.
        """
        # Most service annotations should be in dictionary format
        dict_format_patterns = [
            "service.annotations",
            "externalService.annotations",
            "connectivityService.annotations",
            "externalconnectivityService.annotations",
            "internalService.annotations",
        ]

        # Array format is typically used for pod/container annotations
        array_format_patterns = [
            "mgm.annotations",
            "ndb.annotations",
            "api.annotations",
            "api.ndbapp.annotations",
            "test.annotations",
        ]

        # Check if it should be dictionary format
        for pattern in dict_format_patterns:
            if pattern in path:
                return True

        # Check if it should explicitly be array format
        for pattern in array_format_patterns:
            if pattern in path:
                return False

        # Default to dictionary format for service-related paths
        if "service" in path.lower() and "annotations" in path:
            return True

        return False

    def _get_all_config_paths(
        self, config: Dict[str, Any], prefix: str = ""
    ) -> List[str]:
        """Get all dot-notation paths in a configuration.

        Args:
            config: Configuration dictionary.
            prefix: Current path prefix.

        Returns:
            List of all paths in the configuration.
        """
        paths: List[str] = []

        if isinstance(config, dict):
            for key, value in config.items():
                current_path = f"{prefix}.{key}" if prefix else key
                paths.append(current_path)

                if isinstance(value, dict):
                    paths.extend(self._get_all_config_paths(value, current_path))
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            item_path = f"{current_path}[{i}]"
                            paths.extend(self._get_all_config_paths(item, item_path))

        return paths

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation path.

        Args:
            data: Dictionary to search.
            path: Dot-notation path.

        Returns:
            Value at the path or None if not found.
        """
        if not path:
            return data

        # Handle array indices in path
        if "[" in path and "]" in path:
            return None  # Simplified for now - could implement array support

        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation path.

        Args:
            data: Dictionary to modify.
            path: Dot-notation path.
            value: Value to set.
        """
        if not path:
            return

        # Handle array indices in path
        if "[" in path and "]" in path:
            return  # Simplified for now - could implement array support

        keys = path.split(".")
        current = data

        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def get_network_critical_summary(
        self, config: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate a summary of network-critical configurations found.

        Args:
            config: Configuration to analyze.

        Returns:
            Dictionary mapping categories to lists of paths.
        """
        summary: Dict[str, List[str]] = {}
        network_paths = self.identify_network_critical_paths(config)

        for path in network_paths:
            for pattern in self._network_patterns:
                if re.search(pattern.pattern, path, re.IGNORECASE):
                    if pattern.category not in summary:
                        summary[pattern.category] = []
                    summary[pattern.category].append(path)
                    break

        return summary

    def filter_excluded_annotations_globally(
        self, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove excluded annotations from all annotation paths in the configuration.

        Args:
            config: Configuration to filter.

        Returns:
            Configuration with excluded annotations removed.
        """
        # Check if there are any annotations to exclude
        excluded_annotations = self._rules.get("exclude_these_annotations", [])
        if not excluded_annotations:
            return config

        # Create a copy to avoid modifying the original
        filtered_config = copy.deepcopy(config)

        # Find all annotation-related paths in the configuration
        annotation_paths = [
            path
            for path in self._get_all_config_paths(filtered_config)
            if any(
                ann_type in path.lower()
                for ann_type in ["annotations", "egressannotations", "podannotations"]
            )
        ]

        # Filter excluded annotations from each annotation path
        for path in annotation_paths:
            annotations = self._get_nested_value(filtered_config, path)
            if annotations is not None:
                filtered_annotations = self._filter_excluded_annotations(annotations)
                self._set_nested_value(filtered_config, path, filtered_annotations)

        return filtered_config

    def _fix_array_annotations(
        self,
        golden_old: Dict[str, Any],
        template_new: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Fix both array-style and dictionary-style annotations that need to be merged with new template structure.

        Args:
            golden_old: Original configuration with annotations.
            template_new: New template configuration with annotations.
            result: Configuration to enhance.
        """
        # Get critical annotation paths from rules - use preserve_these_paths for annotation-related paths
        preserve_paths = self._rules.get("preserve_these_paths", [])
        all_config_paths = self._get_all_config_paths(result)
        critical_annotation_paths = []

        for preserve_path in preserve_paths:
            if any(
                ann_type in preserve_path.lower()
                for ann_type in ["annotations", "egressannotations", "podannotations"]
            ):
                # Handle wildcard paths
                if "*" in preserve_path:
                    pattern_regex = preserve_path.replace("*", ".*")
                    import re

                    for config_path in all_config_paths:
                        if (
                            re.match(pattern_regex, config_path)
                            and config_path not in critical_annotation_paths
                        ):
                            critical_annotation_paths.append(config_path)
                elif preserve_path not in critical_annotation_paths:
                    critical_annotation_paths.append(preserve_path)

        for path in critical_annotation_paths:
            old_annotations = self._get_nested_value(golden_old, path)
            new_template_annotations = self._get_nested_value(template_new, path)
            current_annotations = self._get_nested_value(result, path)

            # Process if old_annotations exists OR new template has annotations
            if old_annotations is not None or new_template_annotations is not None:
                # Handle array-style annotations (convert to dict first)
                old_annotations_dict = {}
                if old_annotations is not None:
                    if isinstance(old_annotations, list):
                        old_annotations_dict = self._convert_array_annotations_to_dict(
                            old_annotations
                        )
                    elif isinstance(old_annotations, dict):
                        old_annotations_dict = old_annotations

                # Handle new template annotations
                new_template_annotations_dict = {}
                if new_template_annotations is not None:
                    if isinstance(new_template_annotations, list):
                        new_template_annotations_dict = (
                            self._convert_array_annotations_to_dict(
                                new_template_annotations
                            )
                        )
                    elif isinstance(new_template_annotations, dict):
                        new_template_annotations_dict = new_template_annotations

                # Determine the format to maintain based on current annotations or path
                maintain_array_format = False
                if current_annotations and isinstance(current_annotations, list):
                    maintain_array_format = True
                elif new_template_annotations and isinstance(
                    new_template_annotations, list
                ):
                    maintain_array_format = True
                elif old_annotations and isinstance(old_annotations, list):
                    maintain_array_format = True
                elif path.endswith(".annotations"):
                    # Most component annotations are in array format
                    maintain_array_format = True

                # Override with path-based format detection for service annotations
                if self._should_use_dict_format_for_path(path):
                    maintain_array_format = False

                # Check if golden config explicitly disabled annotations (empty dict/array)
                golden_annotations_explicitly_disabled = (
                    old_annotations is not None
                    and (
                        (
                            isinstance(old_annotations, dict)
                            and len(old_annotations) == 0
                        )
                        or (
                            isinstance(old_annotations, list)
                            and len(old_annotations) == 0
                        )
                    )
                )

                # Merge annotations: golden config + new template annotations
                merged_annotations_dict = {}
                excluded_annotations = self._rules.get("exclude_these_annotations", [])

                # Add old annotations (golden config) - these take precedence
                for key, value in old_annotations_dict.items():
                    if not self._is_annotation_excluded(key):
                        merged_annotations_dict[key] = value

                # Only add new template annotations if golden config didn't explicitly disable them
                if not golden_annotations_explicitly_disabled:
                    # Add new template annotations that don't exist in golden config and aren't excluded
                    for key, value in new_template_annotations_dict.items():
                        if (
                            key not in merged_annotations_dict
                            and not self._is_annotation_excluded(key)
                        ):
                            merged_annotations_dict[key] = value

                # Convert to appropriate format
                if maintain_array_format:
                    if merged_annotations_dict:
                        merged_annotations: Any = [
                            {key: value}
                            for key, value in merged_annotations_dict.items()
                        ]
                    else:
                        # For empty annotations, preserve the original golden config format if it was explicitly disabled
                        if (
                            golden_annotations_explicitly_disabled
                            and old_annotations is not None
                        ):
                            # Preserve the exact format from golden config when it was explicitly disabled
                            merged_annotations = old_annotations
                        else:
                            # For empty array annotations, check if we should maintain array format
                            original_had_content = (
                                old_annotations
                                and isinstance(old_annotations, list)
                                and old_annotations
                            ) or (
                                new_template_annotations
                                and isinstance(new_template_annotations, list)
                                and new_template_annotations
                            )
                            if original_had_content:
                                merged_annotations = []
                            else:
                                # Default to dictionary format for empty annotations
                                merged_annotations = {}
                else:
                    if merged_annotations_dict:
                        merged_annotations = merged_annotations_dict
                    else:
                        # For empty annotations, preserve the original golden config format if it was explicitly disabled
                        if (
                            golden_annotations_explicitly_disabled
                            and old_annotations is not None
                        ):
                            # Preserve the exact format from golden config when it was explicitly disabled
                            merged_annotations = old_annotations
                        else:
                            merged_annotations = {}

                # Set the merged annotations (preserve format consistency)
                self._set_nested_value(result, path, merged_annotations)

    def _convert_array_annotations_to_dict(
        self, array_annotations: List[Any]
    ) -> Dict[str, str]:
        """Convert array-style annotations to dictionary format.

        Args:
            array_annotations: List of annotation dictionaries or "key: value" strings.

        Returns:
            Dictionary of annotation key-value pairs.
        """
        annotation_dict = {}

        if not isinstance(array_annotations, list):
            return annotation_dict

        for annotation in array_annotations:
            if isinstance(annotation, dict):
                # Already a dictionary, merge it
                for key, value in annotation.items():
                    annotation_dict[key] = str(value)
            elif isinstance(annotation, str) and ":" in annotation:
                # Split on first colon to handle values with colons
                key, value = annotation.split(":", 1)
                annotation_dict[key.strip()] = value.strip().strip('"')
            elif isinstance(annotation, str):
                # Handle strings without colons (edge case)
                annotation_dict[annotation.strip()] = ""

        return annotation_dict

    def _merge_annotation_arrays(
        self, current: List[Any], enhanced: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Merge array-style annotations with enhanced annotations.

        Args:
            current: Current array-style annotations.
            enhanced: Enhanced annotations as dictionary.

        Returns:
            Merged annotations as array of single-key dictionaries.
        """
        # Convert current array to dict first
        current_dict = self._convert_array_annotations_to_dict(current)

        # Merge dictionaries (enhanced takes precedence for duplicates)
        merged_dict = {**current_dict, **enhanced}

        # Convert back to array format
        return [{key: value} for key, value in merged_dict.items()]

    def _merge_annotation_dicts(
        self, current: Dict[str, str], enhanced: Dict[str, str]
    ) -> Dict[str, str]:
        """Merge dictionary-style annotations.

        Args:
            current: Current annotations as dictionary.
            enhanced: Enhanced annotations as dictionary.

        Returns:
            Merged annotations dictionary.
        """
        # Enhanced takes precedence, but preserve new template additions
        return {**enhanced, **current}

    def _merge_annotation_sources(
        self, old_annotations: Any, new_annotations: Any, path: str
    ) -> Any:
        """Merge annotations from golden config and new template.

        Args:
            old_annotations: Annotations from golden config (may be None).
            new_annotations: Annotations from new template (may be None).
            path: Configuration path for context.

        Returns:
            Merged annotations in appropriate format.
        """
        # Handle case where only one source has annotations
        if old_annotations is None and new_annotations is not None:
            return self._filter_excluded_annotations(new_annotations)
        elif old_annotations is not None and new_annotations is None:
            return self._filter_excluded_annotations(old_annotations)
        elif old_annotations is None and new_annotations is None:
            return None

        # Both sources have annotations - merge them
        # Convert both to dictionaries for merging
        old_dict = {}
        new_dict = {}

        if isinstance(old_annotations, list):
            old_dict = self._convert_array_annotations_to_dict(old_annotations)
        elif isinstance(old_annotations, dict):
            old_dict = old_annotations

        if isinstance(new_annotations, list):
            new_dict = self._convert_array_annotations_to_dict(new_annotations)
        elif isinstance(new_annotations, dict):
            new_dict = new_annotations

        # Check if golden config explicitly disabled annotations (empty dict/array)
        golden_annotations_explicitly_disabled = old_annotations is not None and (
            (isinstance(old_annotations, dict) and len(old_annotations) == 0)
            or (isinstance(old_annotations, list) and len(old_annotations) == 0)
        )

        # Merge: golden config takes precedence, but add new template annotations
        merged_dict = {}
        excluded_annotations = self._rules.get("exclude_these_annotations", [])

        # Only add new template annotations if golden config didn't explicitly disable them
        if not golden_annotations_explicitly_disabled:
            # Add new template annotations first
            for key, value in new_dict.items():
                if not self._is_annotation_excluded(key):
                    merged_dict[key] = value

        # Add golden config annotations (these override template)
        for key, value in old_dict.items():
            if not self._is_annotation_excluded(key):
                merged_dict[key] = value

        # Determine format based on both old and new annotations and path patterns
        # Prefer the format from golden config if it exists, otherwise use new template format
        use_array_format = False
        if old_annotations is not None and isinstance(old_annotations, list):
            use_array_format = True
        elif old_annotations is None and isinstance(new_annotations, list):
            use_array_format = True

        # Override with path-based format detection for empty results
        if not merged_dict and self._should_use_dict_format_for_path(path):
            use_array_format = False

        # Convert back to appropriate format
        if use_array_format:
            # Maintain array format - convert each key-value pair to a single-key dict
            if merged_dict:
                return [{key: value} for key, value in merged_dict.items()]
            else:
                # For empty annotations, preserve the original golden config format if it was explicitly disabled
                if (
                    golden_annotations_explicitly_disabled
                    and old_annotations is not None
                ):
                    # Preserve the exact format from golden config when it was explicitly disabled
                    return old_annotations
                else:
                    # For empty arrays, maintain array format only if both sources were originally arrays
                    # or if we have explicit content that was filtered out
                    original_had_content = (
                        old_annotations
                        and isinstance(old_annotations, list)
                        and old_annotations
                    ) or (
                        new_annotations
                        and isinstance(new_annotations, list)
                        and new_annotations
                    )
                    if original_had_content:
                        return []
                    else:
                        # Default to dictionary format for empty annotations
                        return {}
        else:
            if merged_dict:
                return merged_dict
            else:
                # For empty annotations, preserve the original golden config format if it was explicitly disabled
                if (
                    golden_annotations_explicitly_disabled
                    and old_annotations is not None
                ):
                    # Preserve the exact format from golden config when it was explicitly disabled
                    return old_annotations
                else:
                    # Maintain dictionary format - return empty dict when no annotations
                    return {}
