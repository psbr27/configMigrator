"""
Dynamic analysis engine for generating merge rules.

Analyzes NSPREV and ENGNEW files to detect conflicts and generate intelligent
merge strategy suggestions for list-type fields (annotations, labels, etc.).
"""

import copy
from typing import Any, Dict, List, Set, Tuple, Optional
from pathlib import Path
from enum import Enum


class ComponentType(Enum):
    """Enumeration of supported Oracle Communications components."""
    NRF = "ocnrf"
    CNDBTIER = "occndbtier"
    UDR = "ocudr"
    UDM = "ocudm"
    AUSF = "ocausf"
    NSSF = "ocnssf"
    PCF = "ocpcf"
    UNKNOWN = "unknown"

    @classmethod
    def detect_from_filename(cls, filename: str) -> 'ComponentType':
        """
        Detect component type from filename.

        Args:
            filename: YAML filename

        Returns:
            Detected component type
        """
        filename_lower = filename.lower()

        if "ocnrf" in filename_lower or "nrf" in filename_lower:
            return cls.NRF
        elif "occndbtier" in filename_lower or "cndbtier" in filename_lower:
            return cls.CNDBTIER
        elif "ocudr" in filename_lower or "udr" in filename_lower:
            return cls.UDR
        elif "ocudm" in filename_lower or "udm" in filename_lower:
            return cls.UDM
        elif "ocausf" in filename_lower or "ausf" in filename_lower:
            return cls.AUSF
        elif "ocnssf" in filename_lower or "nssf" in filename_lower:
            return cls.NSSF
        elif "ocpcf" in filename_lower or "pcf" in filename_lower:
            return cls.PCF
        else:
            return cls.UNKNOWN

    @classmethod
    def detect_from_content(cls, data: Dict[str, Any]) -> 'ComponentType':
        """
        Detect component type from YAML content.

        Args:
            data: YAML data dictionary

        Returns:
            Detected component type
        """
        # Check for component-specific markers in global section
        global_section = data.get('global', {})

        # NRF-specific markers
        if 'nrfTag' in global_section or 'nrfInstanceId' in global_section:
            return cls.NRF

        # Check for NRF microservices
        nrf_services = [
            'nfregistration', 'nfsubscription', 'nfdiscovery',
            'nfaccesstoken', 'nrfconfiguration', 'nrfauditor'
        ]
        if any(service in data for service in nrf_services):
            return cls.NRF

        # Check for ingress/egress gateway pattern (NRF)
        if 'ingress-gateway' in data or 'egress-gateway' in data:
            return cls.NRF

        # CNDBTIER-specific markers
        if any(key.startswith('mysql') for key in data.keys()):
            return cls.CNDBTIER

        # Check for CNDBTIER namespace or service indicators
        if 'occne-cndbtier' in str(data).lower():
            return cls.CNDBTIER

        # Check for CNDBTIER-specific configuration patterns
        if (global_section.get('mgmReplicaCount') is not None or
            global_section.get('ndbReplicaCount') is not None or
            global_section.get('namespace') == 'occne-cndbtier'):
            return cls.CNDBTIER

        return cls.UNKNOWN


