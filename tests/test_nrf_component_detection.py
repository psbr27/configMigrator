#!/usr/bin/env python3
"""
Test script to validate enhanced component detection and analysis with real NRF files.
"""

import sys
sys.path.insert(0, 'src')

from cvpilot.core.analyzer import ConflictAnalyzer, ComponentType, generate_rulebook_from_analysis
from cvpilot.core.parser import YAMLParser
from cvpilot.core.transformer import PathTransformationDetector
from cvpilot.core.merger import ConfigMerger
import traceback
from pathlib import Path


def test_component_detection():
    """Test component detection with real NRF files."""
    print("🔍 Testing Component Detection with Real NRF Files")
    print("=" * 60)

    # Test files
    nrf_files = [
        "nrf_yaml_files/ocnrf_custom_values_24.2.4.yaml",
        "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml",
        "nrf_yaml_files/rcnltxekvzwcnrf-y-or-x-102-ocnrf_24.2.4.yaml"
    ]

    parser = YAMLParser()

    for file_path in nrf_files:
        if Path(file_path).exists():
            print(f"\n📁 Analyzing: {file_path}")

            # Test filename detection
            filename_component = ComponentType.detect_from_filename(file_path)
            print(f"   Filename detection: {filename_component.value}")

            # Test content detection
            try:
                data = parser.load_yaml_file(file_path)
                content_component = ComponentType.detect_from_content(data)
                print(f"   Content detection:  {content_component.value}")

                # Show key indicators found
                global_section = data.get('global', {})
                indicators = []
                if 'nrfTag' in global_section:
                    indicators.append(f"nrfTag: {global_section['nrfTag']}")
                if 'gwTag' in global_section:
                    indicators.append(f"gwTag: {global_section['gwTag']}")
                if 'mysql' in global_section:
                    indicators.append("mysql config found")

                print(f"   Key indicators:     {', '.join(indicators) if indicators else 'none'}")

            except Exception as e:
                print(f"   ❌ Error loading file: {e}")
        else:
            print(f"\n❌ File not found: {file_path}")


def test_nrf_conflict_analysis():
    """Test conflict analysis between NRF versions."""
    print("\n\n🔬 Testing NRF Conflict Analysis")
    print("=" * 60)

    nsprev_path = "nrf_yaml_files/ocnrf_custom_values_24.2.4.yaml"
    engnew_path = "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml"

    if not (Path(nsprev_path).exists() and Path(engnew_path).exists()):
        print(f"❌ Required files not found:")
        print(f"   NSPREV: {nsprev_path}")
        print(f"   ENGNEW: {engnew_path}")
        return

    try:
        analyzer = ConflictAnalyzer()
        analysis = analyzer.analyze_files(nsprev_path, engnew_path)

        print(f"Component Type: {analysis['component_type']}")
        print(f"Total Conflicts: {analysis['summary']['total_conflicts']}")
        print(f"Suggested Merges: {analysis['summary']['suggested_merges']}")
        print(f"Suggested NSPREV: {analysis['summary']['suggested_nsprev']}")
        print(f"Suggested ENGNEW: {analysis['summary']['suggested_engnew']}")
        print(f"High Confidence: {analysis['summary']['high_confidence']}")

        # Show a few example conflicts
        print("\n📋 Example Conflicts Found:")
        for i, conflict in enumerate(analysis['conflicts'][:3]):
            path = conflict['path']
            suggestion = analysis['suggestions'].get(path, {})
            print(f"   {i+1}. {path}")
            print(f"      Type: {conflict['nsprev_type']} vs {conflict['engnew_type']}")
            print(f"      Strategy: {suggestion.get('suggested_strategy', 'unknown')}")
            print(f"      Confidence: {suggestion.get('confidence', 0.0):.2f}")
            print(f"      Reason: {suggestion.get('reason', 'no reason')}")

        # Generate NRF-specific rulebook
        print("\n📜 Generating NRF-specific Rulebook...")
        rulebook = generate_rulebook_from_analysis(analysis)

        # Show key rulebook sections
        print("   Component-specific rules:")
        for field, config in list(rulebook['merge_rules'].items())[:5]:
            print(f"     {field}: {config['strategy']} ({config.get('scope', 'global')})")

        print(f"   Path overrides: {len(rulebook['path_overrides'])} rules")

    except Exception as e:
        print(f"❌ Error in conflict analysis: {e}")
        traceback.print_exc()


