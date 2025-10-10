"""
Configuration merger with NSTF precedence rules.

Implements the core logic for merging YAML configurations according to the flowchart:
1. Start with ETF (Engineering Template File) as base
2. Apply NEWTF (New Engineering Template File) updates
3. Override with NSTF (Namespace Template File) values (highest precedence)
"""

import copy
from typing import Any, Dict


class ConfigMerger:
    """Generic YAML configuration merger with NSTF precedence."""

    @staticmethod
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries with override precedence.

        Args:
            base: Base dictionary
            override: Override dictionary (takes precedence)

        Returns:
            Merged dictionary
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = ConfigMerger.deep_merge(result[key], value)
            else:
                # Override with new value (including lists)
                result[key] = copy.deepcopy(value)

        return result

    @staticmethod
    def merge_configs_stage1(
        nsprev: Dict[str, Any], engprev: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stage 1 merger - returns only the differences between NSPREV and ENGPREV:
        1. Compare NSPREV against ENGPREV (base template)
        2. Return only modified, added, or deleted values from NSPREV

        Args:
            nsprev: Namespace Previous configuration (highest precedence)
            engprev: Engineering Previous template (base template)

        Returns:
            Dictionary containing only the changes (differences) from NSPREV
        """
        # Return only the differences between NSPREV and ENGPREV
        # This gives us just the modifications, additions, and deletions
        return ConfigMerger._get_differences(nsprev, engprev)

    @staticmethod
    def merge_configs_stage2(
        diff_file: Dict[str, Any],
        engnew: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Stage 2 merger with correct precedence order:
        1. Start with ENGNEW (new template structure as foundation)
        2. Apply diff_file values ONLY for keys that exist in ENGNEW (selective overlay)

        Final precedence: NSPREV (via diff) > ENGNEW (for matching keys only)

        Args:
            diff_file: diff_nsprev_engprev.yml data (from Stage 1) - NSPREV differences only
            engnew: ENGNEW data (engineering new template) - foundation structure

        Returns:
            Merged configuration dictionary with ENGNEW structure and NSPREV customizations
        """
        # Start with ENGNEW as foundation
        result = copy.deepcopy(engnew)
        
        # Apply DIFF values only for keys that exist in ENGNEW
        result = ConfigMerger._selective_overlay(result, diff_file)
        
        return result

    @staticmethod
    def _merge_with_stage2_rules(
        base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge with Stage 2 specific rules:
        - Modify: If key exists in both, use value from override (diff_nstf_etf.yml)
        - New: Include new keys from either file
        - Deletion: Ignore deletions (don't remove keys)
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = ConfigMerger._merge_with_stage2_rules(result[key], value)
            else:
                # Modify: Use value from diff_nstf_etf.yml (NSTF precedence)
                result[key] = copy.deepcopy(value)

        return result

    @staticmethod
    def _selective_overlay(
        engnew: Dict[str, Any], diff_file: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply DIFF values only for keys that exist in ENGNEW.
        This ensures ENGNEW structure is preserved while applying NSPREV customizations.

        Args:
            engnew: ENGNEW configuration (foundation structure)
            diff_file: DIFF configuration (NSPREV customizations to apply selectively)

        Returns:
            ENGNEW with NSPREV customizations applied only for existing keys
        """
        result = copy.deepcopy(engnew)

        for key, value in engnew.items():
            if key in diff_file:
                if (
                    isinstance(value, dict)
                    and isinstance(diff_file[key], dict)
                ):
                    # Recursively apply selective overlay for nested dictionaries
                    result[key] = ConfigMerger._selective_overlay(value, diff_file[key])
                elif (
                    isinstance(value, list)
                    and isinstance(diff_file[key], list)
                ):
                    # For lists, merge items by index (preserve ENGNEW structure)
                    result[key] = ConfigMerger._merge_list_items(value, diff_file[key])
                else:
                    # Apply DIFF value for matching key (scalar values)
                    result[key] = copy.deepcopy(diff_file[key])
            # If key not in diff_file, keep original ENGNEW value

        return result

    @staticmethod
    def _merge_list_items(engnew_list: list, diff_list: list) -> list:
        """
        Merge list items by index, preserving ENGNEW structure and applying DIFF values.
        
        Args:
            engnew_list: ENGNEW list (foundation structure)
            diff_list: DIFF list (NSPREV customizations)
            
        Returns:
            Merged list with ENGNEW structure and DIFF values applied
        """
        result = copy.deepcopy(engnew_list)
        
        # Apply DIFF values for matching indices
        for i, diff_item in enumerate(diff_list):
            if i < len(result):
                if isinstance(result[i], dict) and isinstance(diff_item, dict):
                    # Use deep_merge to properly combine dictionaries within list items
                    result[i] = ConfigMerger.deep_merge(result[i], diff_item)
                else:
                    # Replace scalar values or non-dict items
                    result[i] = copy.deepcopy(diff_item)
        
        return result

    @staticmethod
    def compare_configs(
        config1: Dict[str, Any], config2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two configurations and return differences.

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            Dictionary containing differences
        """
        differences = {}

        # Find keys in config2 that are different from config1
        for key, value in config2.items():
            if key not in config1:
                differences[key] = value
            elif isinstance(value, dict) and isinstance(config1[key], dict):
                nested_diff = ConfigMerger.compare_configs(config1[key], value)
                if nested_diff:
                    differences[key] = nested_diff
            elif value != config1[key]:
                differences[key] = value

        return differences

    @staticmethod
    def get_merge_summary(
        nsprev: Dict[str, Any], engprev: Dict[str, Any], engnew: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a summary of the merge process.

        Args:
            nsprev: Namespace Previous configuration
            engprev: Engineering Previous template
            engnew: Engineering New template

        Returns:
            Summary dictionary with merge statistics
        """

        # Count keys at each level
        def count_keys(data: Dict[str, Any]) -> int:
            count = 0
            for value in data.values():
                if isinstance(value, dict):
                    count += count_keys(value)
                else:
                    count += 1
            return count

        # Find ENGNEW additions
        engnew_additions = ConfigMerger.compare_configs(engprev, engnew)

        # Find NSPREV overrides
        nsprev_overrides = ConfigMerger.compare_configs(engprev, nsprev)

        return {
            "engprev_keys": count_keys(engprev),
            "engnew_additions": count_keys(engnew_additions),
            "nsprev_overrides": count_keys(nsprev_overrides),
            "engnew_additions_detail": engnew_additions,
            "nsprev_overrides_detail": nsprev_overrides,
        }

    @staticmethod
    def _get_differences(
        source: Dict[str, Any], base: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get differences between source and base configurations.
        Returns only the keys/values from source that are different from base.

        Args:
            source: Source configuration (NSPREV)
            base: Base configuration (ENGPREV)

        Returns:
            Dictionary containing only the differences from source
        """
        differences = {}

        # Check each key in source
        for key, value in source.items():
            if key not in base:
                # Key is new in source (added)
                differences[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(base[key], dict):
                # Both are dictionaries, recursively check for differences
                nested_diff = ConfigMerger._get_differences(value, base[key])
                if nested_diff:  # Only include if there are actual differences
                    differences[key] = nested_diff
            elif value != base[key]:
                # Value is different (modified)
                differences[key] = copy.deepcopy(value)
            # If value == base[key], it's unchanged, so we don't include it

        return differences

    @staticmethod
    def _merge_engprev_gaps(
        engnew: Dict[str, Any], engprev: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge ENGPREV keys into ENGNEW only where ENGNEW doesn't have those keys.
        This ensures no ENGPREV configuration is lost when ENGNEW doesn't have equivalent keys.

        Args:
            engnew: ENGNEW configuration (takes precedence)
            engprev: ENGPREV configuration (fills gaps)

        Returns:
            ENGNEW with ENGPREV keys added where missing
        """
        result = copy.deepcopy(engnew)

        for key, value in engprev.items():
            if key not in result:
                # Key doesn't exist in ENGNEW, add it from ENGPREV
                result[key] = copy.deepcopy(value)
            elif isinstance(result[key], dict) and isinstance(value, dict):
                # Both are dictionaries, recursively merge gaps
                result[key] = ConfigMerger._merge_engprev_gaps(result[key], value)
            # If key exists in both and at least one is not a dict, ENGNEW takes precedence

        return result
