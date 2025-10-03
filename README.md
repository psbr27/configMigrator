# Config Migrator

A professional, enterprise-ready tool for merging YAML configuration files with NSTF (Namespace Template File) precedence rules. Implements a complete two-stage migration workflow with proper logging and validation.

## Overview

This tool implements the complete configuration migration workflow:

**Stage 1**: NSTF + ETF → diff_nstf_etf.yaml
**Stage 2**: diff + NEWTF → migrated_new_eng_template.yml

The tool automatically runs both stages in sequence to produce the final merged configuration.

## Precedence Rules

The tool follows a strict precedence hierarchy across both stages:

**Stage 1 (NSTF vs ETF):**
1. **ETF (Engineering Template File)** - Base template
2. **NSTF (Namespace Template File)** - Site-specific values (highest precedence)

**Stage 2 (Diff vs NEWTF):**
1. **NEWTF (New Engineering Template File)** - New features and updates
2. **Diff File (NSTF precedence)** - Site-specific values override NEWTF
3. **New Keys** - Include new keys from either file
4. **Deletions** - Ignore deletions (preserve all keys)

**NSTF values take the highest precedence** - site-specific values are always preserved in the final output.

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
python -m config_migrator <nstf_file> <etf_file> <newtf_file>
```

### With Options

```bash
python -m config_migrator nstf.yaml etf.yaml newtf.yaml -o merged_config.yaml -v --summary
```

### Command Line Options

- `nstf_file`: Namespace Template File (site-specific configuration)
- `etf_file`: Engineering Template File (base template)
- `newtf_file`: New Engineering Template File (updated template)
- `-o, --output`: Output file name (default: `migrated_new_eng_template.yml`)
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
╭─────────── Config Migration Tool ────────────╮
│ Complete Migration Workflow Successful!      │
│ Output saved to: migrated_new_eng_template.yml│
╰───────────────────────────────────────────────╯
```

**INFO Level (`-v`):**
```
2025-10-03 11:50:50 - config_migrator - INFO - Step 1: Validating all input files
2025-10-03 11:50:50 - config_migrator - INFO - All YAML files have valid syntax
2025-10-03 11:50:50 - config_migrator - INFO - Stage 1: Merging NSTF and ETF
```

**DEBUG Level (`--debug`):**
```
2025-10-03 11:50:56 - config_migrator - DEBUG - Loading NSTF file: nstf.yaml
2025-10-03 11:50:56 - config_migrator - DEBUG - Saving final configuration to: output.yml
```

## Examples

### Example 1: Basic Migration

```bash
python -m config_migrator \
  rcnltxekvzwcslf-y-or-x-004-occndbtier_25.1.102.yaml \
  occndbtier_custom_values_25.1.102.yaml \
  occndbtier_custom_values_25.1.200.yaml
```

This will create `migrated_new_eng_template.yml` with:
- Site-specific values from NSTF (highest precedence)
- New features from NEWTF (25.1.200)
- Base template from ETF

### Example 2: With Verbose Logging and Summary

```bash
python -m config_migrator \
  nstf.yaml etf.yaml newtf.yaml \
  -o my_merged_config.yaml \
  -v --summary
```

### Example 3: Debug Mode

```bash
python -m config_migrator \
  nstf.yaml etf.yaml newtf.yaml \
  --debug
```

## How It Works

### Stage 1: NSTF + ETF
1. **Load Files**: Load NSTF and ETF YAML files
2. **Validate Syntax**: Ensure all files have valid YAML syntax
3. **Compare**: Identify differences between NSTF and ETF
4. **Merge**: Create diff_nstf_etf.yaml with NSTF precedence

### Stage 2: Diff + NEWTF
1. **Load NEWTF**: Load the new template file
2. **Create Deepcopy**: Create temporary copy of NEWTF
3. **Merge with Rules**: Apply Stage 2 precedence rules:
   - Modify: Use diff values for existing keys
   - New: Include new keys from either file
   - Deletion: Ignore deletions (preserve all keys)
4. **Output**: Generate final migrated_new_eng_template.yml

## Output

The tool generates a final merged YAML file (`migrated_new_eng_template.yml`) that:
- **Preserves NSTF Values**: All site-specific values from NSTF are maintained
- **Includes NEWTF Features**: New features and updates from NEWTF are added
- **Maintains ETF Structure**: Base template structure from ETF is preserved
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
├── src/config_migrator/
│   ├── core/           # Core functionality
│   │   ├── parser.py  # YAML parsing
│   │   └── merger.py  # Configuration merging
│   ├── cli/           # Command-line interface
│   │   └── commands.py
│   └── utils/         # Utility functions
├── tests/             # Test suite
└── examples/          # Example files
```

## Features

- ✅ **Complete Workflow**: Automatic Stage 1 + Stage 2 processing
- ✅ **Professional Logging**: DEBUG, INFO, WARNING levels with timestamps
- ✅ **Enterprise Ready**: Clean, emoji-free output suitable for production
- ✅ **Generic**: Works with any YAML structure
- ✅ **Future-proof**: No schema changes needed for new versions
- ✅ **Simple CLI**: Single command for complete workflow
- ✅ **Fast**: Minimal dependencies and overhead
- ✅ **Flexible**: Handles complex nested configurations
- ✅ **Type-safe**: Full mypy compliance
- ✅ **Well-tested**: Comprehensive test coverage (16/16 tests pass)
- ✅ **High Quality**: ruamel.yaml for excellent YAML formatting

## Dependencies

- `ruamel.yaml>=0.18.0` - Advanced YAML processing with formatting
- `click>=8.0.0` - Professional CLI interface
- `rich>=13.0.0` - Beautiful terminal output and progress bars

## License

This project is licensed under the MIT License.
