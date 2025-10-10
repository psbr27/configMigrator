#!/bin/bash

# CVPilot Usage Guide
# Shows different ways to use CVPilot with examples

echo "🔧 CVPilot Usage Guide"
echo "======================"

echo -e "\n📋 Available Commands:"
echo "1. python -m cvpilot --help                    # Show main help"
echo "2. python -m cvpilot migrate --help           # Show migrate help"
echo "3. python -m cvpilot generate-rules --help    # Show generate-rules help"

echo -e "\n🚀 Basic Usage Patterns:"

echo -e "\n1️⃣ Traditional Migration (Stage 1 + Stage 2):"
echo "python -m cvpilot migrate <nsprev> <engprev> <engnew> [options]"
echo "Example:"
echo "python -m cvpilot migrate \\"
echo "  rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml \\"
echo "  nsprev_25.1.200.yaml \\"
echo "  occndbtier_custom_values_25.1.200.yaml \\"
echo "  --output merged.yaml --summary"

echo -e "\n2️⃣ Generate Merge Rules (Dynamic Analysis):"
echo "python -m cvpilot generate-rules <nsprev> <engnew> [options]"
echo "Example:"
echo "python -m cvpilot generate-rules \\"
echo "  rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml \\"
echo "  occndbtier_custom_values_25.1.200.yaml \\"
echo "  --output merge_rules.yaml --verbose"

echo -e "\n3️⃣ Rulebook-Based Migration:"
echo "python -m cvpilot migrate <nsprev> <engprev> <engnew> --rules <rulebook> [options]"
echo "Example:"
echo "python -m cvpilot migrate \\"
echo "  rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml \\"
echo "  nsprev_25.1.200.yaml \\"
echo "  occndbtier_custom_values_25.1.200.yaml \\"
echo "  --rules merge_rules.yaml \\"
echo "  --output merged.yaml --summary"

echo -e "\n🔧 Common Options:"
echo "  --output FILE     Output file name"
echo "  --rules FILE      Path to merge rules YAML file"
echo "  --verbose         Verbose output"
echo "  --debug           Debug output"
echo "  --summary         Show merge summary"

echo -e "\n📝 Rulebook Configuration:"
echo "The rulebook YAML file supports:"
echo "  • default_strategy: engnew | nsprev | merge"
echo "  • merge_rules: Global rules for field types"
echo "  • path_overrides: Specific path overrides"
echo ""
echo "Example rulebook:"
cat << 'EOF'
default_strategy: engnew
merge_rules:
  annotations:
    strategy: merge
    scope: global
  commonlabels:
    strategy: nsprev
    scope: global
path_overrides:
  "mgm.annotations":
    strategy: nsprev
EOF

echo -e "\n🎯 Use Cases:"
echo "• Traditional: Use when you want standard Stage 1 + Stage 2 workflow"
echo "• Generate Rules: Use to analyze conflicts and get intelligent suggestions"
echo "• Rulebook Migration: Use when you want fine-grained control over merge strategies"

echo -e "\n🧪 Testing Scripts:"
echo "• ./quick_test.sh     - Quick functionality test"
echo "• ./run_cvpilot_modes.sh - Comprehensive testing of all modes"

echo -e "\n📚 For more information, run:"
echo "python -m cvpilot --help"
