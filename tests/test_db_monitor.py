#!/usr/bin/env python3
"""Test db-monitor-svc annotation preservation specifically."""

import sys
import yaml
sys.path.insert(0, 'src')

from network_preservation import NetworkPreservationEngine

def main():
    # Load the original golden config
    with open('rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml', 'r') as f:
        golden_old = yaml.safe_load(f)

    # Load the new template
    with open('occndbtier_custom_values_25.1.200.yaml', 'r') as f:
        template_new = yaml.safe_load(f)

    # Load the previous migration result
    with open('network_safe_occndbtier_25.1.200_v2.yaml', 'r') as f:
        merged_result = yaml.safe_load(f)

    # Create network preservation engine
    engine = NetworkPreservationEngine()

    # Check db-monitor-svc annotations specifically
    path = 'db-monitor-svc.podAnnotations'
    original_annotations = engine._get_nested_value(golden_old, path)
    current_annotations = engine._get_nested_value(merged_result, path)

    print(f"=== {path} ===")
    print(f"Original annotations: {original_annotations}")
    print(f"Current annotations: {current_annotations}")

    # Apply the enhanced fix
    engine._fix_array_annotations(golden_old, merged_result)

    # Check the result
    enhanced_annotations = engine._get_nested_value(merged_result, path)
    print(f"Enhanced annotations: {enhanced_annotations}")

    # Check if critical Istio annotations are now preserved
    if enhanced_annotations and isinstance(enhanced_annotations, dict):
        critical_annotations = [
            "sidecar.istio.io/inject",
            "sidecar.istio.io/proxyCPU",
            "sidecar.istio.io/proxyCPULimit",
            "sidecar.istio.io/proxyMemory",
            "sidecar.istio.io/proxyMemoryLimit",
            "proxy.istio.io/config",
            "oracle.com/cnc"
        ]

        for annotation in critical_annotations:
            if annotation in enhanced_annotations:
                print(f"✅ {annotation}: {enhanced_annotations[annotation]}")
            else:
                print(f"❌ MISSING: {annotation}")

    # Save the enhanced configuration
    with open('network_safe_occndbtier_25.1.200_v3.yaml', 'w') as f:
        yaml.dump(merged_result, f, default_flow_style=False, allow_unicode=True)

    print(f"\n✅ Enhanced configuration saved to network_safe_occndbtier_25.1.200_v3.yaml")

if __name__ == "__main__":
    main()