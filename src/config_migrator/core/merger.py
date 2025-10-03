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
        nstf: Dict[str, Any], etf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stage 1 merger following the flowchart logic:
        1. Start with ETF (template)
        2. Override with NSTF values (highest precedence)

        Args:
            nstf: Namespace Template File (highest precedence)
            etf: Engineering Template File (base template)

        Returns:
            Merged configuration dictionary
        """
        # Step 1: Start with ETF as base template
        result = copy.deepcopy(etf)

        # Step 2: Override with NSTF values (site-specific, highest precedence)
        result = ConfigMerger.deep_merge(result, nstf)

        return result

    @staticmethod
    def merge_configs_stage2(
        diff_file: Dict[str, Any], newtf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stage 2 merger following the flowchart logic:
        1. Start with NEWTF (new_temporary.yml)
        2. Apply diff_nstf_etf.yml with specific precedence rules:
           - Modify: If key exists in both, use value from diff_nstf_etf.yml (NSTF precedence)
           - New: Include new keys from either file
           - Deletion: Ignore deletions (don't remove keys)

        Args:
            diff_file: diff_nstf_etf.yml data (from Stage 1)
            newtf: NEWTF data (new_temporary.yml)

        Returns:
            Merged configuration dictionary
        """
        # Step 1: Start with NEWTF as base (new_temporary.yml)
        result = copy.deepcopy(newtf)

        # Step 2: Apply diff_nstf_etf.yml with precedence rules
        result = ConfigMerger._merge_with_stage2_rules(result, diff_file)

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
        nstf: Dict[str, Any], etf: Dict[str, Any], newtf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a summary of the merge process.

        Args:
            nstf: Namespace Template File
            etf: Engineering Template File
            newtf: New Engineering Template File

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

        # Find NEWTF additions
        newtf_additions = ConfigMerger.compare_configs(etf, newtf)

        # Find NSTF overrides
        nstf_overrides = ConfigMerger.compare_configs(etf, nstf)

        return {
            "etf_keys": count_keys(etf),
            "newtf_additions": count_keys(newtf_additions),
            "nstf_overrides": count_keys(nstf_overrides),
            "newtf_additions_detail": newtf_additions,
            "nstf_overrides_detail": nstf_overrides,
        }
