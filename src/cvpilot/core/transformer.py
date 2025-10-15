"""
Path transformation detection and resolution.

Implements Stage 3 of the migration workflow to detect when configuration values
appear in multiple paths (indicating structural changes between versions) and
provides interactive resolution.
"""

import copy
from typing import Any, Dict, List, Optional
from collections import defaultdict


class TransformationRecord:
    """Represents a detected path transformation."""
    
    def __init__(
        self,
        old_path: str,
        new_path: str,
        value: Any,
        recommendation: str,
        reason: str,
        confidence: str
    ):
        """
        Initialize transformation record.
        
        Args:
            old_path: Original path where value was found
            new_path: New path where value appears
            value: The duplicate value
            recommendation: Suggested action (move|keep_both|remove_old)
            reason: Explanation for the recommendation
            confidence: Confidence level (high|medium|low)
        """
        self.old_path = old_path
        self.new_path = new_path
        self.value = value
        self.recommendation = recommendation
        self.reason = reason
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'old_path': self.old_path,
            'new_path': self.new_path,
            'value': self.value,
            'recommendation': self.recommendation,
            'reason': self.reason,
            'confidence': self.confidence
        }
    
    def __repr__(self) -> str:
        return f"TransformationRecord({self.old_path} → {self.new_path})"


