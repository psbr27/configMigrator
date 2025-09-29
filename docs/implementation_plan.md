# ConfigMigrator Implementation Plan

## Overview
This document provides a detailed implementation plan for the ConfigMigrator tool based on the design specifications. The tool will automate configuration migration between versions while maintaining audit trails.

## Phase 1: Project Setup and Core Infrastructure

### 1.1 Project Structure
```
configMigrator/
├── src/
│   ├── __init__.py
│   ├── config_migrator.py          # Main CLI entry point
│   ├── yaml_processor.py           # YAML loading/saving utilities
│   ├── diff_analyzer.py            # Template comparison logic
│   ├── merge_engine.py             # Core merge and conflict resolution
│   ├── conflict_logger.py          # Logging and audit trail
│   └── validators.py               # Input/output validation
├── tests/
│   ├── __init__.py
│   ├── test_yaml_processor.py
│   ├── test_diff_analyzer.py
│   ├── test_merge_engine.py
│   └── fixtures/                   # Test YAML files
├── requirements.txt
├── setup.py
└── README.md
```

### 1.2 Dependencies Setup
- **Primary**: `PyYAML` or `ruamel.yaml` for YAML processing
- **CLI**: `argparse` (built-in) for command-line interface
- **Testing**: `pytest` for unit testing
- **Validation**: `jsonschema` for output validation

## Phase 2: Core Module Implementation

### 2.1 YAML Processor Module (`yaml_processor.py`)

**Purpose**: Handle all YAML file operations with error handling

**Key Functions**:
```python
def load_yaml_file(file_path: str) -> dict
def save_yaml_file(data: dict, file_path: str) -> None
def validate_yaml_structure(data: dict) -> bool
```

**Implementation Details**:
- Use `ruamel.yaml` to preserve comments and formatting
- Implement comprehensive error handling for file I/O
- Add validation for YAML syntax and basic structure

### 2.2 Diff Analyzer Module (`diff_analyzer.py`)

**Purpose**: Analyze structural differences between template versions

**Key Functions**:
```python
def find_deleted_paths(old_template: dict, new_template: dict) -> List[str]
def find_added_paths(old_template: dict, new_template: dict) -> List[str]
def find_structural_changes(old_template: dict, new_template: dict) -> Dict[str, str]
def get_nested_value(data: dict, path: str) -> Any
def set_nested_value(data: dict, path: str, value: Any) -> None
```

**Implementation Details**:
- Implement recursive traversal for nested dictionaries
- Use dot notation for path representation (e.g., "service.api.port")
- Detect type changes (scalar to dict, list to scalar, etc.)
- Handle edge cases like empty values and null types

### 2.3 Merge Engine Module (`merge_engine.py`)

**Purpose**: Core logic for merging configurations and resolving conflicts

**Key Classes**:
```python
class ConflictResolution(Enum):
    OVERWRITE = "OVERWRITE"
    DELETED = "DELETED"
    ADDED = "ADDED"
    STRUCTURAL_MISMATCH = "STRUCTURAL_MISMATCH"
    MIGRATED = "MIGRATED"

class MergeEngine:
    def extract_custom_data(self, golden_config: dict, template_old: dict) -> Dict[str, Any]
    def resolve_conflicts(self, custom_data: Dict[str, Any], template_new: dict) -> Tuple[dict, List[dict]]
    def apply_migrations(self, custom_data: Dict[str, Any], migration_map: Dict[str, str]) -> Dict[str, Any]
```

**Implementation Details**:
- Compare values at each path between golden config and old template
- Implement all 4 conflict resolution cases from the design
- Generate detailed conflict log entries for each decision
- Handle complex nested structures and arrays

### 2.4 Conflict Logger Module (`conflict_logger.py`)

**Purpose**: Generate structured audit logs

**Key Functions**:
```python
def create_log_entry(path: str, action_type: str, source_value: Any,
                    target_value: Any, new_default_value: Any,
                    reason: str, manual_review: bool = False) -> dict
def export_to_json(log_entries: List[dict], output_path: str) -> None
def export_to_csv(log_entries: List[dict], output_path: str) -> None
```

**Log Entry Schema**:
```python
{
    "path": "service.api.port",
    "action_type": "OVERWRITE",
    "source_value": 8080,
    "target_value": 8080,
    "new_default_value": 9000,
    "reason": "Custom port configuration preserved",
    "manual_review": False
}
```

### 2.5 Validators Module (`validators.py`)

