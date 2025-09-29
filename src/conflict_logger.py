"""Structured audit logging and conflict reporting."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConflictLogger:
    """Generate structured audit logs for configuration migration."""

    def __init__(self) -> None:
        """Initialize conflict logger."""
        self.log_entries: List[Dict[str, Any]] = []

    def add_log_entry(
        self,
        path: str,
        action_type: str,
        source_value: Any,
        target_value: Any,
        new_default_value: Any,
        reason: str,
        manual_review: bool = False
    ) -> None:
        """Add a new log entry to the conflict log.

        Args:
            path: Configuration path in dot notation.
            action_type: Type of action taken (OVERWRITE, DELETED, etc.).
            source_value: Original value from golden config.
            target_value: Final value in merged config.
            new_default_value: Default value from new template.
            reason: Human-readable explanation of the action.
            manual_review: Whether manual review is required.
        """
        entry = self.create_log_entry(
            path, action_type, source_value, target_value,
            new_default_value, reason, manual_review
        )
        self.log_entries.append(entry)

    def create_log_entry(
        self,
        path: str,
        action_type: str,
        source_value: Any,
        target_value: Any,
        new_default_value: Any,
        reason: str,
        manual_review: bool = False
    ) -> Dict[str, Any]:
        """Create a standardized log entry.

        Args:
            path: Configuration path in dot notation.
            action_type: Type of action taken.
            source_value: Original value from golden config.
            target_value: Final value in merged config.
            new_default_value: Default value from new template.
            reason: Human-readable explanation.
            manual_review: Whether manual review is required.

        Returns:
            Formatted log entry dictionary.
        """
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": path,
            "action_type": action_type,
            "source_value": self._serialize_value(source_value),
            "target_value": self._serialize_value(target_value),
            "new_default_value": self._serialize_value(new_default_value),
            "reason": reason,
            "manual_review": manual_review
        }

    def export_to_json(self, output_path: str, log_entries: Optional[List[Dict[str, Any]]] = None) -> None:
        """Export conflict log to JSON format.

        Args:
            output_path: Path for the output JSON file.
            log_entries: Optional list of log entries (uses instance entries if None).

        Raises:
            OSError: If file cannot be written.
            ValueError: If log entries cannot be serialized.
        """
        entries_to_export = log_entries if log_entries is not None else self.log_entries

        output_data = {
            "migration_summary": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_entries": len(entries_to_export),
                "manual_review_required": sum(1 for entry in entries_to_export if entry.get("manual_review", False)),
                "statistics": self._generate_statistics(entries_to_export)
            },
            "conflicts": entries_to_export
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(output_data, file, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Cannot write JSON file {output_path}: {e}") from e
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize log entries to JSON: {e}") from e

    def export_to_csv(self, output_path: str, log_entries: Optional[List[Dict[str, Any]]] = None) -> None:
        """Export conflict log to CSV format.

        Args:
            output_path: Path for the output CSV file.
            log_entries: Optional list of log entries (uses instance entries if None).

        Raises:
            OSError: If file cannot be written.
        """
        entries_to_export = log_entries if log_entries is not None else self.log_entries

        if not entries_to_export:
            # Create empty CSV with headers
            entries_to_export = [self._get_empty_log_entry()]

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "timestamp", "path", "action_type", "source_value",
            "target_value", "new_default_value", "reason", "manual_review"
        ]

        try:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for entry in entries_to_export:
                    # Convert values to strings for CSV
                    csv_entry = {
                        key: self._format_value_for_csv(entry.get(key))
                        for key in fieldnames
                    }
                    writer.writerow(csv_entry)

        except OSError as e:
            raise OSError(f"Cannot write CSV file {output_path}: {e}") from e

    def filter_entries(
        self,
        action_type: Optional[str] = None,
        manual_review_only: bool = False,
        path_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter log entries based on criteria.

        Args:
            action_type: Filter by specific action type.
            manual_review_only: Only return entries requiring manual review.
            path_pattern: Filter by path containing this substring.

        Returns:
            Filtered list of log entries.
        """
        filtered = self.log_entries

        if action_type:
            filtered = [entry for entry in filtered if entry.get("action_type") == action_type]

        if manual_review_only:
            filtered = [entry for entry in filtered if entry.get("manual_review", False)]

        if path_pattern:
            filtered = [entry for entry in filtered if path_pattern in entry.get("path", "")]

        return filtered

    def get_summary_report(self, log_entries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a summary report of the migration.

        Args:
            log_entries: Optional list of log entries (uses instance entries if None).

        Returns:
            Dictionary containing summary statistics and recommendations.
        """
        entries_to_analyze = log_entries if log_entries is not None else self.log_entries

        statistics = self._generate_statistics(entries_to_analyze)
        manual_review_entries = [entry for entry in entries_to_analyze if entry.get("manual_review", False)]

        recommendations = self._generate_recommendations(entries_to_analyze, statistics)

        return {
            "migration_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_conflicts": len(entries_to_analyze),
            "manual_review_required": len(manual_review_entries),
            "statistics": statistics,
            "critical_paths": [entry["path"] for entry in manual_review_entries],
            "recommendations": recommendations,
            "success_rate": self._calculate_success_rate(statistics)
        }

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON compatibility.

        Args:
            value: Value to serialize.

        Returns:
            JSON-serializable representation of the value.
        """
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (dict, list)):
            return value
        else:
            # Convert other types to string representation
            return str(value)

    def _format_value_for_csv(self, value: Any) -> str:
        """Format a value for CSV output.

        Args:
            value: Value to format.

        Returns:
            String representation suitable for CSV.
        """
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)

    def _get_empty_log_entry(self) -> Dict[str, Any]:
        """Get an empty log entry with all fields.

        Returns:
            Empty log entry dictionary.
        """
        return {
            "timestamp": "",
            "path": "",
            "action_type": "",
            "source_value": None,
            "target_value": None,
            "new_default_value": None,
            "reason": "",
            "manual_review": False
        }

    def _generate_statistics(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from log entries.

        Args:
            entries: List of log entries to analyze.

        Returns:
            Dictionary containing various statistics.
        """
        if not entries:
            return {
                "by_action_type": {},
                "manual_review_count": 0,
                "successful_overwrites": 0,
                "data_loss_count": 0
            }

        by_action_type: Dict[str, int] = {}
        manual_review_count = 0
        successful_overwrites = 0
        data_loss_count = 0

        for entry in entries:
            action_type = entry.get("action_type", "UNKNOWN")
            by_action_type[action_type] = by_action_type.get(action_type, 0) + 1

            if entry.get("manual_review", False):
                manual_review_count += 1

            if action_type == "OVERWRITE" and not entry.get("manual_review", False):
                successful_overwrites += 1

            if action_type in ["DELETED", "STRUCTURAL_MISMATCH"]:
                data_loss_count += 1

        return {
            "by_action_type": by_action_type,
            "manual_review_count": manual_review_count,
            "successful_overwrites": successful_overwrites,
            "data_loss_count": data_loss_count
        }

    def _generate_recommendations(self, entries: List[Dict[str, Any]], statistics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on migration results.

        Args:
            entries: List of log entries.
            statistics: Statistics dictionary.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        manual_review_count = statistics.get("manual_review_count", 0)
        data_loss_count = statistics.get("data_loss_count", 0)
        total_conflicts = len(entries)

        if manual_review_count > 0:
            recommendations.append(
                f"Manual review required for {manual_review_count} configuration changes. "
                "Review entries marked with 'manual_review': true before deployment."
            )

        if data_loss_count > 0:
            recommendations.append(
                f"Potential data loss detected in {data_loss_count} configurations. "
                "Verify that removed or incompatible settings are intentional."
            )

        if total_conflicts == 0:
            recommendations.append("No conflicts detected. Configuration migration completed successfully.")
        elif manual_review_count / total_conflicts > 0.5:
            recommendations.append(
                "High number of manual review items detected. Consider reviewing template "
                "compatibility or providing a migration map for renamed fields."
            )

        structural_mismatches = statistics.get("by_action_type", {}).get("STRUCTURAL_MISMATCH", 0)
        if structural_mismatches > 0:
            recommendations.append(
                f"{structural_mismatches} structural mismatches found. These may indicate "
                "incompatible changes in the new template version."
            )

        return recommendations

    def _calculate_success_rate(self, statistics: Dict[str, Any]) -> float:
        """Calculate the success rate of the migration.

        Args:
            statistics: Statistics dictionary.

        Returns:
            Success rate as a percentage (0.0 to 100.0).
        """
        total_actions = sum(statistics.get("by_action_type", {}).values())
        if total_actions == 0:
            return 100.0

        successful_actions = statistics.get("successful_overwrites", 0)
        added_actions = statistics.get("by_action_type", {}).get("ADDED", 0)
        successful_actions += added_actions  # ADDED actions are also successful

        return (successful_actions / total_actions) * 100.0

    def clear_log(self) -> None:
        """Clear all log entries."""
        self.log_entries.clear()

    def get_log_entries(self) -> List[Dict[str, Any]]:
        """Get a copy of all log entries.

        Returns:
            Copy of the log entries list.
        """
        return self.log_entries.copy()