class ConflictAnalyzer:
    """Analyzes YAML files to detect conflicts and suggest merge strategies."""

    # Base list-type fields that should be analyzed for conflicts
    BASE_LIST_FIELD_NAMES = {
        'annotations', 'commonlabels', 'labels', 'podAnnotations',
        'egressannotations', 'service.labels', 'sqlgeorepsvclabels'
    }

    # NRF-specific fields that should be analyzed
    NRF_SPECIFIC_FIELDS = {
        'ingress-gateway', 'egress-gateway', 'nfregistration', 'nfsubscription',
        'nfdiscovery', 'nfaccesstoken', 'nrfconfiguration', 'nrfauditor',
        'mysql.primary', 'mysql.secondary', 'appValidate', 'errorResponseDueToEgwOverload',
        'deprecatedList', 'relaxValidations'
    }

    # Component-specific field sets
    COMPONENT_FIELDS = {
        ComponentType.NRF: BASE_LIST_FIELD_NAMES | NRF_SPECIFIC_FIELDS,
        ComponentType.CNDBTIER: BASE_LIST_FIELD_NAMES | {'mysql', 'database'},
        ComponentType.UNKNOWN: BASE_LIST_FIELD_NAMES
    }

    # Patterns that suggest site-specific content
    SITE_SPECIFIC_PATTERNS = {
        'vz.webscale.com', 'cis.f5.com', 'oracle.com.cnc',
        'sidecar.istio.io', 'traffic.sidecar.istio.io',
        # NRF-specific site patterns
        'customer.oracle.com', 'nrf.customer.com', 'prod.nrf'
    }

    def __init__(self):
        self.conflicts = []
        self.suggestions = {}
        self.detected_component = ComponentType.UNKNOWN
        self.list_field_names = self.BASE_LIST_FIELD_NAMES
    
    def analyze_files(self, nsprev_path: str, engnew_path: str) -> Dict[str, Any]:
        """
        Analyze both files and generate merge rule suggestions.

        Args:
            nsprev_path: Path to NSPREV file
            engnew_path: Path to ENGNEW file

        Returns:
            Dictionary with analysis results and suggestions
        """
        from cvpilot.core.parser import YAMLParser

        parser = YAMLParser()
        nsprev_data = parser.load_yaml_file(nsprev_path)
        engnew_data = parser.load_yaml_file(engnew_path)

        # Detect component type from files
        self._detect_component_type(nsprev_path, engnew_path, nsprev_data, engnew_data)

        # Find all list-type fields in both files
        nsprev_lists = self._find_all_list_fields(nsprev_data)
        engnew_lists = self._find_all_list_fields(engnew_data)

        # Detect conflicts
        self.conflicts = self._detect_conflicts(nsprev_lists, engnew_lists)

        # Generate suggestions
        self.suggestions = self._generate_suggestions(self.conflicts)

        return {
            'component_type': self.detected_component.value,
            'conflicts': self.conflicts,
            'suggestions': self.suggestions,
            'nsprev_lists': nsprev_lists,
            'engnew_lists': engnew_lists,
            'summary': self._generate_summary()
        }

    def _detect_component_type(self, nsprev_path: str, engnew_path: str,
                              nsprev_data: Dict[str, Any], engnew_data: Dict[str, Any]) -> None:
        """
        Detect component type and adjust analysis accordingly.

        Args:
            nsprev_path: Path to NSPREV file
            engnew_path: Path to ENGNEW file
            nsprev_data: NSPREV data
            engnew_data: ENGNEW data
        """
        # Try filename detection first
        nsprev_component = ComponentType.detect_from_filename(Path(nsprev_path).name)
        engnew_component = ComponentType.detect_from_filename(Path(engnew_path).name)

        # If both files suggest the same component, use that
        if nsprev_component != ComponentType.UNKNOWN and nsprev_component == engnew_component:
            self.detected_component = nsprev_component
        # Otherwise, try content detection
        else:
            nsprev_content_component = ComponentType.detect_from_content(nsprev_data)
            engnew_content_component = ComponentType.detect_from_content(engnew_data)

            if nsprev_content_component != ComponentType.UNKNOWN:
                self.detected_component = nsprev_content_component
            elif engnew_content_component != ComponentType.UNKNOWN:
                self.detected_component = engnew_content_component
            elif nsprev_component != ComponentType.UNKNOWN:
                self.detected_component = nsprev_component
            elif engnew_component != ComponentType.UNKNOWN:
                self.detected_component = engnew_component
            else:
                self.detected_component = ComponentType.UNKNOWN

        # Update field names based on detected component
        self.list_field_names = self.COMPONENT_FIELDS.get(
            self.detected_component,
            self.BASE_LIST_FIELD_NAMES
        )
    
    def _find_all_list_fields(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """
        Recursively find all relevant fields (both lists and dicts) in the YAML structure.
        
        Args:
            data: YAML data to analyze
            path: Current path in the structure
            
        Returns:
            Dictionary mapping field paths to their values
        """
        fields = {}
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Check if this dict field is one we care about
                field_name = key.lower()
                if any(list_field in field_name for list_field in self.list_field_names):
                    # This is a target field (like commonlabels dict)
                    fields[current_path] = value
                else:
                    # Recursively search nested dictionaries
                    nested_fields = self._find_all_list_fields(value, current_path)
                    fields.update(nested_fields)
            elif isinstance(value, list):
                # Check if this is a list-type field we care about
                field_name = key.lower()
                if any(list_field in field_name for list_field in self.list_field_names):
                    fields[current_path] = value
            else:
                # Check if this is a dict-type field we care about (like commonlabels)
                field_name = key.lower()
                if any(list_field in field_name for list_field in self.list_field_names):
                    fields[current_path] = value
        
        return fields
    
    def _detect_conflicts(self, nsprev_lists: Dict[str, Any], engnew_lists: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect conflicts between NSPREV and ENGNEW fields.
        
        Args:
            nsprev_lists: Fields from NSPREV
            engnew_lists: Fields from ENGNEW
            
        Returns:
            List of conflict objects
        """
        conflicts = []
        
        # Find fields that exist in both files
        common_paths = set(nsprev_lists.keys()) & set(engnew_lists.keys())
        
        # Also check for field name matches (e.g., commonlabels at different paths)
        nsprev_by_field = {}
        engnew_by_field = {}
        
        for path, value in nsprev_lists.items():
            field_name = path.split('.')[-1]
            if field_name not in nsprev_by_field:
                nsprev_by_field[field_name] = []
            nsprev_by_field[field_name].append((path, value))
        
        for path, value in engnew_lists.items():
            field_name = path.split('.')[-1]
            if field_name not in engnew_by_field:
                engnew_by_field[field_name] = []
            engnew_by_field[field_name].append((path, value))
        
        # Check for field name conflicts (same field name, different paths)
        for field_name in set(nsprev_by_field.keys()) & set(engnew_by_field.keys()):
            for nsprev_path, nsprev_value in nsprev_by_field[field_name]:
                for engnew_path, engnew_value in engnew_by_field[field_name]:
                    # Only compare if they're at the same relative path
                    nsprev_relative = '.'.join(nsprev_path.split('.')[-2:]) if '.' in nsprev_path else nsprev_path
                    engnew_relative = '.'.join(engnew_path.split('.')[-2:]) if '.' in engnew_path else engnew_path
                    
                    if nsprev_relative == engnew_relative:
                        common_paths.add(nsprev_path)
                        # Update engnew_lists to include this path for comparison
                        engnew_lists[nsprev_path] = engnew_value
        
        for path in common_paths:
            nsprev_val = nsprev_lists[path]
            engnew_val = engnew_lists[path]
            
            # Check for structural differences (dict vs list)
            nsprev_is_dict = isinstance(nsprev_val, dict)
            engnew_is_dict = isinstance(engnew_val, dict)
            nsprev_is_list = isinstance(nsprev_val, list)
            engnew_is_list = isinstance(engnew_val, list)
            
            # Detect structural mismatch
            structural_mismatch = (nsprev_is_dict and engnew_is_list) or (nsprev_is_list and engnew_is_dict)
            
            if nsprev_val != engnew_val or structural_mismatch:
                conflict = {
                    'path': path,
                    'field_name': path.split('.')[-1],
                    'nsprev_type': type(nsprev_val).__name__,
                    'engnew_type': type(engnew_val).__name__,
                    'nsprev_count': len(nsprev_val) if isinstance(nsprev_val, (list, dict)) else 1,
                    'engnew_count': len(engnew_val) if isinstance(engnew_val, (list, dict)) else 1,
                    'nsprev_items': nsprev_val,
                    'engnew_items': engnew_val,
                    'structural_mismatch': structural_mismatch,
                    'has_unique_nsprev': self._has_unique_items(nsprev_val, engnew_val),
                    'has_unique_engnew': self._has_unique_items(engnew_val, nsprev_val),
                    'site_specific_score': self._calculate_site_specific_score(nsprev_val),
                    'engnew_specific_score': self._calculate_engnew_specific_score(engnew_val)
                }
                conflicts.append(conflict)
        
        return conflicts
    
    def _has_unique_items(self, list1: List[Any], list2: List[Any]) -> bool:
        """
        Check if list1 has items that don't exist in list2.
        
        Args:
            list1: First list
            list2: Second list
            
        Returns:
            True if list1 has unique items
        """
        if not isinstance(list1, list) or not isinstance(list2, list):
            return list1 != list2
        
        # For list of dicts, compare by key-value pairs
        if list1 and isinstance(list1[0], dict) and list2 and isinstance(list2[0], dict):
            list1_keys = {self._get_dict_key(item) for item in list1 if self._get_dict_key(item)}
            list2_keys = {self._get_dict_key(item) for item in list2 if self._get_dict_key(item)}
            return bool(list1_keys - list2_keys)
        
        # For simple lists, check for items not in list2
        return any(item not in list2 for item in list1)
    
    def _get_dict_key(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Extract the key from a dictionary item (for annotations, labels, etc.).
        
        Args:
            item: Dictionary item
            
        Returns:
            The key name or None if not found
        """
        if isinstance(item, dict) and len(item) == 1:
            return list(item.keys())[0]
        return None
    
    def _calculate_site_specific_score(self, items: List[Any]) -> float:
        """
        Calculate how site-specific the items are based on patterns.
        
        Args:
            items: List of items to analyze
            
        Returns:
            Score from 0.0 to 1.0 (higher = more site-specific)
        """
        if not isinstance(items, list):
            return 0.0
        
        score = 0.0
        total_items = len(items)
        
        if total_items == 0:
            return 0.0
        
        for item in items:
            if isinstance(item, dict):
                for key, value in item.items():
                    # Check for site-specific patterns
                    for pattern in self.SITE_SPECIFIC_PATTERNS:
                        if pattern in key or pattern in str(value):
                            score += 1.0
                            break
            elif isinstance(item, str):
                for pattern in self.SITE_SPECIFIC_PATTERNS:
                    if pattern in item:
                        score += 1.0
                        break
        
        return min(score / total_items, 1.0)
    
    def _calculate_engnew_specific_score(self, items: List[Any]) -> float:
        """
        Calculate how much ENGNEW content is new/template-specific.
        
        Args:
            items: List of items to analyze
            
        Returns:
            Score from 0.0 to 1.0 (higher = more template-specific)
        """
        if not isinstance(items, list):
            return 0.0
        
        # Simple heuristic: more items = more template content
        return min(len(items) / 10.0, 1.0)
    
    def _generate_suggestions(self, conflicts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Generate merge strategy suggestions based on conflict analysis.
        
        Args:
            conflicts: List of detected conflicts
            
        Returns:
            Dictionary of path-specific suggestions
        """
        suggestions = {}
        
        for conflict in conflicts:
            path = conflict['path']
            field_name = conflict['field_name']
            
            # Handle structural mismatches (dict vs list)
            if conflict.get('structural_mismatch', False):
                # For structural mismatches, prefer NSPREV to preserve site-specific structure
                suggested_strategy = 'nsprev'
                reason = f'Structural mismatch: {conflict["nsprev_type"]} vs {conflict["engnew_type"]} - preserving NSPREV structure'
            elif conflict['site_specific_score'] > 0.7:
                # High site-specific content - preserve NSPREV
                suggested_strategy = 'nsprev'
                reason = 'High site-specific content detected'
            elif conflict['has_unique_nsprev'] and conflict['has_unique_engnew']:
                # Both have unique items - merge
                suggested_strategy = 'merge'
                reason = 'Both files have unique items'
            elif conflict['engnew_count'] > conflict['nsprev_count'] * 1.5:
                # ENGNEW has significantly more items
                suggested_strategy = 'engnew'
                reason = 'ENGNEW has significant additions'
            elif conflict['nsprev_count'] > conflict['engnew_count']:
                # NSPREV has more items
                suggested_strategy = 'nsprev'
                reason = 'NSPREV has more items (likely site-specific)'
            else:
                # Default to merge for safety
                suggested_strategy = 'merge'
                reason = 'Safe default: merge both'
            
            suggestions[path] = {
                'suggested_strategy': suggested_strategy,
                'reason': reason,
                'details': conflict,
                'confidence': self._calculate_confidence(conflict, suggested_strategy)
            }
        
        return suggestions
    
    def _calculate_confidence(self, conflict: Dict[str, Any], strategy: str) -> float:
        """
        Calculate confidence level for the suggested strategy.
        
        Args:
            conflict: Conflict details
            strategy: Suggested strategy
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.5  # Base confidence
        
        if strategy == 'nsprev' and conflict['site_specific_score'] > 0.7:
            confidence = 0.9
        elif strategy == 'merge' and conflict['has_unique_nsprev'] and conflict['has_unique_engnew']:
            confidence = 0.8
        elif strategy == 'engnew' and conflict['engnew_count'] > conflict['nsprev_count'] * 2:
            confidence = 0.8
        elif strategy == 'nsprev' and conflict['nsprev_count'] > conflict['engnew_count'] * 2:
            confidence = 0.8
        
        return min(confidence, 1.0)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate analysis summary.
        
        Returns:
            Summary statistics
        """
        if not self.conflicts:
            return {
                'total_conflicts': 0,
                'suggested_merges': 0,
                'suggested_nsprev': 0,
                'suggested_engnew': 0
            }
        
        suggested_merges = sum(1 for s in self.suggestions.values() if s['suggested_strategy'] == 'merge')
        suggested_nsprev = sum(1 for s in self.suggestions.values() if s['suggested_strategy'] == 'nsprev')
        suggested_engnew = sum(1 for s in self.suggestions.values() if s['suggested_strategy'] == 'engnew')
        
        return {
            'total_conflicts': len(self.conflicts),
            'suggested_merges': suggested_merges,
            'suggested_nsprev': suggested_nsprev,
            'suggested_engnew': suggested_engnew,
            'high_confidence': sum(1 for s in self.suggestions.values() if s['confidence'] > 0.8)
        }


def generate_rulebook_from_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate merge_rules.yaml content from analysis results.

    Args:
        analysis: Analysis results from ConflictAnalyzer

    Returns:
        Dictionary representing the rulebook YAML structure
    """
    component_type = analysis.get('component_type', 'unknown')

    # Base rulebook structure
    rulebook = {
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

    # Add component-specific rules
    if component_type == 'ocnrf':
        # NRF-specific merge rules
        nrf_rules = {
            'nrfTag': {
                'strategy': 'engnew',
                'scope': 'global'
            },
            'gwTag': {
                'strategy': 'engnew',
                'scope': 'global'
            },
            'deprecatedList': {
                'strategy': 'nsprev',
                'scope': 'global'
            },
            'relaxValidations': {
                'strategy': 'nsprev',
                'scope': 'global'
            },
            'mysql': {
                'strategy': 'nsprev',
                'scope': 'global'
            },
            'errorResponseDueToEgwOverload': {
                'strategy': 'merge',
                'scope': 'global'
            },
            'edgeDeploymentMode': {
                'strategy': 'engnew',
                'scope': 'global'
            },
            'backEndDeploymentMode': {
                'strategy': 'engnew',
                'scope': 'global'
            }
        }
        rulebook['merge_rules'].update(nrf_rules)

        # NRF-specific path overrides
        nrf_path_overrides = {
            'global.nrfTag': {'strategy': 'engnew'},
            'global.gwTag': {'strategy': 'engnew'},
            'global.deprecatedList': {'strategy': 'nsprev'},
            'global.mysql.primary': {'strategy': 'nsprev'},
            'global.mysql.secondary': {'strategy': 'nsprev'}
        }
        rulebook['path_overrides'].update(nrf_path_overrides)

    elif component_type == 'occndbtier':
        # CNDBTIER-specific rules
        cndbtier_rules = {
            'mysql': {
                'strategy': 'nsprev',
                'scope': 'global'
            },
            'database': {
                'strategy': 'nsprev',
                'scope': 'global'
            }
        }
        rulebook['merge_rules'].update(cndbtier_rules)
    
    # Add path-specific overrides based on suggestions
    suggestions = analysis.get('suggestions', {})
    for path, suggestion in suggestions.items():
        # Include structural mismatches and high-confidence suggestions
        if (suggestion['confidence'] > 0.7 or 
            'structural mismatch' in suggestion['reason'].lower() or
            suggestion['suggested_strategy'] == 'nsprev'):
            rulebook['path_overrides'][path] = {
                'strategy': suggestion['suggested_strategy']
            }
    
    return rulebook
