import sys
import json
import argparse
from pathlib import Path
from ruamel.yaml import YAML
from prettytable import PrettyTable

# --- File Definitions (Based on CVPilot Example 1) ---
FILE_102 = "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml"
FILE_200 = "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.200.yaml"
MERGE_RULES_FILE = "merge_rules.yaml"

def get_nested_value(data_dict, dot_key):
    """
    Traverses a dictionary using dot-notation keys with array indexing support.
    Supports both dict keys and array indices (e.g., 'global.items[0].name').
    Returns the found value or None if any key in the path is missing.
    """
    import re

    keys = dot_key.split('.')
    temp_data = data_dict

    for key in keys:
        # Check if this key contains array indexing (e.g., 'items[0]')
        array_match = re.match(r'^([^[]+)\[(\d+)\]$', key)

        if array_match:
            # Handle array indexing
            array_key = array_match.group(1)
            array_index = int(array_match.group(2))

            # First access the array key
            if isinstance(temp_data, dict) and array_key in temp_data:
                temp_data = temp_data[array_key]
            else:
                return None

            # Then access the array index
            if isinstance(temp_data, list) and 0 <= array_index < len(temp_data):
                temp_data = temp_data[array_index]
            else:
                return None
        else:
            # Handle regular dict key access
            if isinstance(temp_data, dict) and key in temp_data:
                temp_data = temp_data[key]
            else:
                return None

    return temp_data

def extract_value_from_file(filepath, dot_key):
    """
    Extract a value from a YAML file using dot notation.

    Args:
        filepath: Path to the YAML file
        dot_key: Dot notation key to extract

    Returns:
        Formatted string representation of the value
    """
    yaml = YAML()
    try:
        with open(filepath, 'r') as f:
            data = yaml.load(f)
            value = get_nested_value(data, dot_key)

            if value is None:
                return "N/A (Key not found)"

            # Use json.dumps to compact the value into a single line string.
            # Use indent=2 here to make the wrapped content slightly more readable,
            # though it will still be treated as a single string for wrapping.
            return json.dumps(value, indent=2)

    except FileNotFoundError:
        return f"ERROR: File not found ({filepath})"
    except Exception as e:
        return f"ERROR: YAML parsing failed ({str(e)})"

def load_merge_rules():
    """
    Load and parse the merge_rules.yaml file.

    Returns:
        Dictionary containing all the keys from merge_rules and path_overrides
    """
    yaml = YAML()
    try:
        with open(MERGE_RULES_FILE, 'r') as f:
            rules_data = yaml.load(f)

        keys_with_strategies = {}

        # Extract keys from merge_rules
        merge_rules = rules_data.get('merge_rules', {})
        for key, config in merge_rules.items():
            strategy = config.get('strategy', 'unknown')
            scope = config.get('scope', 'unknown')
            keys_with_strategies[key] = {'strategy': strategy, 'scope': scope, 'source': 'merge_rules'}

        # Extract keys from path_overrides
        path_overrides = rules_data.get('path_overrides', {})
        for key, config in path_overrides.items():
            strategy = config.get('strategy', 'unknown')
            keys_with_strategies[key] = {'strategy': strategy, 'scope': 'path_override', 'source': 'path_overrides'}

        return keys_with_strategies

    except FileNotFoundError:
        print(f"ERROR: {MERGE_RULES_FILE} not found")
        return {}
    except Exception as e:
        print(f"ERROR: Failed to parse {MERGE_RULES_FILE}: {e}")
        return {}

