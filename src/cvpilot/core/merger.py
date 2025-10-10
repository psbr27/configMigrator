"""
Configuration merger with NSTF precedence rules.

Implements the core logic for merging YAML configurations according to the flowchart:
1. Start with ETF (Engineering Template File) as base
2. Apply NEWTF (New Engineering Template File) updates
3. Override with NSTF (Namespace Template File) values (highest precedence)
"""

import copy
from typing import Any, Dict, List, Optional


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

    @staticmethod
    def merge_with_rulebook(
        nsprev: Dict[str, Any], 
        engnew: Dict[str, Any], 
        rulebook_path: Optional[str] = None,
        original_nsprev: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge configurations using rulebook-based strategies.
        
        Args:
            nsprev: NSPREV configuration (DIFF file)
            engnew: ENGNEW configuration  
            rulebook_path: Path to rulebook YAML file
            original_nsprev: Original NSPREV data for fallback
            
        Returns:
            Merged configuration
        """
        from cvpilot.core.rulebook import RulebookManager
        
        # Load rulebook if provided
        rulebook = None
        if rulebook_path:
            rulebook = RulebookManager(rulebook_path)
        
        # Start with ENGNEW as base (includes all new fields)
        result = copy.deepcopy(engnew)
        
        # Apply DIFF as overlay, checking rulebook for each field
        result = ConfigMerger._apply_diff_with_rulebook(result, nsprev, original_nsprev, rulebook)
        
        return result

    @staticmethod
    def _apply_diff_with_rulebook(
        engnew: Dict[str, Any], 
        diff: Dict[str, Any], 
        original_nsprev: Optional[Dict[str, Any]],
        rulebook: Optional[Any]
    ) -> Dict[str, Any]:
        """
        Apply DIFF as overlay to ENGNEW, checking rulebook for each field.
        
        Args:
            engnew: ENGNEW configuration (base)
            diff: DIFF configuration (overlay)
            original_nsprev: Original NSPREV data for fallback
            rulebook: Rulebook manager instance
            
        Returns:
            Merged configuration
        """
        result = copy.deepcopy(engnew)
        
        # Apply DIFF as overlay, checking rulebook for each field
        result = ConfigMerger._merge_diff_with_rulebook(result, diff, original_nsprev, rulebook, "")
        
        return result

    @staticmethod
    def _has_rulebook_rule(rulebook: Optional[Any], path: str) -> bool:
        """
        Check if a path has an explicit rulebook rule.
        
        Args:
            rulebook: Rulebook manager instance
            path: Field path to check
            
        Returns:
            True if path has explicit rulebook rule
        """
        if not rulebook:
            return False
            
        # Check path_overrides
        path_overrides = rulebook.rules.get('path_overrides', {})
        if any(rulebook._path_matches(path, override) for override in path_overrides.keys()):
            return True
        
        # Check merge_rules with matching scope
        merge_rules = rulebook.rules.get('merge_rules', {})
        for field_name, config in merge_rules.items():
            if config.get('scope') == 'global':
                # Check if last segment of path matches field name
                path_segments = path.split('.')
                if path_segments[-1] == field_name:
                    return True
            # Check specific scope paths if needed
        
        return False

    @staticmethod
    def _merge_diff_with_rulebook(
        engnew: Dict[str, Any], 
        diff: Dict[str, Any], 
        original_nsprev: Optional[Dict[str, Any]],
        rulebook: Optional[Any],
        path: str
    ) -> Dict[str, Any]:
        """
        Recursively merge DIFF with ENGNEW, checking rulebook for each field.
        
        Args:
            engnew: ENGNEW configuration (base)
            diff: DIFF configuration (overlay)
            original_nsprev: Original NSPREV data for fallback
            rulebook: Rulebook manager instance
            path: Current path in the structure
            
        Returns:
            Merged configuration
        """
        result = copy.deepcopy(engnew)
        
        for key, diff_value in diff.items():
            current_path = f"{path}.{key}" if path else key
            
            if key in engnew:
                engnew_value = engnew[key]
                
                # Check if rulebook has a rule for this path
                if rulebook and ConfigMerger._has_rulebook_rule(rulebook, current_path):
                    strategy = rulebook.get_merge_strategy(current_path)
                    
                    if strategy == "engnew":
                        # Keep ENGNEW value, ignore DIFF
                        continue
                    elif strategy == "nsprev":
                        # Use original NSPREV value
                        if original_nsprev:
                            original_value = ConfigMerger._get_nested_value(original_nsprev, current_path)
                            if original_value is not None:
                                result[key] = copy.deepcopy(original_value)
                            else:
                                # Original NSPREV doesn't have this field, remove it
                                if key in result:
                                    del result[key]
                    elif strategy == "merge":
                        # Smart merge ENGNEW + DIFF
                        if isinstance(engnew_value, dict) and isinstance(diff_value, dict):
                            result[key] = ConfigMerger._merge_dict_with_strategy(
                                engnew_value, diff_value, strategy
                            )
                        elif isinstance(engnew_value, list) and isinstance(diff_value, list):
                            result[key] = ConfigMerger._merge_list_with_strategy(
                                engnew_value, diff_value, strategy, current_path
                            )
                        else:
                            # Scalar or type mismatch - use ENGNEW
                            pass  # result already has ENGNEW value
                    continue
                
                # No rulebook rule - apply DIFF value (default overlay behavior)
                if isinstance(engnew_value, dict) and isinstance(diff_value, dict):
                    # Recursively merge nested dictionaries
                    result[key] = ConfigMerger._merge_diff_with_rulebook(
                        engnew_value, diff_value, original_nsprev, rulebook, current_path
                    )
                elif isinstance(engnew_value, list) and isinstance(diff_value, list):
                    # Merge lists - use DIFF list but preserve ENGNEW fields that don't exist in DIFF
                    result[key] = ConfigMerger._merge_list_with_diff_overlay(
                        engnew_value, diff_value, original_nsprev, rulebook, current_path
                    )
                else:
                    # Override with DIFF value (including scalars)
                    result[key] = copy.deepcopy(diff_value)
            else:
                # Key doesn't exist in ENGNEW - add from DIFF
                result[key] = copy.deepcopy(diff_value)
        
        # Handle ENGNEW fields that don't exist in DIFF
        # These should be kept from ENGNEW (already in result since we start with ENGNEW)
        # But check if there are any rulebook rules that might override them
        if rulebook and original_nsprev:
            for key, engnew_value in engnew.items():
                if key not in diff:
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if rulebook has a rule for this path
                    if ConfigMerger._has_rulebook_rule(rulebook, current_path):
                        strategy = rulebook.get_merge_strategy(current_path)
                        
                        if strategy == "nsprev":
                            # Use original NSPREV value
                            original_value = ConfigMerger._get_nested_value(original_nsprev, current_path)
                            if original_value is not None:
                                result[key] = copy.deepcopy(original_value)
                            else:
                                # Original NSPREV doesn't have this field, remove it
                                if key in result:
                                    del result[key]
                        elif strategy == "merge":
                            # Smart merge ENGNEW + original NSPREV
                            original_value = ConfigMerger._get_nested_value(original_nsprev, current_path)
                            if original_value is not None:
                                if isinstance(engnew_value, dict) and isinstance(original_value, dict):
                                    result[key] = ConfigMerger._merge_dict_with_strategy(
                                        engnew_value, original_value, strategy
                                    )
                                elif isinstance(engnew_value, list) and isinstance(original_value, list):
                                    result[key] = ConfigMerger._merge_list_with_strategy(
                                        engnew_value, original_value, strategy, current_path
                                    )
                                else:
                                    # Scalar or type mismatch - use ENGNEW
                                    pass  # result already has ENGNEW value
                            # If original NSPREV has no value, keep ENGNEW
                        # engnew strategy already handled by default (keep ENGNEW value)
        
        return result

    @staticmethod
    def _merge_list_with_diff_overlay(
        engnew_list: List[Any], 
        diff_list: List[Any], 
        original_nsprev: Optional[Dict[str, Any]],
        rulebook: Optional[Any],
        path: str
    ) -> List[Any]:
        """
        Merge lists with DIFF overlay, preserving ENGNEW fields that don't exist in DIFF.
        
        Args:
            engnew_list: ENGNEW list
            diff_list: DIFF list
            original_nsprev: Original NSPREV data for fallback
            rulebook: Rulebook manager instance
            path: Current path in the structure
            
        Returns:
            Merged list
        """
        result = []
        
        # Start with DIFF list as base (user customizations)
        for i, diff_item in enumerate(diff_list):
            if i < len(engnew_list):
                # Both lists have this item - merge them
                engnew_item = engnew_list[i]
                if isinstance(engnew_item, dict) and isinstance(diff_item, dict):
                    # Merge dictionaries
                    merged_item = ConfigMerger._merge_diff_with_rulebook(
                        engnew_item, diff_item, original_nsprev, rulebook, f"{path}[{i}]"
                    )
                    result.append(merged_item)
                else:
                    # Non-dict items - use DIFF value
                    result.append(copy.deepcopy(diff_item))
            else:
                # DIFF has more items than ENGNEW - add from DIFF
                result.append(copy.deepcopy(diff_item))
        
        # Add any remaining ENGNEW items that don't exist in DIFF
        for i in range(len(diff_list), len(engnew_list)):
            result.append(copy.deepcopy(engnew_list[i]))
        
        return result

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """
        Get a nested value from a dictionary using dot notation path.
        
        Args:
            data: Dictionary to search
            path: Dot notation path (e.g., "api.externalService.annotations")
            
        Returns:
            Value at path or None if not found
        """
        if not path:
            return data
            
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
                
        return current

    @staticmethod
    def _merge_list_with_strategy(
        engnew_list: List[Any], 
        nsprev_list: List[Any], 
        strategy: str, 
        path: str
    ) -> List[Any]:
        """
        Merge lists based on strategy.
        
        Args:
            engnew_list: ENGNEW list
            nsprev_list: NSPREV list
            strategy: Merge strategy
            path: Field path
            
        Returns:
            Merged list
        """
        if strategy == "engnew":
            return copy.deepcopy(engnew_list)
        elif strategy == "nsprev":
            return copy.deepcopy(nsprev_list)
        elif strategy == "merge":
            return ConfigMerger._smart_merge_list(engnew_list, nsprev_list)
        else:
            return copy.deepcopy(engnew_list)

    @staticmethod
    def _smart_merge_list(engnew_list: List[Any], nsprev_list: List[Any]) -> List[Any]:
        """
        Smart merge two lists by key (for list of dicts).
        
        Args:
            engnew_list: ENGNEW list
            nsprev_list: NSPREV list
            
        Returns:
            Merged list
        """
        if not engnew_list and not nsprev_list:
            return []
        
        if not engnew_list:
            return copy.deepcopy(nsprev_list)
        
        if not nsprev_list:
            return copy.deepcopy(engnew_list)
        
        # Check if these are lists of dictionaries
        if (isinstance(engnew_list[0], dict) and isinstance(nsprev_list[0], dict)):
            return ConfigMerger._merge_list_of_dicts(engnew_list, nsprev_list)
        else:
            # Simple lists - use ENGNEW as base, add unique NSPREV items
            result = copy.deepcopy(engnew_list)
            for item in nsprev_list:
                if item not in result:
                    result.append(copy.deepcopy(item))
            return result

    @staticmethod
    def _merge_list_of_dicts(engnew_list: List[Dict], nsprev_list: List[Dict]) -> List[Dict]:
        """
        Merge two lists of dictionaries by key.
        
        Args:
            engnew_list: ENGNEW list of dicts
            nsprev_list: NSPREV list of dicts
            
        Returns:
            Merged list of dicts
        """
        # Create lookup dictionaries
        engnew_dict = {}
        nsprev_dict = {}
        
        # Build lookups from lists
        for item in engnew_list:
            key = ConfigMerger._get_dict_key(item)
            if key:
                engnew_dict[key] = item
        
        for item in nsprev_list:
            key = ConfigMerger._get_dict_key(item)
            if key:
                nsprev_dict[key] = item
        
        # Start with ENGNEW items
        result = []
        used_keys = set()
        
        # Add all ENGNEW items
        for item in engnew_list:
            key = ConfigMerger._get_dict_key(item)
            if key:
                result.append(copy.deepcopy(item))
                used_keys.add(key)
        
        # Add unique NSPREV items
        for item in nsprev_list:
            key = ConfigMerger._get_dict_key(item)
            if key and key not in used_keys:
                result.append(copy.deepcopy(item))
        
        return result

    @staticmethod
    def _get_dict_key(item: Dict[str, Any]) -> Optional[str]:
        """
        Extract the key from a dictionary item.
        
        Args:
            item: Dictionary item
            
        Returns:
            The key name or None if not found
        """
        if isinstance(item, dict) and len(item) == 1:
            return list(item.keys())[0]
        return None

    @staticmethod
    def _should_apply_strategy_to_dict(
        field_path: str, 
        rulebook: Optional[Any], 
        strategy: str
    ) -> bool:
        """
        Determine if we should apply strategy to a dict field or recurse.
        
        Returns True if:
        - Field path is in path_overrides, OR
        - Field name matches a merge_rules entry with explicit scope
        - Strategy is not the default
        
        Returns False if we should recurse into nested dicts.
        """
        if not rulebook:
            return False
        
        # Check if this path has an explicit override
        path_overrides = rulebook.rules.get('path_overrides', {})
        for override_path in path_overrides:
            if rulebook._path_matches(field_path, override_path):
                return True
        
        # Check if field name matches a merge_rules entry
        field_name = field_path.split('.')[-1]
        merge_rules = rulebook.rules.get('merge_rules', {})
        if field_name in merge_rules:
            return True
        
        return False

    @staticmethod
    def _merge_dict_with_strategy(
        engnew_dict: Dict[str, Any],
        nsprev_dict: Dict[str, Any],
        strategy: str
    ) -> Dict[str, Any]:
        """
        Merge two dictionaries based on strategy.
        
        Args:
            engnew_dict: ENGNEW dictionary
            nsprev_dict: NSPREV dictionary
            strategy: Merge strategy
            
        Returns:
            Merged dictionary
        """
        if strategy == "engnew":
            return copy.deepcopy(engnew_dict)
        elif strategy == "nsprev":
            return copy.deepcopy(nsprev_dict)
        elif strategy == "merge":
            # Merge both: ENGNEW base + NSPREV additions
            result = copy.deepcopy(engnew_dict)
            result.update(copy.deepcopy(nsprev_dict))
            return result
        else:
            return copy.deepcopy(engnew_dict)

    @staticmethod
    def _handle_structural_mismatch(
        engnew_value: Any, 
        nsprev_value: Any, 
        strategy: str, 
        path: str
    ) -> Any:
        """
        Handle structural mismatches between dict and list types.
        
        Args:
            engnew_value: ENGNEW value (dict or list)
            nsprev_value: NSPREV value (dict or list)
            strategy: Merge strategy
            path: Field path
            
        Returns:
            Resolved value
        """
        if strategy == "engnew":
            return copy.deepcopy(engnew_value)
        elif strategy == "nsprev":
            return copy.deepcopy(nsprev_value)
        elif strategy == "merge":
            # For structural mismatches, prefer NSPREV to preserve site-specific structure
            # This is a conservative approach to avoid breaking existing configurations
            return copy.deepcopy(nsprev_value)
        else:
            return copy.deepcopy(nsprev_value)

    @staticmethod
    def _apply_scalar_strategy(engnew_value: Any, nsprev_value: Any, strategy: str) -> Any:
        """
        Apply strategy to scalar values.
        
        Args:
            engnew_value: ENGNEW value
            nsprev_value: NSPREV value
            strategy: Merge strategy
            
        Returns:
            Merged value
        """
        if strategy == "engnew":
            return copy.deepcopy(engnew_value)
        elif strategy == "nsprev":
            return copy.deepcopy(nsprev_value)
        elif strategy == "merge":
            # For scalars, NSPREV takes precedence
            return copy.deepcopy(nsprev_value)
        else:
            return copy.deepcopy(engnew_value)

    @staticmethod
    def _is_list_of_dicts(value: List[Any]) -> bool:
        """
        Check if a list contains dictionaries.
        
        Args:
            value: List to check
            
        Returns:
            True if list contains dicts
        """
        return isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict)

    @staticmethod
    def _normalize_list_format(value: List[Any]) -> List[Any]:
        """
        Normalize list format to ensure proper YAML structure.
        
        Args:
            value: List to normalize
            
        Returns:
            Normalized list
        """
        if not isinstance(value, list):
            return value
        
        # Ensure all items are properly formatted
        normalized = []
        for item in value:
            if isinstance(item, dict):
                # Ensure dict items are properly formatted
                normalized.append(copy.deepcopy(item))
            else:
                normalized.append(copy.deepcopy(item))
        
        return normalized
