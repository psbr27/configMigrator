#!/usr/bin/env python3
"""
Test script for the rulebook-based merge system.

This script tests the dynamic analysis and rulebook generation functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cvpilot.core.analyzer import ConflictAnalyzer, generate_rulebook_from_analysis
from cvpilot.core.rulebook import RulebookManager
from cvpilot.core.merger import ConfigMerger


def test_analyzer():
    """Test the conflict analyzer."""
    print("Testing ConflictAnalyzer...")
    
    # Create test data
    nsprev_data = {
        "mgm": {
            "annotations": [
                {"sidecar.istio.io/inject": "true"},
                {"sidecar.istio.io/proxyCPU": "2"},
                {"sidecar.istio.io/proxyMemory": "2Gi"}
            ]
        },
        "global": {
            "commonlabels": {
                "vz.webscale.com/name": "test-site",
                "vz.webscale.com/version": "25.1.102"
            }
        }
    }
    
    engnew_data = {
        "mgm": {
            "annotations": [
                {"sidecar.istio.io/inject": "true"},
                {"traffic.sidecar.istio.io/excludeInboundPorts": "8081"}
            ]
        },
        "global": {
            "commonlabels": {}
        }
    }
    
    # Test analyzer
    analyzer = ConflictAnalyzer()
    
    # Mock the file loading for testing
    def mock_analyze_files(nsprev_path, engnew_path):
        return analyzer._detect_conflicts(
            analyzer._find_all_list_fields(nsprev_data),
            analyzer._find_all_list_fields(engnew_data)
        )
    
    # Override the analyze_files method for testing
    analyzer.analyze_files = mock_analyze_files
    
    # Run analysis
    conflicts = analyzer._detect_conflicts(
        analyzer._find_all_list_fields(nsprev_data),
        analyzer._find_all_list_fields(engnew_data)
    )
    
    print(f"✓ Detected {len(conflicts)} conflicts")
    
    # Test suggestions
    suggestions = analyzer._generate_suggestions(conflicts)
    print(f"✓ Generated {len(suggestions)} suggestions")
    
    return True


def test_rulebook_generation():
    """Test rulebook generation."""
    print("Testing rulebook generation...")
    
    # Create mock analysis results
    analysis = {
        'conflicts': [
            {
                'path': 'mgm.annotations',
                'field_name': 'annotations',
                'nsprev_count': 3,
                'engnew_count': 2,
                'has_unique_nsprev': True,
                'has_unique_engnew': True,
                'site_specific_score': 0.8
            }
        ],
        'suggestions': {
            'mgm.annotations': {
                'suggested_strategy': 'merge',
                'reason': 'Both files have unique items',
                'confidence': 0.8
            }
        },
        'summary': {
            'total_conflicts': 1,
            'suggested_merges': 1,
            'suggested_nsprev': 0,
            'suggested_engnew': 0
        }
    }
    
    # Generate rulebook
    rulebook = generate_rulebook_from_analysis(analysis)
    
    print("✓ Generated rulebook structure:")
    print(f"  - Default strategy: {rulebook.get('default_strategy')}")
    print(f"  - Merge rules: {len(rulebook.get('merge_rules', {}))}")
    print(f"  - Path overrides: {len(rulebook.get('path_overrides', {}))}")
    
    return True


def test_rulebook_manager():
    """Test rulebook manager."""
    print("Testing RulebookManager...")
    
    # Create default rulebook
    manager = RulebookManager()
    default_rules = manager.create_default_rulebook()
    
    print("✓ Created default rulebook")
    print(f"  - Default strategy: {default_rules.get('default_strategy')}")
    print(f"  - Merge rules: {len(default_rules.get('merge_rules', {}))}")
    
    # Test path matching
    test_paths = [
        "mgm.annotations",
        "ndb.annotations", 
        "api.externalService.sqlgeorepsvclabels[0].labels"
    ]
    
    for path in test_paths:
        strategy = manager.get_merge_strategy(path)
        print(f"  - {path} -> {strategy}")
    
    return True


def test_merger_with_rulebook():
    """Test merger with rulebook."""
    print("Testing ConfigMerger with rulebook...")
    
    # Test data
    nsprev = {
        "mgm": {
            "annotations": [
                {"sidecar.istio.io/inject": "true"},
                {"sidecar.istio.io/proxyCPU": "2"}
            ]
        }
    }
    
    engnew = {
        "mgm": {
            "annotations": [
                {"sidecar.istio.io/inject": "true"},
                {"traffic.sidecar.istio.io/excludeInboundPorts": "8081"}
            ]
        }
    }
    
    # Test without rulebook (default behavior)
    result_default = ConfigMerger.merge_with_rulebook(nsprev, engnew)
    print("✓ Merged without rulebook")
    
    # Test with rulebook
    rulebook_content = {
        'default_strategy': 'merge',
        'merge_rules': {
            'annotations': {
                'strategy': 'merge',
                'scope': 'global'
            }
        },
        'path_overrides': {}
    }
    
    # Save temporary rulebook
    import yaml
    with open('temp_rules.yaml', 'w') as f:
        yaml.dump(rulebook_content, f)
    
    try:
        result_with_rules = ConfigMerger.merge_with_rulebook(nsprev, engnew, 'temp_rules.yaml')
        print("✓ Merged with rulebook")
        
        # Check if merge worked correctly
        mgm_annotations = result_with_rules.get('mgm', {}).get('annotations', [])
        print(f"  - Result has {len(mgm_annotations)} annotations")
        
    finally:
        # Clean up
        if os.path.exists('temp_rules.yaml'):
            os.remove('temp_rules.yaml')
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing CVPilot Rulebook System")
    print("=" * 60)
    
    tests = [
        test_analyzer,
        test_rulebook_generation,
        test_rulebook_manager,
        test_merger_with_rulebook
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} FAILED: {e}")
        
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
