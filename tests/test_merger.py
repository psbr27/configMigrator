"""
Tests for configuration merger functionality.
"""

from cvpilot.core.merger import ConfigMerger


class TestConfigMerger:
    """Test cases for ConfigMerger."""

    def test_deep_merge_simple(self):
        """Test simple deep merge."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "new_value2", "key3": "value3"}

        result = ConfigMerger.deep_merge(base, override)

        expected = {"key1": "value1", "key2": "new_value2", "key3": "value3"}
        assert result == expected

    def test_deep_merge_nested(self):
        """Test deep merge with nested dictionaries."""
        base = {
            "global": {
                "sitename": "template",
                "version": "25.1.102",
            },
            "api": {
                "replicas": 2,
            },
        }
        override = {
            "global": {
                "sitename": "site-specific",
                "namespace": "custom-namespace",
            },
            "api": {
                "replicas": 4,
            },
            "new_section": {
                "new_key": "new_value",
            },
        }

        result = ConfigMerger.deep_merge(base, override)

        expected = {
            "global": {
                "sitename": "site-specific",
                "version": "25.1.102",
                "namespace": "custom-namespace",
            },
            "api": {
                "replicas": 4,
            },
            "new_section": {
                "new_key": "new_value",
            },
        }
        assert result == expected

    def test_merge_configs_stage1_difference_extraction(self):
        """Test Stage 1 - difference extraction between NSPREV and ENGPREV."""
        # ENGPREV (base template)
        engprev = {
            "global": {
                "sitename": "cndbtiersitename",
                "version": "25.1.102",
                "namespace": "occne-cndbtier",
            },
            "api": {
                "replicas": 2,
                "timeout": 30,
            },
            "unchanged_section": {
                "key": "value",
            },
        }

        # NSPREV (site-specific, with differences)
        nsprev = {
            "global": {
                "sitename": "rcnltxekvzwcslf-y-or-x-004",  # Modified
                "version": "25.1.102",  # Same as ENGPREV
                "namespace": "rcnltxekvzwcslf-y-or-x-004",  # Modified
            },
            "api": {
                "replicas": 4,  # Modified
                "timeout": 30,  # Same as ENGPREV
            },
            "unchanged_section": {
                "key": "value",  # Same as ENGPREV
            },
            "new_section": {  # Added in NSPREV
                "new_key": "new_value",
            },
        }

        result = ConfigMerger.merge_configs_stage1(nsprev, engprev)

        # Should only contain differences
        assert "global" in result
        assert result["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"  # Modified
        assert result["global"]["namespace"] == "rcnltxekvzwcslf-y-or-x-004"  # Modified
        assert (
            "version" not in result["global"]
        )  # Same as ENGPREV, should not be included

        assert "api" in result
        assert result["api"]["replicas"] == 4  # Modified
        assert "timeout" not in result["api"]  # Same as ENGPREV, should not be included

        assert (
            "unchanged_section" not in result
        )  # Identical to ENGPREV, should not be included

        assert "new_section" in result  # Added in NSPREV
        assert result["new_section"]["new_key"] == "new_value"

    def test_merge_configs_stage2_precedence_order(self):
        """Test Stage 2 - precedence order: NSPREV > ENGNEW (for matching keys only)."""
        # ENGNEW (new template, foundation structure)
        engnew = {
            "global": {
                "sitename": "cndbtiersitename",
                "version": "25.1.200",
                "feature_new": "enabled",
            },
            "api": {
                "replicas": 2,
                "timeout": 60,
            },
            "new_component": {
                "enabled": True,
            },
        }

        # Diff file (NSPREV differences from Stage 1, highest precedence for matching keys)
        diff_file = {
            "global": {
                "sitename": "rcnltxekvzwcslf-y-or-x-004",  # Override ENGNEW
                "namespace": "rcnltxekvzwcslf-y-or-x-004",  # Not in ENGNEW, should be ignored
            },
            "api": {
                "replicas": 4,  # Override ENGNEW
            },
            "old_component": {  # Not in ENGNEW, should be ignored
                "enabled": False,
            },
        }

        result = ConfigMerger.merge_configs_stage2(diff_file, engnew)

        # Test final precedence order
        # NSPREV (diff_file) should override ENGNEW for matching keys
        assert (
            result["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
        )  # From NSPREV (overrides ENGNEW)
        assert result["api"]["replicas"] == 4  # From NSPREV (overrides ENGNEW)

        # ENGNEW values should be preserved where not overridden by NSPREV
        assert result["global"]["version"] == "25.1.200"  # From ENGNEW
        assert result["global"]["feature_new"] == "enabled"  # From ENGNEW
        assert result["api"]["timeout"] == 60  # From ENGNEW
        assert result["new_component"]["enabled"]  # From ENGNEW

        # DIFF keys not in ENGNEW should be ignored
        assert "namespace" not in result["global"]  # Not in ENGNEW, ignored
        assert "old_component" not in result  # Not in ENGNEW, ignored

    def test_merge_configs_stage2_selective_overlay(self):
        """Test Stage 2 selective overlay - only matching keys are updated."""
        engnew = {
            "global": {"version": "25.1.200", "sitename": "template"},
            "api": {"replicas": 2},
        }

        diff_file = {
            "global": {"sitename": "site-specific"},
            "api": {"replicas": 4},
            "ignored_section": {"key": "value"},  # Not in ENGNEW, should be ignored
        }

        result = ConfigMerger.merge_configs_stage2(diff_file, engnew)

        # ENGNEW values should be preserved where not overridden
        assert result["global"]["version"] == "25.1.200"  # From ENGNEW
        # NSPREV should override ENGNEW for matching keys
        assert result["global"]["sitename"] == "site-specific"  # From diff_file
        assert result["api"]["replicas"] == 4  # From diff_file (overrides ENGNEW)
        # DIFF keys not in ENGNEW should be ignored
        assert "ignored_section" not in result

    def test_merge_configs_list_handling_stage1(self):
        """Test Stage 1 difference extraction with list handling."""
        engprev = {
            "services": ["service1", "service2"],
            "config": {
                "items": ["item1", "item2"],
            },
        }

        nsprev = {
            "services": ["service3", "service4"],  # Different from ENGPREV
            "config": {
                "items": ["item1", "item2"],  # Same as ENGPREV
            },
        }

        result = ConfigMerger.merge_configs_stage1(nsprev, engprev)

        # Should only include differences (services changed, items unchanged)
        assert "services" in result
        assert result["services"] == ["service3", "service4"]
        assert "config" not in result  # items are same, so config section not included

    def test_merge_configs_list_handling_stage2(self):
        """Test Stage 2 list handling with precedence."""
        engnew = {
            "services": ["service3", "service4"],  # ENGNEW foundation
        }

        diff_file = {
            "services": [
                "service5",
                "service6",
            ],  # NSPREV override (highest precedence for matching keys)
        }

        result = ConfigMerger.merge_configs_stage2(diff_file, engnew)

        # NSPREV (diff_file) should override ENGNEW for matching keys
        assert result["services"] == ["service5", "service6"]

    def test_compare_configs(self):
        """Test configuration comparison."""
        config1 = {
            "global": {
                "sitename": "template",
                "version": "25.1.102",
            },
            "api": {
                "replicas": 2,
            },
        }

        config2 = {
            "global": {
                "sitename": "site-specific",
                "version": "25.1.102",
                "namespace": "custom",
            },
            "api": {
                "replicas": 4,
            },
            "new_section": {
                "new_key": "new_value",
            },
        }

        differences = ConfigMerger.compare_configs(config1, config2)

        # Should find differences
        assert "global" in differences
        assert differences["global"]["sitename"] == "site-specific"
        assert differences["global"]["namespace"] == "custom"
        assert differences["api"]["replicas"] == 4
        assert "new_section" in differences

    def test_get_merge_summary(self):
        """Test merge summary generation with new naming."""
        engprev = {
            "global": {"sitename": "template", "version": "25.1.102"},
            "api": {"replicas": 2},
        }

        engnew = {
            "global": {"version": "25.1.200", "new_feature": "enabled"},
            "new_section": {"key": "value"},
        }

        nsprev = {
            "global": {"sitename": "site-specific"},
            "api": {"replicas": 4},
        }

        summary = ConfigMerger.get_merge_summary(nsprev, engprev, engnew)

        assert "engprev_keys" in summary
        assert "engnew_additions" in summary
        assert "nsprev_overrides" in summary
        assert summary["engprev_keys"] > 0
        assert summary["engnew_additions"] > 0
        assert summary["nsprev_overrides"] > 0

    def test_get_differences_method(self):
        """Test _get_differences method directly."""
        base = {
            "global": {
                "sitename": "template",
                "version": "25.1.102",
            },
            "api": {"replicas": 2},
        }

        source = {
            "global": {
                "sitename": "site-specific",  # Modified
                "version": "25.1.102",  # Same
                "namespace": "custom",  # Added
            },
            "api": {"replicas": 4},  # Modified
            "new_section": {"key": "value"},  # Added
        }

        differences = ConfigMerger._get_differences(source, base)

        # Should only contain differences
        assert "global" in differences
        assert differences["global"]["sitename"] == "site-specific"
        assert differences["global"]["namespace"] == "custom"
        assert "version" not in differences["global"]  # Same value

        assert "api" in differences
        assert differences["api"]["replicas"] == 4

        assert "new_section" in differences
        assert differences["new_section"]["key"] == "value"