def compare_all_rules():
    """
    Compare all keys mentioned in merge_rules.yaml between the two files.
    """
    print(f"Comparing all keys from {MERGE_RULES_FILE}")
    print("=" * 80)

    # Load merge rules
    rules = load_merge_rules()

    if not rules:
        print("No rules found or failed to load merge rules.")
        return

    # Create main comparison table
    table = PrettyTable()
    table.field_names = ["Key Path", "Strategy", "Source", "Pre-Migration (102)", "Post-Migration (200)", "Status"]

    # Set column widths
    table.max_width["Key Path"] = 35
    table.max_width["Strategy"] = 10
    table.max_width["Source"] = 12
    table.max_width["Pre-Migration (102)"] = 25
    table.max_width["Post-Migration (200)"] = 25
    table.max_width["Status"] = 10

    table.align = "l"

    # Process each key
    total_keys = len(rules)
    different_count = 0
    same_count = 0
    error_count = 0

    for key, rule_info in sorted(rules.items()):
        strategy = rule_info['strategy']
        source = rule_info['source']

        # Extract values from both files
        value_102 = extract_value_from_file(FILE_102, key)
        value_200 = extract_value_from_file(FILE_200, key)

        # Determine status
        if "ERROR" in value_102 or "ERROR" in value_200:
            status = "ERROR"
            error_count += 1
        elif value_102 == value_200:
            status = "SAME"
            same_count += 1
        else:
            status = "DIFFERENT"
            different_count += 1

        # Truncate long values for better display
        display_102 = (value_102[:22] + "...") if len(value_102) > 25 else value_102
        display_200 = (value_200[:22] + "...") if len(value_200) > 25 else value_200

        table.add_row([key, strategy, source, display_102, display_200, status])

    print(table)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"Total keys compared: {total_keys}")
    print(f"Same values: {same_count}")
    print(f"Different values: {different_count}")
    print(f"Errors: {error_count}")

    # Show details for different values
    if different_count > 0:
        print(f"\n--- DETAILED DIFFERENCES ---")
        for key, rule_info in sorted(rules.items()):
            value_102 = extract_value_from_file(FILE_102, key)
            value_200 = extract_value_from_file(FILE_200, key)

            if "ERROR" not in value_102 and "ERROR" not in value_200 and value_102 != value_200:
                print(f"\nKey: {key} (Strategy: {rule_info['strategy']})")
                print(f"  Pre-Migration (102):  {value_102}")
                print(f"  Post-Migration (200): {value_200}")

def query_yaml_and_compare(dot_key):
    """
    Loads both YAML files, extracts the value for the given dot_key,
    and prints the results in a formatted, readable table.
    """
    print(f"Querying key: {dot_key}")
    print("--------------------------------------------------------")

    # Fetch values
    value_102 = extract_value_from_file(FILE_102, dot_key)
    value_200 = extract_value_from_file(FILE_200, dot_key)

    # --- Format and Display Table ---

    table = PrettyTable()

    # Define table headers
    table.field_names = ["Key Path", "Pre-Migration (102)", "Post-Migration (200)"]

    # *** CRITICAL FIX: Set max_width for the data columns ***
    # This forces text wrapping, preventing the table from spanning too wide.
    table.max_width["Pre-Migration (102)"] = 60
    table.max_width["Post-Migration (200)"] = 60

    # Add the data row
    table.add_row([dot_key, value_102, value_200])

    # Configure table alignment and style
    table.align = "l"  # Left alignment for all columns

    print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare YAML values between pre and post migration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare a specific key
  python compare_labels.py global.commonlabels

  # Compare all keys from merge_rules.yaml
  python compare_labels.py --rules

  # Compare a specific key with array indexing
  python compare_labels.py db-replication-svc.dbreplsvcdeployments[0].service.annotations
        """
    )

    parser.add_argument(
        'key',
        nargs='?',
        help='Dot notation key to compare (e.g., global.commonlabels)'
    )

    parser.add_argument(
        '--rules',
        action='store_true',
        help='Compare all keys mentioned in merge_rules.yaml'
    )

    args = parser.parse_args()

    if args.rules:
        # Compare all keys from merge_rules.yaml
        compare_all_rules()
    elif args.key:
        # Compare specific key
        query_yaml_and_compare(args.key)
    else:
        parser.print_help()
        print("\nERROR: You must provide either a key to compare or use --rules flag")
        sys.exit(1)