**Purpose**: Input validation and output verification

**Key Functions**:
```python
def validate_input_files(golden_old: str, template_old: str, template_new: str) -> bool
def validate_output_config(config: dict) -> bool
def check_file_permissions(file_path: str) -> bool
```

## Phase 3: CLI Interface Implementation

### 3.1 Main CLI Module (`config_migrator.py`)

**Command Structure**:
```bash
python config_migrator.py \
  --golden-old ./configs/V_OLD-golden.yaml \
  --template-old ./templates/V_OLD-template.yaml \
  --template-new ./templates/V_NEW-template.yaml \
  --output-config ./output/V_NEW-golden.yaml \
  --output-log ./output/migration-log.json \
  [--migration-map ./mappings/renames.json] \
  [--format json|csv] \
  [--dry-run] \
  [--verbose]
```

**Optional Features**:
- `--migration-map`: JSON file with old-path → new-path mappings
- `--format`: Output format for conflict log (JSON or CSV)
- `--dry-run`: Generate log without writing output config
- `--verbose`: Detailed console output

### 3.2 Error Handling Strategy

**File-level Errors**:
- Missing input files
- Permission issues
- Invalid YAML syntax
- Malformed file structures

**Logic-level Errors**:
- Incompatible template versions
- Circular migration mappings
- Type conversion failures

**Recovery Actions**:
- Graceful degradation where possible
- Detailed error messages with file paths and line numbers
- Suggestions for manual resolution

## Phase 4: Advanced Features

### 4.1 Migration Mapping Support

**JSON Schema for Migration Maps**:
```json
{
  "migrations": {
    "old.path.key": "new.path.key",
    "service.deprecated_api": "service.api.v2",
    "global.timeout": "service.timeouts.global"
  },
  "transformations": {
    "old.path.key": {
      "new_path": "new.path.key",
      "transform": "multiply_by_1000"  // seconds to milliseconds
    }
  }
}
```

### 4.2 Value Transformations

**Supported Transformations**:
- Unit conversions (seconds ↔ milliseconds)
- String format changes (comma-separated ↔ array)
- Boolean representations (true/false ↔ yes/no)
- Custom transformation functions

### 4.3 Backup and Rollback

**Features**:
- Automatic backup of original files
- Rollback command to restore previous state
- Timestamped backup directory structure

## Phase 5: Testing Strategy

### 5.1 Unit Tests

**Coverage Areas**:
- YAML processing edge cases
- Diff analysis accuracy
- Conflict resolution logic
- Log generation completeness

### 5.2 Integration Tests

**Test Scenarios**:
- Complete migration workflows
- Error handling paths
- CLI argument validation
- Output format verification

### 5.3 Test Data Sets

**Fixture Categories**:
- Simple configurations (flat key-value)
- Complex nested structures
- Array/list configurations
- Mixed data types
- Edge cases (empty values, null, special characters)

## Phase 6: Documentation and Deployment

### 6.1 User Documentation

**Required Documents**:
- Installation guide
- Usage examples
- Troubleshooting guide
- Migration best practices

### 6.2 Developer Documentation

**Technical Docs**:
- API reference
- Architecture overview
- Extension points for custom transformations
- Contributing guidelines

## Implementation Timeline

**Week 1-2**: Phase 1 & 2.1-2.2 (Setup + Basic YAML + Diff Analysis)
**Week 3-4**: Phase 2.3-2.4 (Merge Engine + Conflict Logging)
**Week 5**: Phase 2.5 + 3.1 (Validation + CLI)
**Week 6**: Phase 3.2 + Testing (Error Handling + Unit Tests)
**Week 7**: Phase 4.1-4.2 (Advanced Features)
**Week 8**: Phase 5-6 (Integration Testing + Documentation)

## Success Criteria

1. **Functionality**: Successfully migrates 95%+ of configuration values automatically
2. **Reliability**: Zero data loss, comprehensive conflict logging
3. **Usability**: Single command execution with clear error messages
4. **Maintainability**: Modular design allowing easy extension
5. **Performance**: Handles configurations up to 10MB in under 30 seconds

## Risk Mitigation

**Technical Risks**:
- Complex nested structure handling → Extensive testing with real-world configs
- YAML formatting preservation → Use ruamel.yaml instead of PyYAML
- Memory usage with large files → Implement streaming for very large configs

**Process Risks**:
- Incomplete requirements → Regular stakeholder review of implementation
- Integration complexity → Phased delivery with early feedback loops
