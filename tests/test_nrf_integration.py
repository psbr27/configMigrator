"""
Integration tests for NRF component detection and analysis.
Tests the enhanced CVPilot functionality with real Oracle Communications NRF files.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cvpilot.core.analyzer import ConflictAnalyzer, ComponentType, generate_rulebook_from_analysis
from cvpilot.core.parser import YAMLParser
from cvpilot.core.transformer import PathTransformationDetector
from cvpilot.core.merger import ConfigMerger


class TestNRFComponentDetection:
    """Test NRF component detection capabilities."""

    def test_filename_detection_nrf(self):
        """Test component detection from NRF filenames."""
        test_cases = [
            ("ocnrf_custom_values_25.1.200.yaml", ComponentType.NRF),
            ("rcnltxekvzwcnrf-y-or-x-102-ocnrf_24.2.4.yaml", ComponentType.NRF),
            ("nrf_values.yaml", ComponentType.NRF),
            ("occndbtier_custom_values_25.1.102.yaml", ComponentType.CNDBTIER),
            ("random_file.yaml", ComponentType.UNKNOWN),
        ]

        for filename, expected in test_cases:
            result = ComponentType.detect_from_filename(filename)
            assert result == expected, f"Failed for {filename}: expected {expected.value}, got {result.value}"

    def test_content_detection_nrf(self):
        """Test component detection from NRF YAML content."""
        # NRF content with nrfTag
        nrf_content = {
            'global': {
                'nrfTag': '25.1.200',
                'gwTag': '25.1.203'
            }
        }
        assert ComponentType.detect_from_content(nrf_content) == ComponentType.NRF

        # NRF content with microservices
        nrf_microservices_content = {
            'nfregistration': {'enabled': True},
            'nfdiscovery': {'enabled': True}
        }
        assert ComponentType.detect_from_content(nrf_microservices_content) == ComponentType.NRF

        # NRF content with gateways
        nrf_gateway_content = {
            'ingress-gateway': {'enabled': True},
            'egress-gateway': {'enabled': True}
        }
        assert ComponentType.detect_from_content(nrf_gateway_content) == ComponentType.NRF

        # CNDBTIER content
        cndbtier_content = {
            'mysql-service': {'enabled': True},
            'mysql': {'host': 'localhost'}
        }
        assert ComponentType.detect_from_content(cndbtier_content) == ComponentType.CNDBTIER

        # Unknown content
        unknown_content = {
            'random': {'key': 'value'}
        }
        assert ComponentType.detect_from_content(unknown_content) == ComponentType.UNKNOWN


class TestNRFConflictAnalysis:
    """Test NRF-specific conflict analysis."""

    @pytest.fixture
    def nrf_analyzer(self):
        """Create an analyzer instance for NRF testing."""
        analyzer = ConflictAnalyzer()
        analyzer.detected_component = ComponentType.NRF
        analyzer.list_field_names = analyzer.COMPONENT_FIELDS[ComponentType.NRF]
        return analyzer

    def test_nrf_field_detection(self, nrf_analyzer):
        """Test that NRF-specific fields are properly detected."""
        nrf_data = {
            'global': {
                'nrfTag': '25.1.200',
                'deprecatedList': 'nfSetIdList_CaseCheck, sendAcceptEncodeHeaderGzip',
                'mysql': {
                    'primary': {'host': 'mysql-primary'},
                    'secondary': {'host': 'mysql-secondary'}
                }
            },
            'nfregistration': {
                'commonlabels': {'app': 'nrf-registration'},
                'annotations': {'version': '25.1.200'}
            }
        }

        fields = nrf_analyzer._find_all_list_fields(nrf_data)

        # Should find NRF-specific fields
        expected_fields = [
            'global.mysql',
            'nfregistration.commonlabels',
            'nfregistration.annotations'
        ]

        for field in expected_fields:
            assert field in fields, f"Missing expected field: {field}"

    def test_nrf_specific_patterns(self, nrf_analyzer):
        """Test NRF-specific site pattern detection."""
        nrf_items = [
            {'customer.oracle.com/nrf-instance': 'prod-nrf-01'},
            {'nrf.customer.com/region': 'us-west-1'}
        ]

        score = nrf_analyzer._calculate_site_specific_score(nrf_items)
        assert score > 0.5, "Should detect NRF-specific site patterns"


class TestNRFRulebookGeneration:
    """Test NRF-specific rulebook generation."""

    def test_nrf_rulebook_generation(self):
        """Test generation of NRF-specific merge rules."""
        analysis = {
            'component_type': 'ocnrf',
            'conflicts': [],
            'suggestions': {},
            'summary': {'total_conflicts': 0}
        }

        rulebook = generate_rulebook_from_analysis(analysis)

        # Check NRF-specific rules are present
        assert 'nrfTag' in rulebook['merge_rules']
        assert 'gwTag' in rulebook['merge_rules']
        assert 'deprecatedList' in rulebook['merge_rules']
        assert 'mysql' in rulebook['merge_rules']

        # Check strategies are appropriate
        assert rulebook['merge_rules']['nrfTag']['strategy'] == 'engnew'
        assert rulebook['merge_rules']['deprecatedList']['strategy'] == 'nsprev'
        assert rulebook['merge_rules']['mysql']['strategy'] == 'nsprev'

        # Check path overrides
        assert 'global.nrfTag' in rulebook['path_overrides']
        assert 'global.mysql.primary' in rulebook['path_overrides']

    def test_cndbtier_rulebook_generation(self):
        """Test CNDBTIER-specific rulebook generation."""
        analysis = {
            'component_type': 'occndbtier',
            'conflicts': [],
            'suggestions': {},
            'summary': {'total_conflicts': 0}
        }

        rulebook = generate_rulebook_from_analysis(analysis)

        # Check CNDBTIER-specific rules
        assert 'mysql' in rulebook['merge_rules']
        assert 'database' in rulebook['merge_rules']
        assert rulebook['merge_rules']['mysql']['strategy'] == 'nsprev'


class TestNRFPathTransformation:
    """Test path transformation detection with NRF configurations."""

    def test_nrf_version_duplication_detection(self):
        """Test detection of version tag duplications across microservices."""
        # Simulate merged config with version duplications
        merged_config = {
            'global': {
                'nrfTag': '25.1.200'
            },
            'nfregistration': {
                'nrfTag': '25.1.200'  # Duplicate
            },
            'nfdiscovery': {
                'nrfTag': '25.1.200'  # Duplicate
            }
        }

        # Reference shows version should only be in global
        reference_config = {
            'global': {
                'nrfTag': '25.1.200'
            },
            'nfregistration': {
                'enabled': True
            },
            'nfdiscovery': {
                'enabled': True
            }
        }

        detector = PathTransformationDetector()
        transformations = detector.detect_duplicate_values(merged_config, reference_config)

        # Should detect transformations for microservice-level duplicates
        assert len(transformations) > 0

        # Check that we found the right transformations
        paths = [t.old_path for t in transformations]
        assert any('nfregistration.nrfTag' in path for path in paths)
        assert any('nfdiscovery.nrfTag' in path for path in paths)

    def test_nrf_mysql_config_transformation(self):
        """Test MySQL configuration transformation detection."""
        merged_config = {
            'global': {
                'mysql': {
                    'primary': {'host': 'mysql-primary'},
                    'secondary': {'host': 'mysql-secondary'}
                }
            },
            'database': {
                'mysql': {
                    'primary': {'host': 'mysql-primary'}  # Duplicate structure
                }
            }
        }

        reference_config = {
            'global': {
                'mysql': {
                    'primary': {'host': 'mysql-primary'},
                    'secondary': {'host': 'mysql-secondary'}
                }
            }
        }

        detector = PathTransformationDetector()
        transformations = detector.detect_duplicate_values(merged_config, reference_config)

        # Should detect transformation for database.mysql structure
        mysql_transformations = [t for t in transformations if 'mysql' in t.old_path.lower()]
        assert len(mysql_transformations) > 0


class TestNRFPerformance:
    """Test performance with large NRF configurations."""

    def test_large_nrf_file_performance(self):
        """Test that CVPilot handles large NRF files efficiently."""
        # Create a large simulated NRF config
        large_config = {
            'global': {
                'nrfTag': '25.1.200',
                'gwTag': '25.1.203'
            }
        }

        # Add many microservices
        microservices = [
            'nfregistration', 'nfsubscription', 'nfdiscovery',
            'nfaccesstoken', 'nrfconfiguration', 'nrfauditor'
        ]

        for service in microservices:
            large_config[service] = {
                'commonlabels': {f'app': f'nrf-{service}'},
                'annotations': {f'version': '25.1.200'},
                'podAnnotations': {f'service': service},
                'configuration': {f'key_{i}': f'value_{i}' for i in range(50)}
            }

        # Test component detection performance
        import time
        start_time = time.time()
        component = ComponentType.detect_from_content(large_config)
        detection_time = time.time() - start_time

        assert component == ComponentType.NRF
        assert detection_time < 0.1, f"Component detection too slow: {detection_time:.3f}s"

        # Test path mapping performance
        detector = PathTransformationDetector()
        start_time = time.time()
        detector._build_path_value_map(large_config, "")
        mapping_time = time.time() - start_time

        assert len(detector.path_value_map) > 100, "Should map many paths"
        assert mapping_time < 0.5, f"Path mapping too slow: {mapping_time:.3f}s"


class TestNRFRealFileIntegration:
    """Integration tests with real NRF files (if available)."""

    @pytest.fixture
    def nrf_files(self):
        """Return paths to real NRF files if they exist."""
        potential_files = [
            "nrf_yaml_files/ocnrf_custom_values_24.2.4.yaml",
            "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml"
        ]

        existing_files = [f for f in potential_files if Path(f).exists()]
        return existing_files

    @pytest.mark.skipif(
        not Path("nrf_yaml_files/ocnrf_custom_values_24.2.4.yaml").exists(),
        reason="Real NRF files not available"
    )
    def test_real_nrf_file_analysis(self, nrf_files):
        """Test analysis with real NRF files."""
        if len(nrf_files) < 2:
            pytest.skip("Need at least 2 NRF files for comparison")

        nsprev_path = nrf_files[0]
        engnew_path = nrf_files[1]

        analyzer = ConflictAnalyzer()
        analysis = analyzer.analyze_files(nsprev_path, engnew_path)

        # Should detect NRF component
        assert analysis['component_type'] == 'ocnrf'

        # Should find some conflicts (version differences)
        assert analysis['summary']['total_conflicts'] >= 0

        # Generate rulebook
        rulebook = generate_rulebook_from_analysis(analysis)
        assert 'nrfTag' in rulebook['merge_rules']

    @pytest.mark.skipif(
        not Path("nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml").exists(),
        reason="Real NRF file not available"
    )
    def test_real_nrf_file_structure_validation(self):
        """Validate the structure of real NRF files."""
        file_path = "nrf_yaml_files/ocnrf_custom_values_25.1.200.yaml"

        parser = YAMLParser()
        data = parser.load_yaml_file(file_path)

        # Validate expected NRF structure
        assert 'global' in data
        global_section = data['global']

        # Should have version tags
        assert 'nrfTag' in global_section
        assert 'gwTag' in global_section

        # Should have NRF-specific configuration
        expected_nrf_fields = ['deprecatedList', 'mysql', 'appValidate']
        found_fields = [field for field in expected_nrf_fields if field in global_section]
        assert len(found_fields) > 0, f"Missing NRF fields: {expected_nrf_fields}"


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])