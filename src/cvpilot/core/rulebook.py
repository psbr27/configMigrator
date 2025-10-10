"""
Rulebook management for merge strategies.

Handles loading, parsing, validating, and querying merge rules from YAML configuration.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re


class RulebookManager:
    """Manages merge rule configuration and path matching."""
    
    def __init__(self, rulebook_path: Optional[str] = None):
        """
        Initialize rulebook manager.
        
        Args:
            rulebook_path: Path to rulebook YAML file
        """
        self.rulebook_path = rulebook_path
        self.rules = {}
        self.path_cache = {}  # Cache for path matching results
        
        if rulebook_path:
            self.load_rulebook(rulebook_path)
    
    def load_rulebook(self, path: str) -> Dict[str, Any]:
        """
        Load and parse rulebook from YAML file.
        
        Args:
            path: Path to rulebook YAML file
            
        Returns:
            Loaded rulebook dictionary
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.rules = yaml.safe_load(f) or {}
            
            # Validate the rulebook structure
            self._validate_rulebook(self.rules)
            
            return self.rules
        except FileNotFoundError:
            raise FileNotFoundError(f"Rulebook file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in rulebook: {e}")
        except Exception as e:
            raise ValueError(f"Error loading rulebook: {e}")
    
    def get_merge_strategy(self, field_path: str) -> str:
        """
        Determine merge strategy for a given field path.
        
        Priority order:
        1. path_overrides (highest priority)
        2. merge_rules with scope: specific
        3. merge_rules with scope: global
        4. default_strategy (lowest priority)
        
        Args:
            field_path: Path to the field (e.g., "mgm.annotations")
            
        Returns:
            Merge strategy: "engnew", "nsprev", or "merge"
        """
        # Check cache first
        if field_path in self.path_cache:
            return self.path_cache[field_path]
        
        strategy = None
        
        # 1. Check path_overrides (highest priority)
        path_overrides = self.rules.get('path_overrides', {})
        for override_path, override_config in path_overrides.items():
            if self._path_matches(field_path, override_path):
                strategy = override_config.get('strategy')
                break
        
        # 2. Check merge_rules with specific scope
        if not strategy:
            merge_rules = self.rules.get('merge_rules', {})
            for rule_name, rule_config in merge_rules.items():
                if rule_config.get('scope') == 'specific':
                    paths = rule_config.get('paths', [])
                    if any(self._path_matches(field_path, path) for path in paths):
                        strategy = rule_config.get('strategy')
                        break
        
        # 3. Check merge_rules with global scope
        if not strategy:
            field_name = field_path.split('.')[-1].lower()
            merge_rules = self.rules.get('merge_rules', {})
            
            for rule_name, rule_config in merge_rules.items():
                if rule_config.get('scope') == 'global':
                    # Check if field name matches rule name
                    if (rule_name.lower() in field_name or 
                        field_name in rule_name.lower() or
                        self._field_name_matches(field_name, rule_name)):
                        strategy = rule_config.get('strategy')
                        break
        
        # 4. Use default strategy
        if not strategy:
            strategy = self.rules.get('default_strategy', 'engnew')
        
        # Cache the result
        self.path_cache[field_path] = strategy
        return strategy
    
    def _path_matches(self, field_path: str, pattern: str) -> bool:
        """
        Check if a field path matches a pattern.
        
        Supports:
        - Exact matches: "mgm.annotations"
        - Wildcard arrays: "api.externalService.sqlgeorepsvclabels[*].labels"
        - Field wildcards: "*.annotations"
        
        Args:
            field_path: Path to check
            pattern: Pattern to match against
            
        Returns:
            True if path matches pattern
        """
        # Handle wildcard patterns
        if '*' in pattern:
            # Convert pattern to regex
            regex_pattern = pattern.replace('[*]', r'\[\d+\]')  # Array wildcard
            regex_pattern = regex_pattern.replace('*', r'[^.]+')  # Field wildcard
            regex_pattern = f"^{regex_pattern}$"
            
            try:
                return bool(re.match(regex_pattern, field_path))
            except re.error:
                return False
        
        # Exact match
        return field_path == pattern
    
    def _field_name_matches(self, field_name: str, rule_name: str) -> bool:
        """
        Check if a field name matches a rule name with fuzzy matching.
        
        Args:
            field_name: Name of the field
            rule_name: Name of the rule
            
        Returns:
            True if names match
        """
        # Direct match
        if field_name == rule_name:
            return True
        
        # Check if rule name is contained in field name
        if rule_name.lower() in field_name.lower():
            return True
        
        # Check if field name is contained in rule name
        if field_name.lower() in rule_name.lower():
            return True
        
        # Check for common variations
        field_variations = [field_name, field_name + 's', field_name[:-1] if field_name.endswith('s') else field_name]
        rule_variations = [rule_name, rule_name + 's', rule_name[:-1] if rule_name.endswith('s') else rule_name]
        
        for field_var in field_variations:
            for rule_var in rule_variations:
                if field_var.lower() == rule_var.lower():
                    return True
        
        return False
    
    def _validate_rulebook(self, rules: Dict[str, Any]) -> None:
        """
        Validate rulebook structure and content.
        
        Args:
            rules: Rulebook dictionary to validate
            
        Raises:
            ValueError: If rulebook is invalid
        """
        if not isinstance(rules, dict):
            raise ValueError("Rulebook must be a dictionary")
        
        # Validate default_strategy
        default_strategy = rules.get('default_strategy', 'engnew')
        if default_strategy not in ['engnew', 'nsprev', 'merge']:
            raise ValueError(f"Invalid default_strategy: {default_strategy}")
        
        # Validate merge_rules
        merge_rules = rules.get('merge_rules', {})
        if not isinstance(merge_rules, dict):
            raise ValueError("merge_rules must be a dictionary")
        
        for rule_name, rule_config in merge_rules.items():
            if not isinstance(rule_config, dict):
                raise ValueError(f"Rule '{rule_name}' must be a dictionary")
            
            strategy = rule_config.get('strategy')
            if strategy not in ['engnew', 'nsprev', 'merge']:
                raise ValueError(f"Invalid strategy for rule '{rule_name}': {strategy}")
            
            scope = rule_config.get('scope')
            if scope not in ['global', 'specific']:
                raise ValueError(f"Invalid scope for rule '{rule_name}': {scope}")
            
            if scope == 'specific':
                paths = rule_config.get('paths', [])
                if not isinstance(paths, list):
                    raise ValueError(f"Paths for rule '{rule_name}' must be a list")
        
        # Validate path_overrides
        path_overrides = rules.get('path_overrides', {})
        if not isinstance(path_overrides, dict):
            raise ValueError("path_overrides must be a dictionary")
        
        for path, override_config in path_overrides.items():
            if not isinstance(override_config, dict):
                raise ValueError(f"Override for path '{path}' must be a dictionary")
            
            strategy = override_config.get('strategy')
            if strategy not in ['engnew', 'nsprev', 'merge']:
                raise ValueError(f"Invalid strategy for path override '{path}': {strategy}")
    
    def create_default_rulebook(self) -> Dict[str, Any]:
        """
        Create a default rulebook template.
        
        Returns:
            Default rulebook dictionary
        """
        return {
            'default_strategy': 'engnew',
            'merge_rules': {
                'annotations': {
                    'strategy': 'merge',
                    'scope': 'global'
                },
                'commonlabels': {
                    'strategy': 'merge',
                    'scope': 'global'
                },
                'labels': {
                    'strategy': 'engnew',
                    'scope': 'global'
                },
                'podAnnotations': {
                    'strategy': 'merge',
                    'scope': 'global'
                },
                'egressannotations': {
                    'strategy': 'merge',
                    'scope': 'global'
                }
            },
            'path_overrides': {}
        }
    
    def save_rulebook(self, output_path: str) -> None:
        """
        Save current rules to a YAML file.
        
        Args:
            output_path: Path to save the rulebook
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.rules, f, default_flow_style=False, sort_keys=False)
    
    def add_path_override(self, path: str, strategy: str) -> None:
        """
        Add a path-specific override.
        
        Args:
            path: Field path
            strategy: Merge strategy
        """
        if 'path_overrides' not in self.rules:
            self.rules['path_overrides'] = {}
        
        self.rules['path_overrides'][path] = {'strategy': strategy}
        
        # Clear cache for this path
        if path in self.path_cache:
            del self.path_cache[path]
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current rules.
        
        Returns:
            Summary dictionary
        """
        merge_rules = self.rules.get('merge_rules', {})
        path_overrides = self.rules.get('path_overrides', {})
        
        return {
            'default_strategy': self.rules.get('default_strategy', 'engnew'),
            'global_rules': len([r for r in merge_rules.values() if r.get('scope') == 'global']),
            'specific_rules': len([r for r in merge_rules.values() if r.get('scope') == 'specific']),
            'path_overrides': len(path_overrides),
            'total_rules': len(merge_rules) + len(path_overrides)
        }
