"""
Integration tests for the complete config migration workflow.
"""

import os
import tempfile

from cvpilot.core.merger import ConfigMerger
from cvpilot.core.parser import YAMLParser


class TestIntegration:
    """Integration tests for the complete workflow."""

    def test_complete_migration_workflow(self):
        """Test the complete migration workflow from flowchart."""
        # Create test data representing the actual files
        engprev_data = {
            "global": {
                "repository": "docker_repo:5000/occne",
                "sitename": "cndbtiersitename",
                "version": "25.1.102",
                "namespace": "occne-cndbtier",
            },
            "api": {
                "replicas": 2,
                "resources": {
                    "limits": {"cpu": 4, "memory": "4Gi"},
                },
            },
        }

        engnew_data = {
            "global": {
                "version": "25.1.200",
                "serviceMode": {
                    "internal": "IPv4",
                    "external": {"ndbmysqldsvc": "IPv4"},
                },
            },
            "api": {
                "max_binlog_size": 1073741824,
            },
            "new_feature": {
                "enabled": True,
            },
        }

        nsprev_data = {
            "global": {
                "repository": "registry.mtce.vzwops.com/ws_core/5ee22af33858010001ac40e5/occne",
                "sitename": "rcnltxekvzwcslf-y-or-x-004",
                "namespace": "rcnltxekvzwcslf-y-or-x-004",
            },
            "api": {
                "replicas": 4,
                "resources": {
                    "limits": {"cpu": 8, "memory": "8Gi"},
                },
            },
        }

        # Step 1: Process the files (load YAML)
        engprev_file = self._create_temp_yaml(engprev_data)
        engnew_file = self._create_temp_yaml(engnew_data)
        nsprev_file = self._create_temp_yaml(nsprev_data)

        try:
            # Step 2: Validate syntax of all input files
            file_paths = [nsprev_file, engprev_file, engnew_file]
            parser = YAMLParser()
            is_valid, error = parser.validate_all_files(file_paths)
            assert is_valid, f"Validation failed: {error}"

            # Load the files
            engprev_loaded = parser.load_yaml_file(engprev_file)
            engnew_loaded = parser.load_yaml_file(engnew_file)
            nsprev_loaded = parser.load_yaml_file(nsprev_file)

            # Step 3: Stage 1 - Extract differences between NSPREV and ENGPREV
            differences = ConfigMerger.compare_configs(engprev_loaded, nsprev_loaded)
            assert len(differences) > 0, (
                "Should find differences between NSPREV and ENGPREV"
            )

            # Step 4: Stage 1 - Create diff file with differences only
            diff_data = ConfigMerger.merge_configs_stage1(nsprev_loaded, engprev_loaded)

            # Stage 1 should only contain differences, not complete merge
            assert "global" in diff_data
            assert (
                diff_data["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
            )  # Modified in NSPREV
            assert (
                diff_data["global"]["namespace"] == "rcnltxekvzwcslf-y-or-x-004"
            )  # Modified in NSPREV
            assert (
                diff_data["global"]["repository"]
                == "registry.mtce.vzwops.com/ws_core/5ee22af33858010001ac40e5/occne"
            )  # Modified in NSPREV
            # version should NOT be in diff since it's same in both NSPREV and ENGPREV
            assert "version" not in diff_data["global"]

            assert "api" in diff_data
            assert diff_data["api"]["replicas"] == 4  # Modified in NSPREV
            assert (
                diff_data["api"]["resources"]["limits"]["cpu"] == 8
            )  # Modified in NSPREV
            assert (
                diff_data["api"]["resources"]["limits"]["memory"] == "8Gi"
            )  # Modified in NSPREV

            # Step 5: Stage 2 - Merge diff with ENGNEW (with precedence order)
            final_config = ConfigMerger.merge_configs_stage2(
                diff_data, engnew_loaded, engprev_loaded
            )

            # Verify final precedence: NSPREV > ENGNEW > ENGPREV
            assert (
                final_config["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
            )  # From NSPREV (highest)
            assert (
                final_config["global"]["version"] == "25.1.200"
            )  # From ENGNEW (overrides ENGPREV)
            assert final_config["api"]["replicas"] == 4  # From NSPREV (highest)
            assert (
                final_config["api"]["max_binlog_size"] == 1073741824
            )  # From ENGNEW (new feature)
            assert "new_feature" in final_config  # From ENGNEW

            # Test saving the final configuration
            output_file = tempfile.mktemp(suffix=".yaml")
            parser.save_yaml_file(final_config, output_file)

            # Verify the saved file can be loaded back
            loaded_output = parser.load_yaml_file(output_file)
            assert loaded_output == final_config

            os.unlink(output_file)

        finally:
            # Clean up temp files
            for temp_file in [engprev_file, engnew_file, nsprev_file]:
                os.unlink(temp_file)

    def test_nsprev_precedence_rules(self):
        """Test that NSPREV values take highest precedence in Stage 1 difference extraction."""
        engprev = {
            "global": {
                "sitename": "template",
                "services": ["service1", "service2"],
                "config": {
                    "key1": "value1",
                    "key2": "value2",
                },
            },
        }

        engnew = {
            "global": {
                "services": ["service3", "service4"],
                "config": {
                    "key2": "new_value2",
                    "key3": "value3",
                },
            },
        }

        nsprev = {
            "global": {
                "sitename": "site-specific",
                "services": ["service5", "service6"],
                "config": {
                    "key1": "site_value1",
                    "key2": "site_value2",
                },
            },
        }

        # Stage 1: Extract differences between NSPREV and ENGPREV
        diff_result = ConfigMerger.merge_configs_stage1(nsprev, engprev)

        # Stage 1 should only contain differences from NSPREV
        assert "global" in diff_result
        assert (
            diff_result["global"]["sitename"] == "site-specific"
        )  # Different from ENGPREV
        assert diff_result["global"]["services"] == [
            "service5",
            "service6",
        ]  # Different from ENGPREV
        assert (
            diff_result["global"]["config"]["key1"] == "site_value1"
        )  # Different from ENGPREV
        assert (
            diff_result["global"]["config"]["key2"] == "site_value2"
        )  # Different from ENGPREV

        # Stage 2: Apply differences with precedence order
        final_result = ConfigMerger.merge_configs_stage2(diff_result, engnew, engprev)

        # NSPREV should have highest precedence
        assert final_result["global"]["sitename"] == "site-specific"  # From NSPREV
        assert final_result["global"]["services"] == [
            "service5",
            "service6",
        ]  # From NSPREV
        assert final_result["global"]["config"]["key1"] == "site_value1"  # From NSPREV
        assert (
            final_result["global"]["config"]["key2"] == "site_value2"
        )  # From NSPREV (overrides ENGNEW)

        # ENGNEW should provide new features not in NSPREV
        assert final_result["global"]["config"]["key3"] == "value3"  # From ENGNEW

    def _create_temp_yaml(self, data):
        """Create a temporary YAML file with the given data."""
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            return f.name
