"""
Path matching utilities for YAML field paths.

Supports exact paths, wildcards, array indices, and nested patterns.
"""

import re
from typing import List, Set, Optional, Union


class PathMatcher:
    """Handles path matching for YAML field paths."""
    
    @staticmethod
    def match_path(field_path: str, pattern: str) -> bool:
        """
        Check if a field path matches a pattern.
        
        Args:
            field_path: Path to check (e.g., "mgm.annotations")
            pattern: Pattern to match (e.g., "mgm.annotations", "*.annotations", "api.externalService.sqlgeorepsvclabels[*].labels")
            
        Returns:
            True if path matches pattern
        """
        # Exact match
        if field_path == pattern:
            return True
        
        # Handle wildcard patterns
        if '*' in pattern:
            return PathMatcher._match_wildcard(field_path, pattern)
        
        return False
    
    @staticmethod
    def _match_wildcard(field_path: str, pattern: str) -> bool:
        """
        Match field path against wildcard pattern.
        
        Args:
            field_path: Path to check
            pattern: Pattern with wildcards
            
        Returns:
            True if matches
        """
        # Convert pattern to regex
        regex_pattern = pattern
        
        # Handle array wildcards [*] -> [\d+]
        regex_pattern = regex_pattern.replace('[*]', r'\[\d+\]')
        
        # Handle field wildcards * -> [^.]+
        regex_pattern = regex_pattern.replace('*', r'[^.]+')
        
        # Escape other regex special characters
        regex_pattern = re.escape(regex_pattern)
        regex_pattern = regex_pattern.replace(r'\[\\d\+\]', r'\[\d+\]')
        regex_pattern = regex_pattern.replace(r'\[\.\]\+', r'[^.]+')
        
        # Add anchors
        regex_pattern = f"^{regex_pattern}$"
        
        try:
            return bool(re.match(regex_pattern, field_path))
        except re.error:
            return False
    
    @staticmethod
    def find_matching_paths(paths: List[str], pattern: str) -> List[str]:
        """
        Find all paths that match a pattern.
        
        Args:
            paths: List of paths to search
            pattern: Pattern to match
            
        Returns:
            List of matching paths
        """
        return [path for path in paths if PathMatcher.match_path(path, pattern)]
    
    @staticmethod
    def extract_field_name(path: str) -> str:
        """
        Extract the field name from a path.
        
        Args:
            path: Field path (e.g., "mgm.annotations")
            
        Returns:
            Field name (e.g., "annotations")
        """
        return path.split('.')[-1]
    
    @staticmethod
    def extract_parent_path(path: str) -> str:
        """
        Extract the parent path from a field path.
        
        Args:
            path: Field path (e.g., "mgm.annotations")
            
        Returns:
            Parent path (e.g., "mgm")
        """
        parts = path.split('.')
        return '.'.join(parts[:-1]) if len(parts) > 1 else ''
    
    @staticmethod
    def is_array_path(path: str) -> bool:
        """
        Check if a path contains array indices.
        
        Args:
            path: Field path
            
        Returns:
            True if path contains array indices
        """
        return '[' in path and ']' in path
    
    @staticmethod
    def normalize_array_path(path: str) -> str:
        """
        Normalize array path by replacing indices with wildcards.
        
        Args:
            path: Field path with array indices
            
        Returns:
            Normalized path with wildcards
        """
        # Replace [0], [1], [2], etc. with [*]
        return re.sub(r'\[\d+\]', '[*]', path)
    
    @staticmethod
    def get_array_paths(paths: List[str]) -> Set[str]:
        """
        Get all unique array paths (normalized) from a list of paths.
        
        Args:
            paths: List of field paths
            
        Returns:
            Set of normalized array paths
        """
        array_paths = set()
        for path in paths:
            if PathMatcher.is_array_path(path):
                normalized = PathMatcher.normalize_array_path(path)
                array_paths.add(normalized)
        return array_paths
    
    @staticmethod
    def group_by_field_type(paths: List[str]) -> dict:
        """
        Group paths by field type (annotations, labels, etc.).
        
        Args:
            paths: List of field paths
            
        Returns:
            Dictionary mapping field types to lists of paths
        """
        groups = {}
        
        for path in paths:
            field_name = PathMatcher.extract_field_name(path).lower()
            
            # Determine field type
            field_type = None
            if 'annotation' in field_name:
                field_type = 'annotations'
            elif 'label' in field_name:
                field_type = 'labels'
            elif 'commonlabel' in field_name:
                field_type = 'commonlabels'
            else:
                field_type = field_name
            
            if field_type not in groups:
                groups[field_type] = []
            groups[field_type].append(path)
        
        return groups
    
    @staticmethod
    def suggest_patterns(paths: List[str]) -> List[str]:
        """
        Suggest useful patterns based on common path structures.
        
        Args:
            paths: List of field paths
            
        Returns:
            List of suggested patterns
        """
        patterns = set()
        
        # Group by field type
        field_groups = PathMatcher.group_by_field_type(paths)
        
        for field_type, type_paths in field_groups.items():
            if len(type_paths) > 1:
                # Suggest wildcard pattern for this field type
                patterns.add(f"*.{field_type}")
        
        # Group by parent paths
        parent_groups = {}
        for path in paths:
            parent = PathMatcher.extract_parent_path(path)
            if parent:
                if parent not in parent_groups:
                    parent_groups[parent] = []
                parent_groups[parent].append(path)
        
        for parent, parent_paths in parent_groups.items():
            if len(parent_paths) > 1:
                # Suggest pattern for this parent
                field_name = PathMatcher.extract_field_name(parent_paths[0])
                patterns.add(f"{parent}.{field_name}")
        
        return sorted(patterns)
