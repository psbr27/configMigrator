#!/usr/bin/env python3
"""Network preservation end-to-end tests."""

import json
import sys
from pathlib import Path

import pytest
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_migrator import ConfigMigrator


class TestNetworkPreservation:
    """Test network-critical annotation preservation during migration."""

    @pytest.fixture(scope="class")
    def migration_results(self):
        """Run migration once and return results for all tests."""
        # Initialize migrator
        migrator = ConfigMigrator()

        # Define file paths relative to project root
        project_root = Path(__file__).parent.parent

        # Run migration
        success = migrator.migrate(
            golden_old_path=str(
                project_root / "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml"
            ),
            template_old_path=str(
                project_root / "occndbtier_custom_values_25.1.102.yaml"
            ),
            template_new_path=str(
                project_root / "occndbtier_custom_values_25.1.200.yaml"
            ),
            output_config_path=str(project_root / "test_network_output.yaml"),
            output_log_path=str(project_root / "test_network_log.json"),
            verbose=False,
        )

        assert success, "Migration should complete successfully"

        # Load results
        with open(project_root / "test_network_output.yaml") as f:
            result_config = yaml.safe_load(f)

        with open(project_root / "test_network_log.json") as f:
            log_data = json.load(f)

        yield {"config": result_config, "log": log_data, "success": success}

        # Cleanup
        for file_path in [
            project_root / "test_network_output.yaml",
            project_root / "test_network_log.json",
        ]:
            if file_path.exists():
                file_path.unlink()

    @staticmethod
    def get_nested_value(data, path):
        """Get nested value from dictionary using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @staticmethod
    def convert_array_annotations_to_dict(array_annotations):
        """Convert array-style annotations to dictionary format."""
        annotation_dict = {}
        for annotation in array_annotations:
            if isinstance(annotation, dict):
                for key, value in annotation.items():
                    annotation_dict[key] = str(value)
            elif isinstance(annotation, str) and ":" in annotation:
                key, value = annotation.split(":", 1)
                annotation_dict[key.strip()] = value.strip().strip('"')
        return annotation_dict

    def test_migration_completes_successfully(self, migration_results):
        """Test that migration completes without errors."""
        assert migration_results["success"], "Migration should complete successfully"

    def test_istio_sidecar_injection_preserved(self, migration_results):
        """Test that Istio sidecar injection annotations are preserved."""
        config = migration_results["config"]

        critical_paths = [
            "mgm.annotations",
            "ndb.annotations",
            "api.annotations",
            "api.ndbapp.annotations",
        ]

        injection_found = False
        for path in critical_paths:
            annotations = self.get_nested_value(config, path)
            if annotations:
                if isinstance(annotations, list):
                    annotations_dict = self.convert_array_annotations_to_dict(
                        annotations
                    )
                elif isinstance(annotations, dict):
                    annotations_dict = annotations
                else:
                    continue

                if "sidecar.istio.io/inject" in annotations_dict:
                    assert annotations_dict["sidecar.istio.io/inject"] == "true"
                    injection_found = True

        assert (
            injection_found
        ), "Istio sidecar injection should be preserved in at least one component"

    def test_istio_proxy_resources_preserved(self, migration_results):
        """Test that Istio proxy resource annotations are preserved."""
        config = migration_results["config"]

        critical_paths = [
            "mgm.annotations",
            "ndb.annotations",
            "api.annotations",
            "api.ndbapp.annotations",
        ]

        proxy_annotations = [
            "sidecar.istio.io/proxyCPU",
            "sidecar.istio.io/proxyCPULimit",
            "sidecar.istio.io/proxyMemory",
            "sidecar.istio.io/proxyMemoryLimit",
        ]

        found_proxy_configs = 0

        for path in critical_paths:
            annotations = self.get_nested_value(config, path)
            if annotations:
                if isinstance(annotations, list):
                    annotations_dict = self.convert_array_annotations_to_dict(
                        annotations
                    )
                elif isinstance(annotations, dict):
                    annotations_dict = annotations
                else:
                    continue

                for proxy_annotation in proxy_annotations:
                    if proxy_annotation in annotations_dict:
                        found_proxy_configs += 1
                        # Verify the values are reasonable
                        value = annotations_dict[proxy_annotation]
                        if "CPU" in proxy_annotation:
                            assert (
                                value == "2"
                            ), f"CPU annotation should be '2', got '{value}'"
                        elif "Memory" in proxy_annotation:
                            assert (
                                value == "2Gi"
                            ), f"Memory annotation should be '2Gi', got '{value}'"

        assert (
            found_proxy_configs >= 4
        ), f"Should find at least 4 proxy resource configs, found {found_proxy_configs}"

    def test_istio_proxy_config_preserved(self, migration_results):
        """Test that Istio proxy configuration is preserved."""
        config = migration_results["config"]

        critical_paths = [
            "mgm.annotations",
            "ndb.annotations",
            "api.annotations",
            "api.ndbapp.annotations",
        ]

        config_found = False
        for path in critical_paths:
            annotations = self.get_nested_value(config, path)
            if annotations:
                if isinstance(annotations, list):
                    annotations_dict = self.convert_array_annotations_to_dict(
                        annotations
                    )
                elif isinstance(annotations, dict):
                    annotations_dict = annotations
                else:
                    continue

                if "proxy.istio.io/config" in annotations_dict:
                    assert (
                        annotations_dict["proxy.istio.io/config"] == "{concurrency: 2}"
                    )
                    config_found = True

        assert (
            config_found
        ), "Istio proxy config should be preserved in at least one component"

    def test_f5_load_balancer_labels_preserved(self, migration_results):
        """Test that F5 load balancer labels are preserved."""
        config = migration_results["config"]

        # Check F5 labels in sqlgeorepsvclabels
        sqlgeorepsvclabels = self.get_nested_value(
            config, "api.externalService.sqlgeorepsvclabels"
        )

        assert sqlgeorepsvclabels is not None, "sqlgeorepsvclabels should exist"
        assert isinstance(
            sqlgeorepsvclabels, list
        ), "sqlgeorepsvclabels should be a list"

        f5_labels_found = 0
        f5_label_keys = [
            "cis.f5.com/as3-tenant",
            "cis.f5.com/as3-app",
            "cis.f5.com/as3-pool",
        ]

        for service_config in sqlgeorepsvclabels:
            if "labels" in service_config and isinstance(
                service_config["labels"], list
            ):
                labels_dict = self.convert_array_annotations_to_dict(
                    service_config["labels"]
                )
                for f5_label in f5_label_keys:
                    if f5_label in labels_dict:
                        f5_labels_found += 1
                        # Verify the label contains expected site identifier
                        assert "rcnltxekvzwcslf_y_or_x_004" in labels_dict[f5_label]

        assert (
            f5_labels_found >= 3
        ), f"Should find at least 3 F5 labels, found {f5_labels_found}"

    def test_oracle_cnf_annotations_preserved(self, migration_results):
        """Test that Oracle CNF annotations are preserved."""
        config = migration_results["config"]

        # Check Oracle CNF in db-replication-svc pod annotations
        dbreplsvc = self.get_nested_value(
            config, "db-replication-svc.dbreplsvcdeployments"
        )

        if dbreplsvc and isinstance(dbreplsvc, list):
            oracle_cnf_found = False
            for deployment in dbreplsvc:
                pod_annotations = deployment.get("podAnnotations", {})
                if "oracle.com/cnc" in pod_annotations:
                    assert pod_annotations["oracle.com/cnc"] == "true"
                    oracle_cnf_found = True

            assert (
                oracle_cnf_found
            ), "Oracle CNF annotation should be preserved in db-replication-svc"

    def test_metallb_annotations_preserved(self, migration_results):
        """Test that MetalLB annotations are preserved."""
        config = migration_results["config"]

        # Check MetalLB in db-replication-svc service annotations
        dbreplsvc = self.get_nested_value(
            config, "db-replication-svc.dbreplsvcdeployments"
        )

        if dbreplsvc and isinstance(dbreplsvc, list):
            metallb_found = False
            for deployment in dbreplsvc:
                service_annotations = deployment.get("service", {}).get(
                    "annotations", {}
                )
                if "metallb.universe.tf/address-pool" in service_annotations:
                    assert (
                        service_annotations["metallb.universe.tf/address-pool"] == "oam"
                    )
                    metallb_found = True

            assert (
                metallb_found
            ), "MetalLB annotation should be preserved in db-replication-svc"

    def test_network_preservation_summary_logged(self, migration_results):
        """Test that network preservation is logged in conflict log."""
        log_data = migration_results["log"]

        assert "conflicts" in log_data, "Log should contain conflicts array"

        network_entry_found = False
        for conflict in log_data["conflicts"]:
            if conflict["path"] == "__NETWORK_PRESERVATION_SUMMARY__":
                network_entry_found = True
                assert "network-critical configurations" in conflict["source_value"]
                assert "network categories" in conflict["target_value"].lower()
                break

        assert network_entry_found, "Network preservation summary should be logged"

    def test_network_categories_preserved(self, migration_results):
        """Test that all expected network categories are preserved."""
        log_data = migration_results["log"]

        # Find network preservation summary
        network_summary = None
        for conflict in log_data["conflicts"]:
            if conflict["path"] == "__NETWORK_PRESERVATION_SUMMARY__":
                network_summary = conflict
                break

        assert network_summary is not None, "Network preservation summary should exist"

        expected_categories = [
            "f5_integration",
            "service_discovery",
            "service_mesh",
            "load_balancer",
            "oracle_cnf",
        ]

        target_value = network_summary["target_value"].lower()

        for category in expected_categories:
            assert category.replace("_", "") in target_value.replace(
                "_", ""
            ), f"Category {category} should be preserved"

    def test_migration_statistics(self, migration_results):
        """Test migration statistics are reasonable."""
        log_data = migration_results["log"]

        assert "migration_summary" in log_data, "Log should contain migration summary"

        summary = log_data["migration_summary"]
        statistics = summary["statistics"]

        # Verify we have a reasonable number of overwrites (preserved custom values)
        assert (
            statistics["by_action_type"]["OVERWRITE"] >= 50
        ), "Should have substantial number of overwrites"

        # Verify we have network preservation activity
        assert (
            summary["total_entries"] >= 100
        ), "Should have processed substantial number of entries"

        # Verify some manual review items (expected for deleted/changed paths)
        assert (
            summary["manual_review_required"] > 0
        ), "Should have some items requiring manual review"

    def test_critical_service_labels_preserved(self, migration_results):
        """Test that critical service discovery labels are preserved."""
        config = migration_results["config"]

        # Check for app labels in services (these are critical for service discovery)
        service_paths = [
            "api.externalService.sqlgeorepsvclabels",
            "db-replication-svc.dbreplsvcdeployments",
        ]

        app_labels_found = 0

        for path in service_paths:
            data = self.get_nested_value(config, path)
            if data and isinstance(data, list):
                for item in data:
                    # Check service labels
                    if "service" in item and "labels" in item["service"]:
                        labels = item["service"]["labels"]
                        if isinstance(labels, dict) and "app" in labels:
                            assert labels["app"] == "occne_infra"
                            app_labels_found += 1
                    # Check direct labels
                    elif "labels" in item and isinstance(item["labels"], list):
                        labels_dict = self.convert_array_annotations_to_dict(
                            item["labels"]
                        )
                        if "app" in labels_dict:
                            assert labels_dict["app"] == "occne_infra"
                            app_labels_found += 1

        assert (
            app_labels_found >= 2
        ), f"Should find at least 2 service app labels, found {app_labels_found}"