class PathTransformationDetector:
    """Detects and resolves path transformations in merged configurations."""
    
    def __init__(self):
        """Initialize the detector."""
        self.path_value_map: Dict[str, Any] = {}
        self.value_paths_map: Dict[str, List[str]] = defaultdict(list)
    
    def detect_duplicate_values(
        self,
        merged_config: Dict[str, Any],
        reference_config: Dict[str, Any]
    ) -> List[TransformationRecord]:
        """
        Detect duplicate values across different paths in merged configuration.
        
        Args:
            merged_config: The merged output from Stage 2
            reference_config: The ENGNEW reference configuration
            
        Returns:
            List of detected transformation records
        """
        # Build path-value mappings
        self._build_path_value_map(merged_config, "")
        
        # Find duplicate values across different paths
        duplicate_groups = self._find_duplicate_value_groups()
        
        # Generate transformation records
        transformations = []
        for value_key, paths in duplicate_groups.items():
            if len(paths) >= 2:
                # Compare against reference to determine correct structure
                records = self._analyze_duplicate_paths(
                    paths, 
                    self.path_value_map,
                    reference_config
                )
                transformations.extend(records)
        
        # Detect parent object transformations
        parent_transformations = self._detect_parent_object_transformations(
            transformations,
            merged_config,
            reference_config
        )
        
        # Filter out child transformations when parent is being transformed
        if parent_transformations:
            parent_paths = {pt.old_path for pt in parent_transformations}
            transformations = [
                t for t in transformations
                if not self._is_child_of_any(t.old_path, parent_paths)
            ]
        
        transformations.extend(parent_transformations)
        
        return transformations
    
    def _build_path_value_map(
        self,
        data: Any,
        current_path: str,
        parent_key: str = ""
    ) -> None:
        """
        Recursively build mapping of paths to values.
        
        Args:
            data: Current data node
            current_path: Current path in dot notation
            parent_key: Parent key name for context
        """
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                
                if isinstance(value, (dict, list)):
                    # Recurse into nested structures
                    self._build_path_value_map(value, new_path, key)
                else:
                    # Store leaf values
                    self.path_value_map[new_path] = value
                    
                    # Create hashable key for value tracking
                    # Only track non-empty, non-null scalar values
                    if value is not None and value != "" and value != {}:
                        value_key = self._make_value_key(value, key)
                        self.value_paths_map[value_key].append(new_path)
        
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_path = f"{current_path}[{idx}]"
                
                if isinstance(item, (dict, list)):
                    self._build_path_value_map(item, new_path, parent_key)
                else:
                    # Store leaf values
                    self.path_value_map[new_path] = item
                    
                    if item is not None and item != "" and item != {}:
                        value_key = self._make_value_key(item, parent_key)
                        self.value_paths_map[value_key].append(new_path)
    
    def _make_value_key(self, value: Any, context: str = "") -> str:
        """
        Create a hashable key for value tracking.
        
        Args:
            value: The value to create key for
            context: Context (field name) for disambiguation
            
        Returns:
            String key for value tracking
        """
        # Include context to avoid false positives with common values
        return f"{context}:{str(value)}"
    
    def _find_duplicate_value_groups(self) -> Dict[str, List[str]]:
        """
        Find groups of paths that share the same value.
        
        Returns:
            Dictionary mapping value keys to lists of paths
        """
        # Filter to only values that appear in multiple paths
        return {
            value_key: paths
            for value_key, paths in self.value_paths_map.items()
            if len(paths) >= 2
        }
    
    def _detect_parent_object_transformations(
        self,
        field_transformations: List[TransformationRecord],
        merged_config: Dict[str, Any],
        reference_config: Dict[str, Any]
    ) -> List[TransformationRecord]:
        """
        Detect when entire parent objects should be removed because their children
        have been transformed.
        
        Args:
            field_transformations: List of field-level transformations
            merged_config: The merged configuration
            reference_config: The ENGNEW reference
            
        Returns:
            List of parent object transformation records
        """
        parent_transformations = []
        
        # Group transformations by parent path
        parent_groups = defaultdict(list)
        for trans in field_transformations:
            if trans.recommendation == 'move':
                parent_path = self._get_parent_path(trans.old_path)
                if parent_path:  # Only if there is a parent
                    parent_groups[parent_path].append(trans)
        
        # Check each parent
        for parent_path, child_transformations in parent_groups.items():
            # Get all fields under this parent in merged config
            parent_obj = self._get_value_at_path(merged_config, parent_path)
            
            if not isinstance(parent_obj, dict):
                continue  # Only process dict objects
            
            # Count total fields in parent
            total_fields = self._count_leaf_fields(parent_obj)
            transformed_fields = len(child_transformations)
            
            # If 50% or more fields are transformed, suggest removing parent
            if total_fields > 0 and transformed_fields / total_fields >= 0.5:
                # Check if parent exists in reference
                parent_exists_in_ref = self._path_exists_in_config(parent_path, reference_config)
                
                if not parent_exists_in_ref:
                    # Parent doesn't exist in reference - should be removed
                    # Find a representative new path from child transformations
                    representative_new_path = self._get_representative_new_path(child_transformations)
                    
                    parent_transformations.append(TransformationRecord(
                        old_path=parent_path,
                        new_path=representative_new_path,
                        value=f"[Object with {total_fields} field(s)]",
                        recommendation='move',
                        reason=f'{transformed_fields}/{total_fields} child fields transformed, parent not in ENGNEW',
                        confidence='high'
                    ))
        
        return parent_transformations
    
    def _get_parent_path(self, path: str) -> Optional[str]:
        """
        Get the parent path of a given path.
        
        Args:
            path: Path string
            
        Returns:
            Parent path or None if no parent
        """
        if '.' not in path and '[' not in path:
            return None
        
        # Handle array indices
        if '[' in path:
            # Remove array index and everything after
            parts = path.split('[')
            base = parts[0]
            if '.' in base:
                return '.'.join(base.split('.')[:-1])
            return None
        
        # Simple dot notation
        parts = path.split('.')
        if len(parts) > 1:
            return '.'.join(parts[:-1])
        
        return None
    
    def _get_value_at_path(self, config: Dict[str, Any], path: str) -> Any:
        """
        Get value at a specific path in config.
        
        Args:
            config: Configuration dictionary
            path: Path to value
            
        Returns:
            Value at path or None
        """
        try:
            current = config
            segments = self._parse_path_segments(path)
            
            for segment in segments:
                if isinstance(segment, int):
                    current = current[segment]
                else:
                    current = current[segment]
            
            return current
        except (KeyError, IndexError, TypeError):
            return None
    
    def _set_value_at_path(
        self, 
        config: Dict[str, Any], 
        path: str, 
        value: Any
    ) -> Dict[str, Any]:
        """
        Set value at a specific path in config.
        
        Args:
            config: Configuration dictionary
            path: Path to set value at
            value: Value to set
            
        Returns:
            Modified configuration
        """
        try:
            result = copy.deepcopy(config)
            segments = self._parse_path_segments(path)
            
            if not segments:
                return result
            
            # Navigate to parent
            current = result
            for segment in segments[:-1]:
                if isinstance(segment, int):
                    current = current[segment]
                else:
                    current = current[segment]
            
            # Set the value
            last_segment = segments[-1]
            if isinstance(last_segment, int):
                if isinstance(current, list) and 0 <= last_segment < len(current):
                    current[last_segment] = value
            else:
                if isinstance(current, dict):
                    current[last_segment] = value
            
            return result
        except (KeyError, IndexError, TypeError):
            # Path doesn't exist, return unchanged
            return config
    
    def _count_leaf_fields(self, obj: Any) -> int:
        """
        Count the number of leaf (scalar) fields in an object.
        
        Args:
            obj: Object to count fields in
            
        Returns:
            Number of leaf fields
        """
        if not isinstance(obj, dict):
            return 0
        
        count = 0
        for value in obj.values():
            if isinstance(value, dict):
                count += self._count_leaf_fields(value)
            elif isinstance(value, list):
                # For lists, count each item
                for item in value:
                    if isinstance(item, dict):
                        count += self._count_leaf_fields(item)
                    else:
                        count += 1
            else:
                count += 1
        
        return count
    
    def _get_representative_new_path(self, transformations: List[TransformationRecord]) -> str:
        """
        Get a representative new path from a list of transformations.
        
        Args:
            transformations: List of transformation records
            
        Returns:
            Representative new path (parent of new paths)
        """
        if not transformations:
            return "[unknown]"
        
        # Get the common parent of all new paths
        first_new_path = transformations[0].new_path
        parent = self._get_parent_path(first_new_path)
        
        if parent:
            return f"{parent}.*"
        
        return first_new_path
    
    def _is_child_of_any(self, path: str, parent_paths: set) -> bool:
        """
        Check if a path is a child of any parent path.
        
        Args:
            path: Path to check
            parent_paths: Set of potential parent paths
            
        Returns:
            True if path is a child of any parent path
        """
        for parent_path in parent_paths:
            if self._is_child_of(path, parent_path):
                return True
        return False
    
    def _is_child_of(self, child_path: str, parent_path: str) -> bool:
        """
        Check if a path is a child of a parent path.
        
        Args:
            child_path: Potential child path
            parent_path: Potential parent path
            
        Returns:
            True if child_path is under parent_path
        """
        # Child must start with parent path followed by a dot or bracket
        if child_path == parent_path:
            return False  # Same path, not a child
        
        return (child_path.startswith(parent_path + '.') or 
                child_path.startswith(parent_path + '['))
    
    def _analyze_duplicate_paths(
        self,
        paths: List[str],
        path_value_map: Dict[str, Any],
        reference_config: Dict[str, Any]
    ) -> List[TransformationRecord]:
        """
        Analyze duplicate paths and generate transformation records.
        
        Args:
            paths: List of paths with duplicate values
            path_value_map: Mapping of paths to values
            reference_config: ENGNEW reference configuration
            
        Returns:
            List of transformation records
        """
        transformations = []
        
        # Get the shared value
        value = path_value_map[paths[0]]
        
        # Check which paths exist in reference config
        paths_in_reference = []
        paths_not_in_reference = []
        
        for path in paths:
            if self._path_exists_in_config(path, reference_config):
                paths_in_reference.append(path)
            else:
                paths_not_in_reference.append(path)
        
        # Determine transformation based on reference structure
        if len(paths_in_reference) == 1 and len(paths_not_in_reference) >= 1:
            # Clear case: one path exists in reference (new), others don't (old)
            new_path = paths_in_reference[0]
            for old_path in paths_not_in_reference:
                transformations.append(TransformationRecord(
                    old_path=old_path,
                    new_path=new_path,
                    value=value,
                    recommendation='move',
                    reason='new_path exists in ENGNEW reference, old_path does not',
                    confidence='high'
                ))
        
        elif len(paths_in_reference) >= 2:
            # Both paths exist in reference - might be intentional duplication
            # Sort paths to have consistent ordering
            sorted_paths = sorted(paths)
            for i in range(len(sorted_paths) - 1):
                transformations.append(TransformationRecord(
                    old_path=sorted_paths[i],
                    new_path=sorted_paths[i + 1],
                    value=value,
                    recommendation='keep_both',
                    reason='both paths exist in ENGNEW reference',
                    confidence='medium'
                ))
        
        elif len(paths_not_in_reference) >= 2:
            # Neither path exists in reference - unclear situation
            sorted_paths = sorted(paths)
            for i in range(len(sorted_paths) - 1):
                transformations.append(TransformationRecord(
                    old_path=sorted_paths[i],
                    new_path=sorted_paths[i + 1],
                    value=value,
                    recommendation='keep_both',
                    reason='neither path exists in ENGNEW reference - manual review needed',
                    confidence='low'
                ))
        
        return transformations
    
    def _path_exists_in_config(self, path: str, config: Dict[str, Any]) -> bool:
        """
        Check if a path exists in the configuration.
        
        Args:
            path: Dot-notation path (e.g., "api.service.name" or "list[0].key")
            config: Configuration dictionary to check
            
        Returns:
            True if path exists in config
        """
        try:
            current = config
            
            # Parse path segments (handle both dots and array indices)
            segments = self._parse_path_segments(path)
            
            for segment in segments:
                if isinstance(segment, int):
                    # Array index
                    if isinstance(current, list) and 0 <= segment < len(current):
                        current = current[segment]
                    else:
                        return False
                else:
                    # Dictionary key
                    if isinstance(current, dict) and segment in current:
                        current = current[segment]
                    else:
                        return False
            
            return True
        
        except (KeyError, IndexError, TypeError):
            return False
    
    def _parse_path_segments(self, path: str) -> List[Any]:
        """
        Parse path string into segments (keys and indices).
        
        Args:
            path: Path string (e.g., "api.list[0].name")
            
        Returns:
            List of segments (strings for keys, ints for indices)
        """
        import re
        segments = []
        
        # Split on dots, but handle array indices
        parts = path.split('.')
        for part in parts:
            # Check if part contains array index
            match = re.match(r'([^\[]+)\[(\d+)\]', part)
            if match:
                # Part with array index: "list[0]"
                segments.append(match.group(1))  # key
                segments.append(int(match.group(2)))  # index
            else:
                # Simple key
                segments.append(part)
        
        return segments
    
    def apply_transformations(
        self,
        config: Dict[str, Any],
        transformations: List[TransformationRecord]
    ) -> Dict[str, Any]:
        """
        Apply selected transformations to the configuration.
        
        Args:
            config: Configuration to transform
            transformations: List of transformation records to apply
            
        Returns:
            Transformed configuration
        """
        result = copy.deepcopy(config)
        
        # Sort transformations: parent objects first, then child fields
        # This ensures we don't try to remove child fields of already-removed parents
        sorted_transformations = sorted(
            transformations,
            key=lambda t: (t.old_path.count('.'), t.old_path)
        )
        
        for transformation in sorted_transformations:
            if transformation.recommendation == 'move':
                # Check if path still exists (parent might have been removed)
                if self._path_exists_in_config(transformation.old_path, result):
                    # Move value from old path to new path and remove old path
                    result = self._move_value(
                        result,
                        transformation.old_path,
                        transformation.new_path,
                        transformation.value
                    )
            elif transformation.recommendation == 'remove_old':
                # Only remove old path
                if self._path_exists_in_config(transformation.old_path, result):
                    result = self._remove_path(result, transformation.old_path)
        
        return result
    
    def _move_value(
        self,
        config: Dict[str, Any],
        old_path: str,
        new_path: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Move a value from old path to new path.
        
        Args:
            config: Configuration dictionary
            old_path: Source path
            new_path: Destination path (may include wildcards like *)
            value: Value to move
            
        Returns:
            Modified configuration
        """
        result = copy.deepcopy(config)
        
        # For parent object transformations, get the actual object
        if "[Object with" in str(value):
            # This is a parent object transformation
            old_value = self._get_value_at_path(result, old_path)
            if old_value and isinstance(old_value, dict):
                # Try to intelligently merge values to new location
                # For now, we'll log this but not auto-transfer complex objects
                # The new structure should already have correct values from Stage 2
                pass
        else:
            # Single field transformation - ensure value is at new path
            # Get actual value from old path
            old_value = self._get_value_at_path(result, old_path)
            if old_value is not None:
                # Try to set value at new path if it exists
                result = self._set_value_at_path(result, new_path, old_value)
        
        # Remove old path
        result = self._remove_path(result, old_path)
        
        return result
    
    def _remove_path(
        self,
        config: Dict[str, Any],
        path: str
    ) -> Dict[str, Any]:
        """
        Remove a path from configuration.
        
        Args:
            config: Configuration dictionary
            path: Path to remove
            
        Returns:
            Modified configuration
        """
        result = copy.deepcopy(config)
        
        try:
            segments = self._parse_path_segments(path)
            
            # Navigate to parent
            current = result
            parents = [result]
            
            for i, segment in enumerate(segments[:-1]):
                if isinstance(segment, int):
                    current = current[segment]
                else:
                    current = current[segment]
                parents.append(current)
            
            # Remove the last segment
            last_segment = segments[-1]
            if isinstance(last_segment, int):
                if isinstance(current, list) and 0 <= last_segment < len(current):
                    del current[last_segment]
            else:
                if isinstance(current, dict) and last_segment in current:
                    del current[last_segment]
            
            # Clean up empty parents
            self._cleanup_empty_parents(result, segments[:-1])
        
        except (KeyError, IndexError, TypeError):
            # Path doesn't exist, nothing to remove
            pass
        
        return result
    
    def _cleanup_empty_parents(
        self,
        config: Dict[str, Any],
        parent_segments: List[Any]
    ) -> None:
        """
        Remove empty parent dictionaries after path removal.
        
        Args:
            config: Root configuration
            parent_segments: Segments leading to the removed path
        """
        # Work backwards through parent segments
        for i in range(len(parent_segments) - 1, -1, -1):
            try:
                current = config
                
                # Navigate to the parent
                for segment in parent_segments[:i]:
                    if isinstance(segment, int):
                        current = current[segment]
                    else:
                        current = current[segment]
                
                # Check if the target is empty
                target_segment = parent_segments[i]
                if isinstance(target_segment, int):
                    if isinstance(current, list) and 0 <= target_segment < len(current):
                        if not current[target_segment]:  # Empty dict or list
                            del current[target_segment]
                else:
                    if isinstance(current, dict) and target_segment in current:
                        target = current[target_segment]
                        if isinstance(target, dict) and not target:
                            del current[target_segment]
                        elif isinstance(target, list) and not target:
                            del current[target_segment]
            
            except (KeyError, IndexError, TypeError):
                break
    
    def generate_transformation_report(
        self,
        transformations: List[TransformationRecord]
    ) -> str:
        """
        Generate a human-readable report of detected transformations.
        
        Args:
            transformations: List of transformation records
            
        Returns:
            Formatted report string
        """
        if not transformations:
            return "No path transformations detected."
        
        report_lines = [
            f"\nDetected {len(transformations)} potential path transformation(s):\n"
        ]
        
        for i, t in enumerate(transformations, 1):
            report_lines.append(f"{i}. {t.old_path} → {t.new_path}")
            report_lines.append(f"   Value: {t.value}")
            report_lines.append(f"   Recommendation: {t.recommendation}")
            report_lines.append(f"   Reason: {t.reason}")
            report_lines.append(f"   Confidence: {t.confidence}\n")
        
        return "\n".join(report_lines)

