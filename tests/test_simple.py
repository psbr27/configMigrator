#!/usr/bin/env python3
"""Simple test of the annotation preservation fix."""

import sys

import yaml

sys.path.insert(0, "src")

from network_preservation import NetworkPreservationEngine


def main():
    # Load the original golden config
    with open("rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml") as f:
        golden_old = yaml.safe_load(f)

    # Load the new template
    with open("occndbtier_custom_values_25.1.200.yaml") as f:
        template_new = yaml.safe_load(f)

    # Load the previous migration result
    with open("network_safe_occndbtier_25.1.200.yaml") as f:
        merged_result = yaml.safe_load(f)

    # Create network preservation engine
    engine = NetworkPreservationEngine()

    # Apply enhanced preservation
    enhanced_config = engine.preserve_network_config(
        golden_old, template_new, merged_result
    )

    # Check specific annotation paths that were missing
    check_paths = [
        "mgm.annotations",
        "ndb.annotations",
        "api.annotations",
        "api.ndbapp.annotations",
    ]

    for path in check_paths:
        result_annotations = engine._get_nested_value(enhanced_config, path)
        original_annotations = engine._get_nested_value(golden_old, path)

        print(f"\n=== {path} ===")
        print(f"Original annotations: {original_annotations}")
        print(f"Enhanced annotations: {result_annotations}")

        # Check if critical Istio annotations are preserved
        if result_annotations and isinstance(result_annotations, list):
            enhanced_dict = engine._convert_array_annotations_to_dict(
                result_annotations
            )
            print(f"Enhanced as dict: {enhanced_dict}")

            critical_annotations = [
                "sidecar.istio.io/proxyCPU",
                "sidecar.istio.io/proxyCPULimit",
                "sidecar.istio.io/proxyMemory",
                "sidecar.istio.io/proxyMemoryLimit",
                "proxy.istio.io/config",
            ]

            for annotation in critical_annotations:
                if annotation in enhanced_dict:
                    print(f"✅ {annotation}: {enhanced_dict[annotation]}")
                else:
                    print(f"❌ MISSING: {annotation}")

    # Save the enhanced configuration
    with open("network_safe_occndbtier_25.1.200_v2.yaml", "w") as f:
        yaml.dump(enhanced_config, f, default_flow_style=False, allow_unicode=True)

    print(
        "\n✅ Enhanced configuration saved to network_safe_occndbtier_25.1.200_v2.yaml"
    )


if __name__ == "__main__":
    main()
