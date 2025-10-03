"""
Tests for configuration merger functionality.
"""

from config_migrator.core.merger import ConfigMerger


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

    def test_merge_configs_nstf_precedence(self):
        """Test merge with NSTF precedence rules."""
        # ETF (base template)
        etf = {
            "global": {
                "sitename": "cndbtiersitename",
                "version": "25.1.102",
                "namespace": "occne-cndbtier",
            },
            "api": {
                "replicas": 2,
            },
        }

        # NEWTF (new features)
        _newtf = {
            "global": {
                "version": "25.1.200",
                "new_feature": "enabled",
            },
            "new_section": {
                "new_key": "new_value",
            },
        }

        # NSTF (site-specific, highest precedence)
        nstf = {
            "global": {
                "sitename": "rcnltxekvzwcslf-y-or-x-004",
                "namespace": "rcnltxekvzwcslf-y-or-x-004",
            },
            "api": {
                "replicas": 4,
            },
        }

        result = ConfigMerger.merge_configs_stage1(nstf, etf)

        # NSTF should override ETF values
        assert result["global"]["sitename"] == "rcnltxekvzwcslf-y-or-x-004"
        assert result["global"]["namespace"] == "rcnltxekvzwcslf-y-or-x-004"
        assert result["api"]["replicas"] == 4

        # ETF base values should be preserved where not overridden
        assert result["global"]["version"] == "25.1.102"  # From ETF

        # ETF base values should be preserved where not overridden
        assert (
            "cndbtiersitename" not in result["global"]["sitename"]
        )  # Overridden by NSTF

    def test_merge_configs_list_handling(self):
        """Test merge with list handling."""
        etf = {
            "services": ["service1", "service2"],
            "config": {
                "items": ["item1", "item2"],
            },
        }

        _newtf = {
            "services": ["service3", "service4"],  # Should replace ETF list
            "config": {
                "items": ["item3", "item4"],  # Should replace ETF list
            },
        }

        nstf = {
            "services": ["service5", "service6"],  # Should override NEWTF list
            "config": {
                "items": ["item5", "item6"],  # Should override NEWTF list
            },
        }

        result = ConfigMerger.merge_configs_stage1(nstf, etf)

        # NSTF should have final precedence for lists
        assert result["services"] == ["service5", "service6"]
        assert result["config"]["items"] == ["item5", "item6"]

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
        """Test merge summary generation."""
        etf = {
            "global": {"sitename": "template", "version": "25.1.102"},
            "api": {"replicas": 2},
        }

        _newtf = {
            "global": {"version": "25.1.200", "new_feature": "enabled"},
            "new_section": {"key": "value"},
        }

        nstf = {
            "global": {"sitename": "site-specific"},
            "api": {"replicas": 4},
        }

        summary = ConfigMerger.get_merge_summary(nstf, etf, _newtf)

        assert "etf_keys" in summary
        assert "newtf_additions" in summary
        assert "nstf_overrides" in summary
        assert summary["etf_keys"] > 0
        assert summary["newtf_additions"] > 0
        assert summary["nstf_overrides"] > 0
