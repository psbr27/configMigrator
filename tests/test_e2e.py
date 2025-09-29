#!/usr/bin/env python3
"""End-to-end test of the complete migration workflow."""

import sys
import os
import yaml
import json
sys.path.insert(0, 'src')

from config_migrator import ConfigMigrator

def main():
    print("🚀 Starting End-to-End Migration Test")
    print("=" * 50)

    # Initialize migrator
    migrator = ConfigMigrator()

    # Test 1: Complete migration workflow
    print("📋 Test 1: Complete Migration Workflow")
    success = migrator.migrate(
        golden_old_path="rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml",
        template_old_path="occndbtier_custom_values_25.1.102.yaml",
        template_new_path="occndbtier_custom_values_25.1.200.yaml",
        output_config_path="e2e_test_output.yaml",
        output_log_path="e2e_test_log.json",
        verbose=True
    )

    if not success:
        print("❌ Migration failed!")
        return False

    print("✅ Migration completed successfully!")

    # Test 2: Verify conflict log structure
    print(f"\n📋 Test 2: Verify Conflict Log")
    with open('e2e_test_log.json', 'r') as f:
        log_data = json.load(f)

    if 'migration_summary' in log_data:
        summary = log_data['migration_summary']
        print(f"  ✅ Total entries: {summary['total_entries']}")
        print(f"  ✅ Manual review required: {summary['manual_review_required']}")
        print(f"  ✅ Statistics: {summary['statistics']}")
    else:
        print("  ❌ Missing migration summary in log")
        return False

    if 'conflicts' in log_data:
        conflicts = log_data['conflicts']
        print(f"  ✅ Conflicts logged: {len(conflicts)}")

        # Check for network preservation log entry
        network_entry_found = False
        for conflict in conflicts:
            if conflict['path'] == '__NETWORK_PRESERVATION_SUMMARY__':
                network_entry_found = True
                print(f"  ✅ Network preservation summary: {conflict['source_value']}")
                break

        if not network_entry_found:
            print("  ⚠️  Network preservation summary not found")
    else:
        print("  ❌ Missing conflicts array in log")
        return False

    # Test 3: Verify file integrity
    print(f"\n📋 Test 3: Verify Output File Integrity")

    # Check output file exists and is valid YAML
    if not os.path.exists('e2e_test_output.yaml'):
        print("  ❌ Output configuration file not created")
        return False

    try:
        with open('e2e_test_output.yaml', 'r') as f:
            yaml.safe_load(f)
        print("  ✅ Output configuration is valid YAML")
    except yaml.YAMLError as e:
        print(f"  ❌ Output configuration is invalid YAML: {e}")
        return False

    # Check log file exists and is valid JSON
    if not os.path.exists('e2e_test_log.json'):
        print("  ❌ Output log file not created")
        return False

    try:
        with open('e2e_test_log.json', 'r') as f:
            json.load(f)
        print("  ✅ Output log is valid JSON")
    except json.JSONDecodeError as e:
        print(f"  ❌ Output log is invalid JSON: {e}")
        return False

    # Final summary
    print("\n" + "=" * 50)
    print("🎉 END-TO-END TEST RESULTS")
    print("=" * 50)
    print(f"✅ Migration workflow: SUCCESS")
    print(f"✅ Conflict logging: SUCCESS")
    print(f"✅ File integrity: SUCCESS")
    print("\n🏆 Basic workflow tests passed! Run 'pytest tests/test_network_preservation.py' for detailed network tests.")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)