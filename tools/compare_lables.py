import sys
import json
from pathlib import Path
from ruamel.yaml import YAML
from prettytable import PrettyTable

# --- File Definitions (Based on CVPilot Example 1) ---
FILE_102 = "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml"
FILE_200 = "rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.200.yaml"

def get_nested_value(data_dict, dot_key):
    """
    Traverses a dictionary using dot-notation keys (e.g., 'global.commonlabels').
    Returns the found value or None if any key in the path is missing.
    """
    keys = dot_key.split('.')
    temp_data = data_dict
    for key in keys:
        if isinstance(temp_data, dict) and key in temp_data:
            temp_data = temp_data[key]
        else:
            return None
    return temp_data

def query_yaml_and_compare(dot_key):
    """
    Loads both YAML files, extracts the value for the given dot_key,
    and prints the results in a formatted, readable table.
    """
    print(f"Querying key: {dot_key}")
    print("--------------------------------------------------------")

    yaml = YAML()
    
    # --- 1. Load Files and Extract Values ---
    
    def extract_value(filepath):
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

    # Fetch values
    value_102 = extract_value(FILE_102)
    value_200 = extract_value(FILE_200)

    # --- 2. Format and Display Table ---
    
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
    if len(sys.argv) < 2:
        print("Usage: python compare_labels.py <dot.notation.key>")
        print("Example: python compare_labels.py global.commonlabels")
        sys.exit(1)

    key_to_query = sys.argv[1]
    query_yaml_and_compare(key_to_query)
