"""Tests for merge engine module."""


from src.merge_engine import ConflictResolution, MergeEngine


class TestMergeEngine:
    """Test cases for MergeEngine class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = MergeEngine()

    def test_simple_overwrite_scenario(self) -> None:
        """Test simple custom value overwrite scenario."""
        golden_config = {
            "service": {
                "name": "my-service",
                "port": 8080,
                "timeout": 60,  # Custom value
            }
        }

        template_old = {
            "service": {
                "name": "my-service",
                "port": 8080,
                "timeout": 30,  # Default value
            }
        }

        template_new = {
            "service": {
                "name": "my-service",
                "port": 8080,
                "timeout": 45,  # New default value
            }
        }

        final_config, conflict_log = self.engine.merge_configurations(
            golden_config, template_old, template_new
        )

        # Custom timeout should be preserved
        assert final_config["service"]["timeout"] == 60

        # Should have one conflict log entry for the overwrite
        assert len(conflict_log) == 1
        log_entry = conflict_log[0]
        assert log_entry["path"] == "service.timeout"
        assert log_entry["action_type"] == ConflictResolution.OVERWRITE.value
        assert log_entry["source_value"] == 60
        assert log_entry["target_value"] == 60
        assert log_entry["new_default_value"] == 45
        assert log_entry["manual_review"] is False

    def test_deleted_key_scenario(self) -> None:
        """Test handling of keys deleted in new template."""
        golden_config = {
            "service": {"name": "my-service", "deprecated_setting": "custom-value"}
        }

        template_old = {
            "service": {"name": "my-service", "deprecated_setting": "default-value"}
        }

        template_new = {
            "service": {
                "name": "my-service"
                # deprecated_setting removed
            }
        }

        final_config, conflict_log = self.engine.merge_configurations(
            golden_config, template_old, template_new
        )

        # Deleted key should not be in final config
        assert "deprecated_setting" not in final_config["service"]

        # Should have conflict log entry for deletion
        assert len(conflict_log) == 1
        log_entry = conflict_log[0]
        assert log_entry["path"] == "service.deprecated_setting"
        assert log_entry["action_type"] == ConflictResolution.DELETED.value
        assert log_entry["source_value"] == "custom-value"
        assert log_entry["target_value"] is None
        assert log_entry["manual_review"] is True

    def test_structural_mismatch_scenario(self) -> None:
        """Test handling of structural type changes."""
        golden_config = {"service": {"config": {"debug": True, "level": "info"}}}

        template_old = {"service": {"config": {"debug": False, "level": "warn"}}}

        template_new = {
            "service": {
                "config": ["debug", "level"]  # Changed from dict to list
            }
        }

        final_config, conflict_log = self.engine.merge_configurations(
            golden_config, template_old, template_new
        )

        # Should keep new template structure (list)
        assert isinstance(final_config["service"]["config"], list)
        assert final_config["service"]["config"] == ["debug", "level"]

        # Should have conflict log entries for structural mismatch
        conflict_paths = [entry["path"] for entry in conflict_log]
        assert "service.config.debug" in conflict_paths
        assert "service.config.level" in conflict_paths

        # All entries should require manual review
        for entry in conflict_log:
            if entry["action_type"] == ConflictResolution.STRUCTURAL_MISMATCH.value:
                assert entry["manual_review"] is True

    def test_apply_migrations(self) -> None:
        """Test applying path migrations."""
        custom_data = {
            "old.path.setting": "value1",
            "another.old.path": "value2",
            "unchanged.path": "value3",
        }

        migration_map = {
            "old.path.setting": "new.path.setting",
            "another.old.path": "another.new.path",
        }

        migrated_data = self.engine.apply_migrations(custom_data, migration_map)

        expected = {
            "new.path.setting": "value1",
            "another.new.path": "value2",
            "unchanged.path": "value3",
        }

        assert migrated_data == expected

    def test_validate_migration_map_valid(self) -> None:
        """Test validating a valid migration map."""
        migration_map = {"old.path.one": "new.path.one", "old.path.two": "new.path.two"}

        errors = self.engine.validate_migration_map(migration_map)
        assert errors == []

    def test_validate_migration_map_circular(self) -> None:
        """Test detecting circular references in migration map."""
        migration_map = {
            "path.a": "path.b",
            "path.b": "path.c",
            "path.c": "path.a",  # Circular reference
        }

        errors = self.engine.validate_migration_map(migration_map)
        assert len(errors) > 0
        assert any("circular" in error.lower() for error in errors)

    def test_validate_migration_map_invalid_paths(self) -> None:
        """Test detecting invalid path formats in migration map."""
        migration_map = {
            ".invalid.start": "valid.path",
            "valid.path": "invalid.end.",
            "valid.path2": "invalid..double.dot",
        }

        errors = self.engine.validate_migration_map(migration_map)
        assert len(errors) >= 3  # At least one error for each invalid path

    def test_get_merge_statistics(self) -> None:
        """Test generating merge statistics."""
        conflict_log = [
            {"action_type": ConflictResolution.OVERWRITE.value, "manual_review": False},
            {"action_type": ConflictResolution.OVERWRITE.value, "manual_review": False},
            {"action_type": ConflictResolution.DELETED.value, "manual_review": True},
            {
                "action_type": ConflictResolution.STRUCTURAL_MISMATCH.value,
                "manual_review": True,
            },
        ]

        stats = self.engine.get_merge_statistics(conflict_log)

        assert stats["total_conflicts"] == 4
        assert stats["by_action_type"][ConflictResolution.OVERWRITE.value] == 2
        assert stats["by_action_type"][ConflictResolution.DELETED.value] == 1
        assert (
            stats["by_action_type"][ConflictResolution.STRUCTURAL_MISMATCH.value] == 1
        )
        assert stats["manual_review_required"] == 2
        assert stats["successful_overwrites"] == 2

    def test_get_merge_statistics_empty(self) -> None:
        """Test generating statistics for empty conflict log."""
        stats = self.engine.get_merge_statistics([])

        assert stats["total_conflicts"] == 0
        assert stats["by_action_type"] == {}
        assert stats["manual_review_required"] == 0
        assert stats["successful_overwrites"] == 0

    def test_extract_custom_data(self) -> None:
        """Test extracting custom data."""
        golden_config = {
            "service": {
                "name": "custom-name",  # Different from template
                "port": 8080,  # Same as template
                "new_setting": "value",  # Not in template
            }
        }

        template_old = {"service": {"name": "default-name", "port": 8080}}

        custom_data = self.engine.extract_custom_data(golden_config, template_old)

        assert "service.name" in custom_data
        assert custom_data["service.name"] == "custom-name"
        assert "service.port" not in custom_data  # Same as template
        assert "service.new_setting" in custom_data
        assert custom_data["service.new_setting"] == "value"

    def test_complete_migration_workflow(self) -> None:
        """Test complete migration workflow with various scenarios."""
        golden_config = {
            "service": {
                "name": "my-service",  # Custom value
                "port": 8080,  # Same as old template
                "timeout": 120,  # Custom value
                "deprecated": "old-value",  # Will be deleted
            },
            "database": {
                "host": "custom-host",  # Custom value
                "port": 5432,  # Same as template
            },
        }

        template_old = {
            "service": {
                "name": "default-service",
                "port": 8080,
                "timeout": 30,
                "deprecated": "default-value",
            },
            "database": {"host": "localhost", "port": 5432},
        }

        template_new = {
            "service": {
                "name": "default-service",
                "port": 9000,  # Changed default
                "timeout": 45,  # Changed default
                # deprecated removed
                "new_setting": "default",  # Added
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "ssl": True,  # Added
            },
        }

        final_config, conflict_log = self.engine.merge_configurations(
            golden_config, template_old, template_new
        )

        # Verify final configuration
        assert final_config["service"]["name"] == "my-service"  # Custom preserved
        assert final_config["service"]["port"] == 9000  # New default (not customized)
        assert final_config["service"]["timeout"] == 120  # Custom preserved
        assert "deprecated" not in final_config["service"]  # Deleted
        assert final_config["service"]["new_setting"] == "default"  # New default

        assert final_config["database"]["host"] == "custom-host"  # Custom preserved
        assert final_config["database"]["port"] == 5432  # Same as template
        assert final_config["database"]["ssl"] is True  # New default

        # Verify conflict log
        assert len(conflict_log) > 0

        # Check for specific conflict types
        action_types = [entry["action_type"] for entry in conflict_log]
        assert ConflictResolution.OVERWRITE.value in action_types
        assert ConflictResolution.DELETED.value in action_types

        # Verify manual review flags
        manual_review_entries = [
            entry for entry in conflict_log if entry["manual_review"]
        ]
        deleted_entries = [
            entry
            for entry in conflict_log
            if entry["action_type"] == ConflictResolution.DELETED.value
        ]
        assert len(manual_review_entries) >= len(
            deleted_entries
        )  # Deleted entries require manual review
