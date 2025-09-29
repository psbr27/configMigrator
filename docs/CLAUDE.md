# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConfigMigrator is an automated configuration migration tool that systematically compares and merges YAML configuration files while logging all conflicts and structural changes. The tool migrates operational settings from a production configuration version (V_OLD) to a new target configuration schema version (V_NEW).

### Core Workflow
1. **Input**: Takes three YAML files (Golden Config V_OLD, Engineering Template V_OLD, Engineering Template V_NEW)
2. **Analysis**: Identifies structural differences and custom data
3. **Merge**: Applies customizations to new template with conflict resolution
4. **Output**: Generates new golden config and detailed conflict log

## Development Commands

### Setup and Installation
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once project structure is created)
pip install -r requirements.txt
pip install -e .
```

### Code Quality and Linting
```bash
# Run mypy for type checking (strict mode required)
mypy src/ --strict --warn-return-any --warn-unused-configs

# Run ruff for linting and formatting
ruff check src/ tests/           # Linting
ruff format src/ tests/          # Formatting
ruff check --fix src/ tests/     # Auto-fix issues

# Pre-commit hooks (when configured)
pre-commit run --all-files
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_merge_engine.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run tests for specific functionality
pytest -k "test_conflict_resolution"
```

### Running the Tool
```bash
# Basic usage
python src/config_migrator.py \
  --golden-old ./configs/V_OLD-golden.yaml \
  --template-old ./templates/V_OLD-template.yaml \
  --template-new ./templates/V_NEW-template.yaml \
  --output-config ./output/V_NEW-golden.yaml \
  --output-log ./output/migration-log.json

# With additional options
python src/config_migrator.py \
  --golden-old ./configs/V_OLD-golden.yaml \
  --template-old ./templates/V_OLD-template.yaml \
  --template-new ./templates/V_NEW-template.yaml \
  --output-config ./output/V_NEW-golden.yaml \
  --output-log ./output/migration-log.json \
  --migration-map ./mappings/renames.json \
  --format json \
  --dry-run \
  --verbose
```

## Architecture Overview

### Core Components

**5-Module Architecture**:
1. **yaml_processor.py**: YAML file I/O with ruamel.yaml for format preservation
2. **diff_analyzer.py**: Template comparison and structural change detection
3. **merge_engine.py**: Core merge logic and conflict resolution engine
4. **conflict_logger.py**: Structured audit logging (JSON/CSV output)
5. **validators.py**: Input/output validation and error handling

### Data Flow Architecture

```
Input Files → YAML Processor → Diff Analyzer → Merge Engine → Conflict Logger → Output Files
     ↓              ↓              ↓              ↓              ↓
Golden Config   Parse/Load    Find Changes   Resolve       Generate     New Config
Template Old       ↓         Deletions      Conflicts      Audit Log    + Log File
Template New   Validation    Additions      Apply Custom
                             Migrations     Values
```

### Key Data Structures

**Conflict Resolution Types**:
- `OVERWRITE`: Custom value applied to new template
- `DELETED`: Key removed in new version, custom value lost
- `STRUCTURAL_MISMATCH`: Type/structure changed, requires manual review
- `MIGRATED`: Key renamed/moved via migration mapping
- `ADDED`: New key in V_NEW template

**Path Representation**: Dot notation (e.g., `service.api.port`) for nested YAML structure navigation

### Core Algorithms

**3-Way Merge Process**:
1. Extract custom data by diffing Golden Config vs Template Old
2. Analyze Template Old vs Template New for structural changes
3. Apply custom data to Template New with conflict resolution
4. Generate comprehensive audit log for all decisions

## Code Style Requirements

### Type Annotations
- **Strict mypy compliance required**: All functions must have complete type annotations
- Use `typing` module imports: `List`, `Dict`, `Optional`, `Union`, `Any`, `Tuple`
- Return type annotations mandatory for all functions
- Class attributes must be type-annotated

```python
from typing import Dict, List, Optional, Any, Tuple

def extract_custom_data(self, golden_config: Dict[str, Any],
                       template_old: Dict[str, Any]) -> Dict[str, Any]:
```

### Ruff Configuration Compliance
- Line length: 88 characters (Black-compatible)
- Import sorting: isort-compatible
- No unused imports or variables
- Consistent quote style (double quotes preferred)
- Proper docstring formatting (Google style)

### Function Documentation
```python
def resolve_conflicts(self, custom_data: Dict[str, Any],
                     template_new: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Resolve conflicts between custom data and new template structure.

    Args:
        custom_data: Dictionary of custom configuration values.
        template_new: New template configuration structure.

    Returns:
        Tuple containing merged configuration and list of conflict log entries.

    Raises:
        ValueError: If template structure is invalid.
        TypeError: If data types are incompatible.
    """
```

## Testing Patterns

### Unit Test Structure
```python
# tests/test_merge_engine.py
def test_simple_overwrite_conflict():
    """Test basic custom value overwrite scenario."""

def test_structural_mismatch_detection():
    """Test detection of incompatible type changes."""

def test_migration_mapping_application():
    """Test application of old-path to new-path mappings."""
```

### Test Fixtures
- Store test YAML files in `tests/fixtures/`
- Create realistic configuration scenarios
- Include edge cases (empty values, complex nesting, arrays)

## Error Handling Strategy

### Input Validation
- File existence and permissions
- YAML syntax validation
- Schema structure verification
- Required field presence

### Conflict Resolution
- Type compatibility checking
- Graceful degradation for non-critical errors
- Detailed logging for manual review requirements
- Clear error messages with file paths and line numbers

## Module Dependencies

**Core Dependencies**:
- `ruamel.yaml`: YAML processing with comment/format preservation
- `argparse`: CLI argument handling (built-in)
- `pathlib`: Modern path handling (built-in)

**Development Dependencies**:
- `pytest`: Testing framework
- `mypy`: Static type checking
- `ruff`: Linting and formatting
- `pre-commit`: Git hooks for code quality

**Optional Dependencies**:
- `jsonschema`: Output validation
- `click`: Alternative CLI framework (if argparse insufficient)

## Critical Implementation Notes

### YAML Processing
- Use `ruamel.yaml` to preserve comments and formatting
- Handle Unicode and special characters properly
- Implement streaming for large configuration files (>10MB)

### Path Navigation
- Implement robust dot-notation path parsing
- Handle array indices in paths (e.g., `servers.0.host`)
- Escape special characters in keys

### Conflict Logging
- Every modification must be logged with full context
- `manual_review=True` for structural mismatches
- Include human-readable explanations in `reason` field

### Performance Considerations
- Target: Process 10MB configs in <30 seconds
- Memory-efficient deep copying for large structures
- Lazy loading for optional migration mappings
