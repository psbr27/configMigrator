"""Migration suggestion and execution engine for discovered structural changes."""

import copy
import json
from typing import Any, Dict, List, Tuple

try:
    from ..diff_analyzer import DiffAnalyzer
    from .dynamic_detector import DiscoveredMigration, MigrationCandidate
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from diff_analyzer import DiffAnalyzer
    from dynamic_detector import DiscoveredMigration, MigrationCandidate


class MigrationSuggester:
    """Generate and execute migration suggestions based on discovered patterns."""

    def __init__(self, enable_verbose_logging: bool = False) -> None:
        """Initialize migration suggester.

        Args:
            enable_verbose_logging: Enable detailed logging for migration steps.
        """
        self.diff_analyzer = DiffAnalyzer()
        self.verbose = enable_verbose_logging

    def generate_migration_report(
        self, migrations: List[DiscoveredMigration]
    ) -> Dict[str, Any]:
        """Generate a comprehensive migration report.

        Args:
            migrations: List of discovered migrations.

        Returns:
            Detailed migration report with suggestions and actions.
        """
        auto_apply = []
        require_review = []
        low_confidence = []

        for migration in migrations:
            if (
                migration.confidence >= 0.8
                and migration.best_candidate
                and not migration.best_candidate.requires_human_review
            ):
                auto_apply.append(migration)
            elif migration.confidence >= 0.5:
                require_review.append(migration)
            else:
                low_confidence.append(migration)

        report = {
            "summary": {
                "total_migrations": len(migrations),
                "auto_apply_count": len(auto_apply),
                "review_required_count": len(require_review),
                "low_confidence_count": len(low_confidence),
            },
            "auto_apply_migrations": [
                self._format_migration_entry(m) for m in auto_apply
            ],
            "review_required_migrations": [
                self._format_migration_entry(m) for m in require_review
            ],
            "low_confidence_migrations": [
                self._format_migration_entry(m) for m in low_confidence
            ],
            "recommendations": self._generate_recommendations(migrations),
        }

        return report

    def apply_automatic_migrations(
        self, migrations: List[DiscoveredMigration], target_config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Apply migrations that meet automatic application criteria.

        Args:
            migrations: List of discovered migrations.
            target_config: Configuration to apply migrations to.

        Returns:
            Tuple of (updated_config, migration_log).
        """
        updated_config = copy.deepcopy(target_config)
        migration_log = []

        auto_apply_migrations = [
            m
            for m in migrations
            if m.confidence >= 0.8
            and m.best_candidate
            and not m.best_candidate.requires_human_review
        ]

        if self.verbose:
            print(f"🤖 Applying {len(auto_apply_migrations)} automatic migrations...")

        for migration in auto_apply_migrations:
            try:
                success = self._apply_single_migration(migration, updated_config)
                log_entry = {
                    "old_path": migration.old_path,
                    "new_path": migration.best_candidate.new_path,
                    "custom_value": migration.custom_value,
                    "migration_type": migration.migration_type,
                    "confidence": migration.confidence,
                    "success": success,
                    "evidence": migration.best_candidate.evidence,
                    "applied_automatically": True,
                }
                migration_log.append(log_entry)

                if self.verbose and success:
                    print(
                        f"✅ Applied: {migration.old_path} → {migration.best_candidate.new_path}"
                    )

            except Exception as e:
                error_log = {
                    "old_path": migration.old_path,
                    "new_path": migration.best_candidate.new_path
                    if migration.best_candidate
                    else "unknown",
                    "custom_value": migration.custom_value,
                    "success": False,
                    "error": str(e),
                    "applied_automatically": True,
                }
                migration_log.append(error_log)

                if self.verbose:
                    print(f"❌ Failed: {migration.old_path} - {e}")

        return updated_config, migration_log

    def create_migration_map(
        self,
        migrations: List[DiscoveredMigration],
        include_low_confidence: bool = False,
    ) -> Dict[str, str]:
        """Create a migration map from discovered migrations.

        Args:
            migrations: List of discovered migrations.
            include_low_confidence: Whether to include low-confidence migrations.

        Returns:
            Dictionary mapping old paths to new paths.
        """
        migration_map = {}

        for migration in migrations:
            if not migration.best_candidate:
                continue

            # Skip low confidence migrations unless explicitly requested
            if migration.confidence < 0.5 and not include_low_confidence:
                continue

            migration_map[migration.old_path] = migration.best_candidate.new_path

        return migration_map

    def suggest_manual_migrations(
        self, migrations: List[DiscoveredMigration]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for manual migration review.

        Args:
            migrations: List of discovered migrations.

        Returns:
            List of formatted suggestions for manual review.
        """
        suggestions = []

        review_migrations = [
            m
            for m in migrations
            if 0.5 <= m.confidence < 0.8
            or (m.best_candidate and m.best_candidate.requires_human_review)
        ]

        for migration in review_migrations:
            suggestion = {
                "old_path": migration.old_path,
                "custom_value": migration.custom_value,
                "migration_type": migration.migration_type,
                "confidence": migration.confidence,
                "primary_suggestion": self._format_candidate(migration.best_candidate)
                if migration.best_candidate
                else None,
                "alternative_suggestions": [
                    self._format_candidate(candidate)
                    for candidate in migration.candidates[1:3]
                ],
                "recommendation": self._generate_migration_recommendation(migration),
                "risks": self._assess_migration_risks(migration),
                "manual_steps": self._generate_manual_steps(migration),
            }
            suggestions.append(suggestion)

        return suggestions

    def _apply_single_migration(
        self, migration: DiscoveredMigration, target_config: Dict[str, Any]
    ) -> bool:
        """Apply a single migration to the target configuration.

        Args:
            migration: Migration to apply.
            target_config: Configuration to modify.

        Returns:
            True if migration was applied successfully.
        """
        if not migration.best_candidate:
            return False

        try:
            new_path = migration.best_candidate.new_path
            custom_value = migration.custom_value

            # Handle field mapping if present
            if migration.best_candidate.field_mapping:
                # For field mappings, we might need to transform the value
                custom_value = self._apply_field_mapping(
                    custom_value, migration.best_candidate.field_mapping
                )

            # Handle array path notation (e.g., "accounts[0].serviceAccountName")
            if "[" in new_path and "]" in new_path:
                return self._apply_array_migration(
                    new_path, custom_value, target_config, migration.best_candidate
                )
            else:
                # Simple path assignment
                self.diff_analyzer.set_nested_value(
                    target_config, new_path, custom_value
                )

            # Apply metadata additions if present
            if migration.best_candidate.metadata_additions:
                self._apply_metadata_additions(
                    new_path, migration.best_candidate.metadata_additions, target_config
                )

            return True

        except Exception:
            return False

    def _apply_array_migration(
        self,
        array_path: str,
        custom_value: Any,
        target_config: Dict[str, Any],
        candidate: MigrationCandidate,
    ) -> bool:
        """Apply migration to an array-indexed path.

        Args:
            array_path: Path with array notation like "accounts[0].field".
            custom_value: Value to apply.
            target_config: Configuration to modify.
            candidate: Migration candidate with additional context.

        Returns:
            True if successfully applied.
        """
        try:
            # Parse array path: "global.autoCreateResources.serviceAccounts.accounts[0].serviceAccountName"
            if not ("[" in array_path and "]" in array_path):
                return False

            # Split on the first array index
            before_array, after_array = array_path.split("[", 1)
            index_part, field_part = after_array.split("]", 1)
            index = int(index_part)

            # Get the array
            array = self.diff_analyzer.get_nested_value(target_config, before_array)
            if not isinstance(array, list) or len(array) <= index:
                return False

            # Apply the value to the array element
            if field_part.startswith("."):
                field_path = field_part[1:]  # Remove leading dot
                if "." in field_path:
                    # Nested field in array element
                    self.diff_analyzer.set_nested_value(
                        array[index], field_path, custom_value
                    )
                else:
                    # Direct field in array element
                    array[index][field_path] = custom_value
            else:
                # Direct array assignment
                array[index] = custom_value

            return True

        except (ValueError, KeyError, IndexError, TypeError):
            return False

    def _apply_field_mapping(self, value: Any, field_mapping: Dict[str, str]) -> Any:
        """Apply field name mappings to a value.

        Args:
            value: Original value.
            field_mapping: Mapping of old field names to new field names.

        Returns:
            Transformed value with field mappings applied.
        """
        if isinstance(value, dict):
            mapped_value = {}
            for old_key, val in value.items():
                new_key = field_mapping.get(old_key, old_key)
                mapped_value[new_key] = val
            return mapped_value
        else:
            # For non-dict values, return as-is
            return value

    def _apply_metadata_additions(
        self, path: str, metadata: Dict[str, Any], target_config: Dict[str, Any]
    ) -> None:
        """Apply metadata additions to a configuration path.

        Args:
            path: Configuration path.
            metadata: Metadata to add.
            target_config: Configuration to modify.
        """
        try:
            # Get the parent object
            if "." in path:
                parent_path = ".".join(path.split(".")[:-1])
                parent_obj = self.diff_analyzer.get_nested_value(
                    target_config, parent_path
                )
                if isinstance(parent_obj, dict):
                    parent_obj.update(metadata)
        except (KeyError, TypeError):
            pass  # Ignore metadata addition failures

    def _format_migration_entry(self, migration: DiscoveredMigration) -> Dict[str, Any]:
        """Format a migration for report output.

        Args:
            migration: Migration to format.

        Returns:
            Formatted migration entry.
        """
        return {
            "old_path": migration.old_path,
            "custom_value": migration.custom_value,
            "suggested_new_path": migration.best_candidate.new_path
            if migration.best_candidate
            else None,
            "confidence": migration.confidence,
            "migration_type": migration.migration_type,
            "evidence": migration.best_candidate.evidence
            if migration.best_candidate
            else "",
            "requires_review": migration.best_candidate.requires_human_review
            if migration.best_candidate
            else True,
            "alternatives_count": len(migration.candidates) - 1,
        }

    def _format_candidate(self, candidate: MigrationCandidate) -> Dict[str, Any]:
        """Format a migration candidate for output.

        Args:
            candidate: Candidate to format.

        Returns:
            Formatted candidate information.
        """
        return {
            "new_path": candidate.new_path,
            "similarity_type": candidate.similarity_type,
            "similarity_score": candidate.similarity_score,
            "evidence": candidate.evidence,
            "requires_review": candidate.requires_human_review,
            "field_mapping": candidate.field_mapping,
            "metadata_additions": candidate.metadata_additions,
        }

    def _generate_recommendations(
        self, migrations: List[DiscoveredMigration]
    ) -> List[str]:
        """Generate overall recommendations based on migration analysis.

        Args:
            migrations: List of discovered migrations.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        total_migrations = len(migrations)
        high_confidence = sum(1 for m in migrations if m.confidence >= 0.8)
        medium_confidence = sum(1 for m in migrations if 0.5 <= m.confidence < 0.8)

        if total_migrations == 0:
            recommendations.append(
                "No structural migrations detected. Standard migration should handle all changes."
            )
        elif high_confidence == total_migrations:
            recommendations.append(
                "All migrations have high confidence. Consider enabling automatic application."
            )
        elif medium_confidence > 0:
            recommendations.append(
                f"{medium_confidence} migrations require manual review before applying."
            )

        # Check for common migration patterns
        migration_types = [m.migration_type for m in migrations]
        if migration_types.count("path_consolidation") > 1:
            recommendations.append(
                "Multiple path consolidations detected. Review for consistency."
            )
        if migration_types.count("field_rename") > 1:
            recommendations.append(
                "Multiple field renames detected. Verify naming conventions."
            )

        return recommendations

    def _generate_migration_recommendation(self, migration: DiscoveredMigration) -> str:
        """Generate a specific recommendation for a migration.

        Args:
            migration: Migration to analyze.

        Returns:
            Recommendation string.
        """
        if migration.confidence >= 0.8:
            return "High confidence migration. Safe to apply automatically."
        elif migration.confidence >= 0.6:
            return (
                "Medium confidence migration. Review evidence and apply if appropriate."
            )
        elif migration.confidence >= 0.4:
            return "Low confidence migration. Carefully review before applying."
        else:
            return "Very low confidence. Consider manual investigation."

    def _assess_migration_risks(self, migration: DiscoveredMigration) -> List[str]:
        """Assess potential risks of applying a migration.

        Args:
            migration: Migration to assess.

        Returns:
            List of potential risks.
        """
        risks = []

        if migration.confidence < 0.5:
            risks.append("Low confidence score may indicate incorrect mapping")

        if migration.migration_type == "path_consolidation":
            risks.append("Path consolidation may require additional field mappings")

        if migration.migration_type == "structural_relocation":
            risks.append("Structural changes may affect dependent configurations")

        if isinstance(migration.custom_value, dict) and len(migration.custom_value) > 3:
            risks.append("Complex object migration may lose nested data")

        return risks

    def _generate_manual_steps(self, migration: DiscoveredMigration) -> List[str]:
        """Generate manual steps for applying a migration.

        Args:
            migration: Migration to create steps for.

        Returns:
            List of manual steps.
        """
        steps = []

        if not migration.best_candidate:
            steps.append(
                "No clear migration path found - manual investigation required"
            )
            return steps

        steps.append(
            f"1. Verify that '{migration.best_candidate.new_path}' is the correct target location"
        )
        steps.append("2. Check compatibility between old value type and new location")

        if migration.best_candidate.field_mapping:
            steps.append("3. Apply field name mappings as needed")

        if migration.best_candidate.metadata_additions:
            steps.append("4. Add required metadata fields")

        steps.append(
            "5. Test the migrated configuration in a non-production environment"
        )

        return steps

    def export_migration_report(
        self, report: Dict[str, Any], output_path: str, format: str = "json"
    ) -> None:
        """Export migration report to file.

        Args:
            report: Migration report to export.
            output_path: Path to write the report.
            format: Output format ('json' or 'text').
        """
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
        elif format == "text":
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_text_report(report, f)

    def _write_text_report(self, report: Dict[str, Any], file) -> None:
        """Write migration report in text format.

        Args:
            report: Migration report.
            file: File object to write to.
        """
        file.write("DYNAMIC MIGRATION DISCOVERY REPORT\\n")
        file.write("=" * 50 + "\\n\\n")

        summary = report["summary"]
        file.write(f"Total Migrations Found: {summary['total_migrations']}\\n")
        file.write(f"Auto-Apply Ready: {summary['auto_apply_count']}\\n")
        file.write(f"Review Required: {summary['review_required_count']}\\n")
        file.write(f"Low Confidence: {summary['low_confidence_count']}\\n\\n")

        if report["auto_apply_migrations"]:
            file.write("AUTO-APPLY MIGRATIONS\\n")
            file.write("-" * 25 + "\\n")
            for migration in report["auto_apply_migrations"]:
                file.write(
                    f"• {migration['old_path']} → {migration['suggested_new_path']}\\n"
                )
                file.write(f"  Confidence: {migration['confidence']:.2f}\\n")
                file.write(f"  Evidence: {migration['evidence']}\\n\\n")

        if report["review_required_migrations"]:
            file.write("REVIEW REQUIRED MIGRATIONS\\n")
            file.write("-" * 30 + "\\n")
            for migration in report["review_required_migrations"]:
                file.write(
                    f"• {migration['old_path']} → {migration['suggested_new_path']}\\n"
                )
                file.write(f"  Confidence: {migration['confidence']:.2f}\\n")
                file.write(f"  Evidence: {migration['evidence']}\\n\\n")

        if report["recommendations"]:
            file.write("RECOMMENDATIONS\\n")
            file.write("-" * 15 + "\\n")
            for rec in report["recommendations"]:
                file.write(f"• {rec}\\n")
