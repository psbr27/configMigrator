# CVPilot - Configuration Verification Pilot

A professional, enterprise-ready tool for merging YAML configuration files with NSPREV (Namespace Previous) precedence rules. Implements a complete two-stage migration workflow with proper logging and validation.

## Overview

CVPilot implements the complete configuration migration workflow:

**Stage 1**: NSPREV + ENGPREV → diff_nsprev_engprev.yaml (difference extraction)
**Stage 2**: diff + ENGNEW → intermediate result (merge with precedence rules)
**Stage 3**: Path transformation detection → final output file (resolve duplicate values)

The tool automatically runs all three stages in sequence to produce the final merged configuration with auto-generated filenames.

## Precedence Rules

The tool follows a strict precedence hierarchy across both stages:

**Stage 1 (NSPREV vs ENGPREV):**
1. **ENGPREV (Engineering Previous)** - Base template
2. **NSPREV (Namespace Previous)** - Site-specific values (highest precedence)
   - *Stage 1 extracts only differences between NSPREV and ENGPREV*

**Stage 2 (Diff vs ENGNEW vs ENGPREV):**
1. **ENGPREV (Engineering Previous)** - Base template (lowest precedence)
2. **ENGNEW (Engineering New)** - New features and updates (medium precedence)
3. **Diff File (NSPREV precedence)** - Site-specific values override everything (highest precedence)
4. **New Keys** - Include new keys from any file
5. **Deletions** - Ignore deletions (preserve all keys)

**NSPREV values take the highest precedence** - site-specific values are always preserved in the final output.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

## Usage

### Basic Usage

```bash
python -m cvpilot <nsprev_file> <engprev_file> <engnew_file>
```

### With Options

```bash
python -m cvpilot nsprev.yaml engprev.yaml engnew.yaml -o custom_output.yaml -v --summary
```

### Command Line Options

- `nsprev_file`: Namespace Previous File (site-specific configuration)
- `engprev_file`: Engineering Previous File (base template)
- `engnew_file`: Engineering New File (updated template)
- `-o, --output`: Output file name (default: auto-generated from nsprev filename + engnew version)
- `-v, --verbose`: Verbose output with INFO level logging
- `--debug`: Debug output with detailed logging
- `--summary`: Show detailed merge summary statistics

## Logging Levels

The tool provides three logging levels:

- **WARNING** (default): Minimal output, only success/error messages
- **INFO** (`-v`): Verbose output with progress information and timestamps
- **DEBUG** (`--debug`): Detailed debug information including file paths and internal operations

### Logging Examples

**WARNING Level (default):**
```
╭─────────── CVPilot - Configuration Verification Pilot ────────────╮
│ CVPilot Migration Workflow Successful!                            │
│ Stage 1: NSPREV + ENGPREV → diff_nsprev_engprev.yaml             │
│ Stage 2: diff + ENGNEW → nsprev_25.1.200.yaml                    │
╰────────────────────────────────────────────────────────────────────╯
```

**INFO Level (`-v`):**
```
2025-10-08 14:50:50 - cvpilot - INFO - Step 1: Validating all input files
2025-10-08 14:50:50 - cvpilot - INFO - All YAML files have valid syntax
2025-10-08 14:50:50 - cvpilot - INFO - Stage 1: Merging NSPREV and ENGPREV
2025-10-08 14:50:50 - cvpilot - INFO - Stage 2: Merging with ENGNEW
```

**DEBUG Level (`--debug`):**
```
2025-10-08 14:50:56 - cvpilot - DEBUG - Loading NSPREV file: nsprev.yaml
2025-10-08 14:50:56 - cvpilot - DEBUG - Loading ENGPREV file: engprev.yaml
2025-10-08 14:50:56 - cvpilot - DEBUG - Loading ENGNEW file: engnew.yaml
2025-10-08 14:50:56 - cvpilot - DEBUG - Saving final configuration to: nsprev_25.1.200.yaml
```

## Examples

### Example 1: Basic Migration

```bash
python -m cvpilot \
  rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml \
  occndbtier_custom_values_25.1.102.yaml \
  occndbtier_custom_values_25.1.200.yaml
```

This will create auto-generated filename `rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.200.yaml` with:
- Site-specific values from NSPREV (highest precedence)
- New features from ENGNEW (25.1.200)
- Base template from ENGPREV
- Automatic filename generation from NSPREV basename + ENGNEW version

### Example 2: With Verbose Logging and Summary

