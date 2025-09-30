"""Main CLI entry point for ConfigMigrator tool."""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

try:
    from .conflict_logger import ConflictLogger
    from .dynamic_discovery import DynamicStructuralDetector, MigrationSuggester
    from .merge_engine import MergeEngine
    from .validators import ConfigValidator
    from .yaml_processor import YAMLProcessor
except ImportError:
    from conflict_logger import ConflictLogger
    from merge_engine import MergeEngine
    from validators import ConfigValidator
    from yaml_processor import YAMLProcessor

    try:
        from .dynamic_discovery import DynamicStructuralDetector, MigrationSuggester
    except ImportError:
        try:
            from dynamic_discovery import DynamicStructuralDetector, MigrationSuggester
        except ImportError:
            DynamicStructuralDetector = None
            MigrationSuggester = None


class ConfigMigrator:
    """Main configuration migration tool."""

    def __init__(self, rules_file_path: Optional[str] = None) -> None:
        """Initialize the configuration migrator.

        Args:
            rules_file_path: Optional path to network migration rules JSON file.
        """
        self.yaml_processor = YAMLProcessor()
        self.validator = ConfigValidator()
        self.merge_engine = MergeEngine(rules_file_path)
        self.conflict_logger = ConflictLogger()

    def migrate(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str,
        output_config_path: str,
        output_log_path: str,
        migration_map_path: Optional[str] = None,
        output_format: str = "json",
        dry_run: bool = False,
        verbose: bool = False,
        enable_dynamic_discovery: bool = False,
        dynamic_discovery_report_path: Optional[str] = None,
    ) -> bool:
        """Perform configuration migration.

        Args:
            golden_old_path: Path to V_OLD golden configuration.
            template_old_path: Path to V_OLD template.
            template_new_path: Path to V_NEW template.
            output_config_path: Path for output configuration.
            output_log_path: Path for output log.
            migration_map_path: Optional path to migration mapping.
            output_format: Output format for log (json or csv).
            dry_run: If True, generate log without writing output config.
            verbose: Enable verbose output.
            enable_dynamic_discovery: Enable intelligent structural migration discovery.
            dynamic_discovery_report_path: Path to export dynamic discovery report.

        Returns:
            True if migration successful, False otherwise.
        """
        try:
            # Step 1: Validate inputs
            if verbose:
                print("Validating input files...")

            validation_errors = self._validate_inputs(
                golden_old_path,
                template_old_path,
                template_new_path,
                output_config_path,
                output_log_path,
                migration_map_path,
            )

            if validation_errors:
                print("Validation errors found:", file=sys.stderr)
                for error in validation_errors:
                    print(f"  - {error}", file=sys.stderr)
                return False

            # Step 2: Load files
            if verbose:
                print("Loading configuration files...")

            golden_config, template_old, template_new, migration_map = self._load_files(
                golden_old_path,
                template_old_path,
                template_new_path,
                migration_map_path,
                verbose,
            )

            # Step 3: Dynamic Discovery (if enabled)
            dynamic_migration_map = {}
            if enable_dynamic_discovery:
                if DynamicStructuralDetector is None:
                    print(
                        "Warning: Dynamic discovery requested but not available. Skipping...",
                        file=sys.stderr,
                    )
                else:
                    if verbose:
                        print("Running dynamic structural migration discovery...")

                    dynamic_migration_map = self._run_dynamic_discovery(
                        golden_config,
                        template_old,
                        template_new,
                        verbose,
                        dynamic_discovery_report_path,
                    )

            # Step 4: Perform migration
            if verbose:
                print("Performing configuration migration...")

            # Merge any discovered migrations with existing migration map
            combined_migration_map = {**(migration_map or {}), **dynamic_migration_map}

            final_config, conflict_log = self.merge_engine.merge_configurations(
                golden_config,
                template_old,
                template_new,
                combined_migration_map if combined_migration_map else migration_map,
            )

            # Step 5: Validate output
            if verbose:
                print("Validating merged configuration...")

            output_validation_errors = self.validator.validate_output_config(
                final_config
            )
            if output_validation_errors:
                print("Output validation warnings:", file=sys.stderr)
                for error in output_validation_errors:
                    print(f"  - {error}", file=sys.stderr)

            # Step 6: Generate reports
            if verbose:
                print("Generating migration reports...")

            self._print_migration_summary(conflict_log, verbose)

            # Step 7: Write outputs
            if not dry_run:
                if verbose:
                    print(f"Writing output configuration to: {output_config_path}")
                self.yaml_processor.save_yaml_file(final_config, output_config_path)

            if verbose:
                print(f"Writing migration log to: {output_log_path}")

            if output_format.lower() == "csv":
                self.conflict_logger.export_to_csv(output_log_path, conflict_log)
            else:
                self.conflict_logger.export_to_json(output_log_path, conflict_log)

            print("Migration completed successfully!")
            if dry_run:
                print("(Dry run mode - output configuration not written)")

            return True

        except Exception as e:
            print(f"Migration failed: {e}", file=sys.stderr)
            if verbose:
                import traceback

                traceback.print_exc()
            return False

    def _validate_inputs(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str,
        output_config_path: str,
        output_log_path: str,
        migration_map_path: Optional[str],
    ) -> List[str]:
        """Validate all input parameters.

        Args:
            golden_old_path: Path to golden config.
            template_old_path: Path to old template.
            template_new_path: Path to new template.
            output_config_path: Output config path.
            output_log_path: Output log path.
            migration_map_path: Optional migration map path.

        Returns:
            List of validation error messages.
        """
        errors: List[str] = []

        # Validate input files
        input_errors = self.validator.validate_input_files(
            golden_old_path, template_old_path, template_new_path, migration_map_path
        )
        errors.extend(input_errors)

        # Validate output paths
        output_errors = self.validator.validate_output_paths(
            output_config_path, output_log_path
        )
        errors.extend(output_errors)

        return errors

    def _load_files(
        self,
        golden_old_path: str,
        template_old_path: str,
        template_new_path: str,
        migration_map_path: Optional[str],
        verbose: bool,
    ) -> tuple:
        """Load all required files.

        Args:
            golden_old_path: Path to golden config.
            template_old_path: Path to old template.
            template_new_path: Path to new template.
            migration_map_path: Optional migration map path.
            verbose: Enable verbose output.

        Returns:
            Tuple of (golden_config, template_old, template_new, migration_map).
        """
        # Load YAML files
        golden_config = self.yaml_processor.load_yaml_file(golden_old_path)
        template_old = self.yaml_processor.load_yaml_file(template_old_path)
        template_new = self.yaml_processor.load_yaml_file(template_new_path)

        if verbose:
            print(f"  Golden config: {len(golden_config)} top-level keys")
            print(f"  Template old: {len(template_old)} top-level keys")
            print(f"  Template new: {len(template_new)} top-level keys")

        # Load optional migration map
        migration_map: Optional[Dict[str, str]] = None
        if migration_map_path:
            with open(migration_map_path, encoding="utf-8") as file:
                migration_data = json.load(file)

            # Support both simple and complex migration map formats
            if "migrations" in migration_data:
                migration_map = migration_data["migrations"]
            else:
                migration_map = migration_data

            if verbose:
                print(f"  Migration map: {len(migration_map)} mappings loaded")

        return golden_config, template_old, template_new, migration_map

    def _run_dynamic_discovery(
        self,
        golden_config: Dict[str, Any],
        template_old: Dict[str, Any],
        template_new: Dict[str, Any],
        verbose: bool,
        report_path: Optional[str],
    ) -> Dict[str, str]:
        """Run dynamic structural migration discovery.

        Args:
            golden_config: Golden configuration with custom values.
            template_old: Old template configuration.
            template_new: New template configuration.
            verbose: Enable verbose output.
            report_path: Optional path to export discovery report.

        Returns:
            Dictionary mapping old paths to new paths for discovered migrations.
        """
        if DynamicStructuralDetector is None or MigrationSuggester is None:
            return {}

        try:
            # Initialize dynamic discovery components
            detector = DynamicStructuralDetector(enable_verbose_logging=verbose)
            suggester = MigrationSuggester(enable_verbose_logging=verbose)

            # Discover structural migrations
            discoveries = detector.discover_structural_migrations(
                golden_config, template_old, template_new
            )

            if verbose:
                print(
                    f"🔍 Dynamic discovery found {len(discoveries)} potential migrations"
                )

            # Generate migration report
            report = suggester.generate_migration_report(discoveries)

            # Export report if path provided
            if report_path:
                suggester.export_migration_report(report, report_path, "json")
                if verbose:
                    print(f"📝 Dynamic discovery report exported to: {report_path}")

            # Apply automatic migrations to get high-confidence migration map
            auto_migrations = detector.get_auto_apply_migrations(discoveries)
            migration_map = suggester.create_migration_map(auto_migrations)

            # Print summary
            if verbose and discoveries:
                print(
                    f"🤖 Auto-applying {len(auto_migrations)} high-confidence migrations"
                )
                if len(auto_migrations) < len(discoveries):
                    manual_count = len(discoveries) - len(auto_migrations)
                    print(f"👀 {manual_count} migrations require manual review")

            return migration_map

        except Exception as e:
            print(f"Warning: Dynamic discovery failed: {e}", file=sys.stderr)
            if verbose:
                import traceback

                traceback.print_exc()
            return {}

    def _print_migration_summary(
        self, conflict_log: List[Dict[str, Any]], verbose: bool
    ) -> None:
        """Print migration summary to console.

        Args:
            conflict_log: List of conflict log entries.
            verbose: Enable verbose output.
        """
        summary = self.conflict_logger.get_summary_report(conflict_log)

        print("\nMigration Summary:")
        print(f"  Total conflicts processed: {summary['total_conflicts']}")
        print(f"  Manual review required: {summary['manual_review_required']}")
        print(f"  Success rate: {summary['success_rate']:.1f}%")

        if verbose and summary["statistics"]["by_action_type"]:
            print("\nActions taken:")
            for action_type, count in summary["statistics"]["by_action_type"].items():
                print(f"  {action_type}: {count}")

        if summary["critical_paths"]:
            print("\nPaths requiring manual review:")
            for path in summary["critical_paths"][:5]:  # Show first 5
                print(f"  - {path}")
            if len(summary["critical_paths"]) > 5:
                print(f"  ... and {len(summary['critical_paths']) - 5} more")

        if summary["recommendations"]:
            print("\nRecommendations:")
            for rec in summary["recommendations"]:
                print(f"  - {rec}")


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="ConfigMigrator: Automated YAML configuration migration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --golden config-v1.yaml --template template-v1.yaml \\
           --new-template template-v2.yaml --output config-v2.yaml \\
           --log migration-log.json

  %(prog)s --golden config-v1.yaml --template template-v1.yaml \\
           --new-template template-v2.yaml --output config-v2.yaml \\
           --log migration-log.csv --format csv --dry-run --verbose

  %(prog)s --golden config-v1.yaml --template template-v1.yaml \\
           --new-template template-v2.yaml --output config-v2.yaml \\
           --log migration-log.json --dynamic \\
           --discovery-report discovery-report.json --verbose
        """,
    )

    # Required arguments
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "--golden", required=True, help="Path to V_OLD golden configuration file"
    )
    required.add_argument(
        "--template", required=True, help="Path to V_OLD template file"
    )
    required.add_argument(
        "--new-template", required=True, help="Path to V_NEW template file"
    )
    required.add_argument(
        "--output",
        required=True,
        help="Path for output V_NEW golden configuration",
    )
    required.add_argument(
        "--log", required=True, help="Path for migration conflict log"
    )

    # Optional arguments
    parser.add_argument(
        "--map", help="Path to JSON file with old-path to new-path mappings"
    )
    parser.add_argument(
        "--rules",
        help="Path to network migration rules JSON file (default: network_migration_rules.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format for conflict log (default: json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate log without writing output configuration",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Enable dynamic structural migration discovery (experimental)",
    )
    parser.add_argument(
        "--discovery-report",
        help="Path to export dynamic discovery report (optional, requires --dynamic)",
    )
    parser.add_argument("--version", action="version", version="ConfigMigrator 0.1.0")

    return parser


def main() -> None:
    """Main entry point for command-line interface."""
    parser = create_parser()
    args = parser.parse_args()

    # Create migrator instance
    migrator = ConfigMigrator(rules_file_path=args.rules)

    # Perform migration
    success = migrator.migrate(
        golden_old_path=args.golden,
        template_old_path=args.template,
        template_new_path=args.new_template,
        output_config_path=args.output,
        output_log_path=args.log,
        migration_map_path=args.map,
        output_format=args.format,
        dry_run=args.dry_run,
        verbose=args.verbose,
        enable_dynamic_discovery=args.dynamic,
        dynamic_discovery_report_path=args.discovery_report,
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
