#!/usr/bin/env python3
"""Test script to run the enhanced migration."""

import sys
import os
import json
sys.path.insert(0, 'src')

from conflict_logger import ConflictLogger
from merge_engine import MergeEngine
from validators import ConfigValidator
from yaml_processor import YAMLProcessor

class ConfigMigrator:
    """Main configuration migration tool."""

    def __init__(self) -> None:
        """Initialize the configuration migrator."""
        self.yaml_processor = YAMLProcessor()
        self.validator = ConfigValidator()
        self.merge_engine = MergeEngine()
        self.conflict_logger = ConflictLogger()

    def migrate(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str,
        output_config_path: str,
        output_log_path: str,
        migration_map_path = None,
        output_format: str = "json",
        dry_run: bool = False,
        verbose: bool = False
    ) -> bool:
        """Perform configuration migration."""
        try:
            if verbose:
                print(f"Loading configurations...")

            # Load configurations
            golden_config = self.yaml_processor.load_yaml(golden_old_path)
            template_old = self.yaml_processor.load_yaml(template_old_path)
            template_new = self.yaml_processor.load_yaml(template_new_path)

            if verbose:
                print(f"Performing migration...")

            # Load migration map if provided
            migration_map = None
            if migration_map_path:
                with open(migration_map_path, 'r') as f:
                    migration_map = json.load(f)

            # Perform merge
            final_config, conflict_log = self.merge_engine.merge_configurations(
                golden_config, template_old, template_new, migration_map
            )

            if verbose:
                print(f"Migration completed. Writing output...")

            # Write output configuration
            if not dry_run:
                self.yaml_processor.save_yaml(final_config, output_config_path)

            # Write conflict log
            self.conflict_logger.save_log(conflict_log, output_log_path, output_format)

            return True

        except Exception as e:
            print(f"Migration failed: {e}")
            return False

def main():
    migrator = ConfigMigrator()

    success = migrator.migrate(
        golden_old_path="rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml",
        template_old_path="occndbtier_custom_values_25.1.102.yaml",
        template_new_path="occndbtier_custom_values_25.1.200.yaml",
        output_config_path="network_safe_occndbtier_25.1.200_v2.yaml",
        output_log_path="network_safe_migration_log_v2.json",
        verbose=True
    )

    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()