```bash
python -m cvpilot \
  nsprev.yaml engprev.yaml engnew.yaml \
  -o my_merged_config.yaml \
  -v --summary
```

### Example 3: Debug Mode

```bash
python -m cvpilot \
  nsprev.yaml engprev.yaml engnew.yaml \
  --debug
```

## How It Works

### Stage 1: NSPREV + ENGPREV (Difference Extraction)
1. **Load Files**: Load NSPREV and ENGPREV YAML files
2. **Validate Syntax**: Ensure all files have valid YAML syntax
3. **Compare**: Identify differences between NSPREV and ENGPREV
4. **Extract Differences**: Create diff_nsprev_engprev.yaml containing only the differences (not a complete merge)

### Stage 2: Diff + ENGNEW + ENGPREV (Merge with Precedence)
1. **Load ENGNEW**: Load the new template file
2. **Apply Precedence**: Apply Stage 2 precedence rules with three-way merge:
   - **NSPREV (via diff)**: Highest precedence - site-specific values override everything
   - **ENGNEW**: Medium precedence - new features and updates
   - **ENGPREV**: Lowest precedence - base template values
3. **Version Normalization**: Ensure version references are consistent throughout

### Stage 3: Path Transformation Detection (Structural Changes)
1. **Scan for Duplicates**: Detect values that appear in multiple paths (indicating structural changes)
2. **Compare with Reference**: Use ENGNEW as reference to determine correct structure
3. **Interactive Resolution**: Present findings to user with recommendations:
   - **High confidence**: Clear transformation (old path → new path)
   - **Medium confidence**: Both paths exist in reference (possible duplication)
   - **Low confidence**: Neither path exists in reference (manual review needed)
4. **Apply Transformations**: User selects which transformations to apply (or auto-apply high-confidence ones)
5. **Generate Filename**: Auto-generate output filename from NSPREV basename + ENGNEW version
6. **Output**: Generate final merged YAML file with auto-generated name

## Output

The tool generates a final merged YAML file (auto-generated filename like `nsprev_25.1.200.yaml`) that:
- **Preserves NSPREV Values**: All site-specific values from NSPREV are maintained (highest precedence)
- **Includes ENGNEW Features**: New features and updates from ENGNEW are added
- **Maintains ENGPREV Structure**: Base template structure from ENGPREV is preserved
- **Auto-Generated Filename**: Smart filename generation from NSPREV basename + ENGNEW version
- **Professional Formatting**: Clean, well-formatted YAML output using ruamel.yaml
- **Complete Configuration**: Ready-to-use configuration with all precedence rules applied

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/
```

### Project Structure

```
configMigratorv2/
├── src/cvpilot/
│   ├── core/           # Core functionality
│   │   ├── parser.py  # YAML parsing
│   │   └── merger.py  # Configuration merging
│   ├── cli/           # Command-line interface
│   │   └── commands.py
│   └── utils/         # Utility functions
│       ├── helpers.py # File operations and utilities
│       └── logging.py # Logging configuration
├── tests/             # Test suite (94 tests, 94% coverage)
└── examples/          # Example files
```

## Features

- ✅ **Complete Workflow**: Automatic Stage 1 + Stage 2 processing with difference extraction
- ✅ **Professional Logging**: DEBUG, INFO, WARNING levels with timestamps and Rich console output
- ✅ **Enterprise Ready**: Clean, professional output suitable for production environments
- ✅ **Generic**: Works with any YAML structure and configuration format
- ✅ **Future-proof**: No schema changes needed for new versions
- ✅ **Simple CLI**: Single command for complete workflow with auto-generated filenames
- ✅ **Fast**: Minimal dependencies and optimized performance
- ✅ **Flexible**: Handles complex nested configurations with deep merging
- ✅ **Type-safe**: Full mypy compliance and robust error handling
- ✅ **Well-tested**: Comprehensive test coverage (94 tests pass, 94% coverage)
- ✅ **High Quality**: ruamel.yaml for excellent YAML formatting and preservation
- ✅ **Smart Filename Generation**: Auto-generates output filenames from input basename + version
- ✅ **Difference Extraction**: Stage 1 extracts only differences for precise control
- ✅ **Three-way Precedence**: NSPREV > ENGNEW > ENGPREV with proper conflict resolution

## Dependencies

- `ruamel.yaml>=0.18.0` - Advanced YAML processing with formatting
- `click>=8.0.0` - Professional CLI interface
- `rich>=13.0.0` - Beautiful terminal output and progress bars

## License

This project is licensed under the MIT License.
