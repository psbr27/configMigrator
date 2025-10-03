"""
Integration tests for the complete config migration workflow.
"""

import os
import tempfile

from config_migrator.core.merger import ConfigMerger
from config_migrator.core.parser import YAMLParser


class TestIntegration:
    """Integration tests for the complete workflow."""

    def test_complete_migration_workflow(self):
        """Test the complete migration workflow from flowchart."""
        # Create test data representing the actual files
        etf_data = {
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

        newtf_data = {
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

        nstf_data = {
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
        etf_file = self._create_temp_yaml(etf_data)
        newtf_file = self._create_temp_yaml(newtf_data)
        nstf_file = self._create_temp_yaml(nstf_data)

        try:
            # Step 2: Validate syntax of both input files (Stage 1)
            file_paths = [etf_file, nstf_file]
            parser = YAMLParser()
            is_valid, error = parser.validate_all_files(file_paths)
            assert is_valid, f"Validation failed: {error}"

            # Load the files
            etf_loaded = parser.load_yaml_file(etf_file)
            nstf_loaded = parser.load_yaml_file(nstf_file)

            # Step 3: Compare 1 & 2 files (NSTF vs ETF)
            differences = ConfigMerger.compare_configs(etf_loaded, nstf_loaded)
            assert len(differences) > 0, "Should find differences between NSTF and ETF"

            # Step 4: Create diff_nstf_etf.yaml file with NSTF precedence
            merged_config = ConfigMerger.merge_configs_stage1(nstf_loaded, etf_loaded)

            # Verify NSTF precedence
            assert merged_config["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
            assert merged_config["global"]["namespace"] == "rcnltxekvzwcslf-y-or-x-004"
            assert merged_config["api"]["replicas"] == 4

            # Verify ETF base values are preserved where not overridden
            assert merged_config["global"]["version"] == "25.1.102"  # From ETF
            assert merged_config["api"]["resources"]["limits"]["cpu"] == 8  # From NSTF

            # Verify ETF base values are preserved where not overridden
            assert (
                merged_config["global"]["repository"]
                == "registry.mtce.vzwops.com/ws_core/5ee22af33858010001ac40e5/occne"
            )

            # Test saving the merged configuration
            output_file = tempfile.mktemp(suffix=".yaml")
            parser.save_yaml_file(merged_config, output_file)

            # Verify the saved file can be loaded back
            loaded_output = parser.load_yaml_file(output_file)
            assert loaded_output == merged_config

            os.unlink(output_file)

        finally:
            # Clean up temp files
            for temp_file in [etf_file, newtf_file, nstf_file]:
                os.unlink(temp_file)

    def test_nstf_precedence_rules(self):
        """Test that NSTF values take highest precedence in lists and maps."""
        etf = {
            "global": {
                "sitename": "template",
                "services": ["service1", "service2"],
                "config": {
                    "key1": "value1",
                    "key2": "value2",
                },
            },
        }

        _newtf = {
            "global": {
                "services": ["service3", "service4"],
                "config": {
                    "key2": "new_value2",
                    "key3": "value3",
                },
            },
        }

        nstf = {
            "global": {
                "sitename": "site-specific",
                "services": ["service5", "service6"],
                "config": {
                    "key1": "site_value1",
                    "key2": "site_value2",
                },
            },
        }

        result = ConfigMerger.merge_configs_stage1(nstf, etf)

        # NSTF should override everything
        assert result["global"]["sitename"] == "site-specific"
        assert result["global"]["services"] == ["service5", "service6"]
        assert result["global"]["config"]["key1"] == "site_value1"
        assert result["global"]["config"]["key2"] == "site_value2"

        # ETF base values should be preserved where not overridden
        assert result["global"]["config"]["key2"] == "site_value2"  # NSTF overrides ETF

    def _create_temp_yaml(self, data):
        """Create a temporary YAML file with the given data."""
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            return f.name