def test_path_transformation_detection():
    """Test path transformation detection with NRF files."""
    print("\n\n🔄 Testing Path Transformation Detection")
    print("=" * 60)

    # This would normally be the output from Stage 2 merge
    # For testing, we'll simulate by doing a basic merge
    nsprev_path = "nrf_yaml_files/ocnrf_custom_values_24.2.4.yaml"
    engnew_path = "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml"

    if not (Path(nsprev_path).exists() and Path(engnew_path).exists()):
        print(f"❌ Required files not found")
        return

    try:
        parser = YAMLParser()
        nsprev_data = parser.load_yaml_file(nsprev_path)
        engnew_data = parser.load_yaml_file(engnew_path)

        # Create a simple merged config for testing
        # This simulates the output from Stage 2
        merged_config = ConfigMerger.deep_merge(engnew_data, nsprev_data)

        # Test path transformation detection
        detector = PathTransformationDetector()
        transformations = detector.detect_duplicate_values(merged_config, engnew_data)

        print(f"Detected Transformations: {len(transformations)}")

        if transformations:
            print("\n📋 Example Transformations:")
            for i, trans in enumerate(transformations[:5]):
                print(f"   {i+1}. {trans.old_path} → {trans.new_path}")
                print(f"      Value: {str(trans.value)[:50]}{'...' if len(str(trans.value)) > 50 else ''}")
                print(f"      Recommendation: {trans.recommendation}")
                print(f"      Confidence: {trans.confidence}")
                print(f"      Reason: {trans.reason}")
                print()

            # Generate transformation report
            report = detector.generate_transformation_report(transformations)
            print("📊 Transformation Report Summary:")
            lines = report.split('\n')[:10]  # First 10 lines
            for line in lines:
                if line.strip():
                    print(f"   {line}")
        else:
            print("   ✅ No path transformations detected")

    except Exception as e:
        print(f"❌ Error in path transformation detection: {e}")
        traceback.print_exc()


def test_performance_with_large_files():
    """Test performance with large NRF files."""
    print("\n\n⚡ Testing Performance with Large NRF Files")
    print("=" * 60)

    import time

    large_file = "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml"

    if not Path(large_file).exists():
        print(f"❌ Large file not found: {large_file}")
        return

    try:
        parser = YAMLParser()

        # Test file loading performance
        start_time = time.time()
        data = parser.load_yaml_file(large_file)
        load_time = time.time() - start_time

        # Count structure complexity
        def count_keys(obj, level=0):
            if level > 10:  # Prevent infinite recursion
                return 0
            count = 0
            if isinstance(obj, dict):
                count = len(obj)
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        count += count_keys(value, level + 1)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        count += count_keys(item, level + 1)
            return count

        total_keys = count_keys(data)
        file_size = Path(large_file).stat().st_size / 1024  # KB

        print(f"File Size: {file_size:.1f} KB")
        print(f"Total Keys/Items: {total_keys:,}")
        print(f"Load Time: {load_time:.3f} seconds")
        print(f"Processing Rate: {total_keys/load_time:.0f} keys/second")

        # Test component detection performance
        start_time = time.time()
        component = ComponentType.detect_from_content(data)
        detection_time = time.time() - start_time

        print(f"Component Detection: {component.value} ({detection_time:.3f}s)")

        # Test path building performance (simplified)
        start_time = time.time()
        detector = PathTransformationDetector()
        detector._build_path_value_map(data, "")
        path_build_time = time.time() - start_time

        print(f"Path Mapping: {len(detector.path_value_map):,} paths ({path_build_time:.3f}s)")

    except Exception as e:
        print(f"❌ Error in performance testing: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 CVPilot Enhanced NRF Testing Suite")
    print("=" * 80)

    # Run all tests
    test_component_detection()
    test_nrf_conflict_analysis()
    test_path_transformation_detection()
    test_performance_with_large_files()

    print("\n" + "=" * 80)
    print("✅ Testing Complete!")