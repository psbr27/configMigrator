#!/usr/bin/env python3
"""Test script for dynamic discovery system."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "dynamic_discovery"))

from dynamic_discovery import DynamicStructuralDetector, MigrationSuggester
from yaml_processor import YAMLProcessor


def test_dynamic_discovery():
    """Test dynamic discovery on the actual serviceAccount case."""

    # Load the actual files
    yaml_processor = YAMLProcessor()

    try:
        golden_config = yaml_processor.load_yaml_file(
            "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml"
        )
        template_old = yaml_processor.load_yaml_file(
            "occndbtier_custom_values_25.1.102.yaml"
        )
        template_new = yaml_processor.load_yaml_file(
            "occndbtier_custom_values_25.1.200.yaml"
        )

        print("✅ Successfully loaded configuration files")

    except Exception as e:
        print(f"❌ Failed to load files: {e}")
        return False

    # Initialize dynamic discovery
    try:
        detector = DynamicStructuralDetector(enable_verbose_logging=True)
        suggester = MigrationSuggester(enable_verbose_logging=True)

        print("✅ Successfully initialized dynamic discovery components")

    except Exception as e:
        print(f"❌ Failed to initialize dynamic discovery: {e}")
        return False

    # Run discovery
    try:
        print("\\n🔍 Running dynamic structural migration discovery...")
        discoveries = detector.discover_structural_migrations(
            golden_config, template_old, template_new
        )

        print("\\n📊 Discovery Results:")
        print(f"   Found {len(discoveries)} potential migrations")

        for i, discovery in enumerate(discoveries[:5]):  # Show first 5
            print(f"\\n   Migration {i+1}:")
            print(f"     Old Path: {discovery.old_path}")
            print(f"     Custom Value: {discovery.custom_value}")
            print(f"     Confidence: {discovery.confidence:.2f}")
            print(f"     Migration Type: {discovery.migration_type}")

            if discovery.best_candidate:
                print(f"     Suggested Path: {discovery.best_candidate.new_path}")
                print(f"     Evidence: {discovery.best_candidate.evidence}")

        if len(discoveries) > 5:
            print(f"\\n   ... and {len(discoveries) - 5} more migrations")

    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Generate report
    try:
        print("\\n📝 Generating migration report...")
        report = suggester.generate_migration_report(discoveries)

        print("\\n📈 Report Summary:")
        print(f"   Total migrations: {report['summary']['total_migrations']}")
        print(f"   Auto-apply ready: {report['summary']['auto_apply_count']}")
        print(f"   Review required: {report['summary']['review_required_count']}")
        print(f"   Low confidence: {report['summary']['low_confidence_count']}")

        # Export report
        suggester.export_migration_report(
            report, "dynamic_discovery_test_report.json", "json"
        )
        print("\\n💾 Report exported to: dynamic_discovery_test_report.json")

    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test specific serviceAccount case
    try:
        print("\\n🎯 Looking for serviceAccount migrations...")
        sa_migrations = [
            d
            for d in discoveries
            if "serviceaccount" in d.old_path.lower()
            or "serviceaccount" in str(d.custom_value).lower()
        ]

        print(f"   Found {len(sa_migrations)} serviceAccount-related migrations:")
        for migration in sa_migrations:
            print(
                f"     • {migration.old_path} → {migration.best_candidate.new_path if migration.best_candidate else 'No candidate'}"
            )
            print(f"       Confidence: {migration.confidence:.2f}")

    except Exception as e:
        print(f"❌ ServiceAccount analysis failed: {e}")
        return False

    print("\\n🎉 Dynamic discovery test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_dynamic_discovery()
    sys.exit(0 if success else 1)
