# Network Migration Rules Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Section Definitions](#section-definitions)
4. [Configuration Examples](#configuration-examples)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Overview

The `network_migration_rules.json` file is the configuration backbone of the ConfigMigrator tool. It defines how network-critical configurations are preserved, merged, and validated during YAML template migrations. This file allows you to customize the migration behavior without modifying source code.

### Purpose
- **Preserve Network Connectivity**: Ensures critical network configurations survive template upgrades
- **Smart Merging**: Intelligently combines old custom values with new template structure
- **Version Management**: Automatically updates version numbers where appropriate
- **Validation**: Ensures migrated configurations meet networking requirements
- **Extensibility**: Easy to add new rules for different environments or requirements

### When to Modify
- Adding support for new networking technologies (service mesh, load balancers, etc.)
- Changing target version for migrations
- Adding company-specific annotation patterns
- Modifying validation requirements
- Customizing merge strategies for specific configuration types

---

## File Structure

The configuration file contains seven main sections:

```json
{
  "network_critical_patterns": [...],      // Pattern matching for critical paths
  "critical_annotation_paths": [...],      // Specific paths needing special handling
  "network_annotation_patterns": [...],    // Patterns for critical annotation keys
  "critical_annotations": [...],           // Exact annotation keys to preserve
  "version_update_rules": {...},           // Version updating configuration
  "merge_strategies": {...},               // How to merge different config types
  "validation_rules": {...}                // Post-migration validation requirements
}
```

---

## Section Definitions

### 1. Network Critical Patterns

**Purpose**: Defines regex patterns that identify configuration paths containing network-critical settings.

```json
"network_critical_patterns": [
  {
    "pattern": ".*cis\\\\.f5\\\\.com/as3-(tenant|app|pool)",
    "category": "f5_integration",
    "priority": 100,
    "description": "F5 BIG-IP Container Ingress Services labels"
  }
]
```

#### Field Descriptions:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `pattern` | String (Regex) | Regular expression to match YAML paths | `".*metallb\\\\.universe\\\\.tf/.*"` |
| `category` | String | Logical grouping for related patterns | `"load_balancer"`, `"service_mesh"` |
| `priority` | Integer | Importance level (1-100, higher = more critical) | `100` (critical), `50` (medium) |
| `description` | String | Human-readable explanation | `"MetalLB load balancer annotations"` |

#### Pattern Matching Rules:
- Patterns use **dot notation** for YAML paths: `global.commonlabels`, `api.service.labels`
- Use `\\\\.` to match literal dots in JSON (e.g., `metallb\\\\.universe\\\\.tf`)
- Use `.*` for wildcard matching
- Patterns are case-insensitive
- Use `|` for alternation: `as3-(tenant|app|pool)`

#### Categories:
- **`f5_integration`**: F5 load balancer configurations
- **`service_discovery`**: Kubernetes service discovery labels
- **`load_balancer`**: Load balancer annotations (MetalLB, etc.)
- **`oracle_cnf`**: Oracle Cloud Native Framework settings
- **`service_mesh`**: Service mesh configurations (Istio, etc.)
- **`app_identification`**: Application identification labels

### 2. Critical Annotation Paths

**Purpose**: Specifies exact YAML paths where annotations require special merge handling.

```json
"critical_annotation_paths": [
  "mgm.annotations",
  "ndb.annotations",
  "api.annotations",
  "api.ndbapp.annotations",
  "db-monitor-svc.podAnnotations"
]
```

#### Usage:
- These paths get **intelligent merging** where both old and new annotations are preserved
- Format preservation (array vs. dictionary) is maintained
- Network-critical annotations take precedence over template defaults
- New template annotations are added without overwriting critical ones

#### Path Format:
- Use dot notation: `component.subcomponent.annotations`
- Path must exist in at least one of the configuration files
- Supports both `annotations` and `podAnnotations` fields

### 3. Network Annotation Patterns

**Purpose**: Regex patterns to identify which individual annotation keys are network-critical.

```json
"network_annotation_patterns": [
  "metallb\\\\.universe\\\\.tf/.*",
  "cis\\\\.f5\\\\.com/.*",
  "oracle\\\\.com\\\\.cnc/.*",
  "istio\\\\.io/.*"
]
```

#### How It Works:
1. When merging annotations, each annotation key is tested against these patterns
2. Keys matching these patterns are considered **network-critical**
3. Network-critical annotations from the old configuration are preserved
4. Non-network annotations follow standard merge rules

#### Pattern Examples:
- `"metallb\\\\.universe\\\\.tf/.*"` → Matches `metallb.universe.tf/address-pool`
- `"cis\\\\.f5\\\\.com/.*"` → Matches `cis.f5.com/as3-tenant`, `cis.f5.com/as3-app`
- `".*\\\\.istio\\\\.io/.*"` → Matches any Istio annotation

### 4. Critical Annotations

**Purpose**: Exact annotation key names that must always be preserved (no regex needed).

```json
"critical_annotations": [
  "sidecar.istio.io/inject",
  "sidecar.istio.io/proxyCPU",
  "sidecar.istio.io/proxyCPULimit",
  "sidecar.istio.io/proxyMemory",
  "sidecar.istio.io/proxyMemoryLimit",
  "proxy.istio.io/config",
  "traffic.sidecar.istio.io/excludeInboundPorts",
  "oracle.com/cnc"
]
```

#### Characteristics:
- **Exact string matching** (no regex processing)
- **Always preserved** regardless of other rules
- **High priority** - takes precedence over template values
- Common use cases: Service mesh injection, resource limits, traffic routing

### 5. Version Update Rules

**Purpose**: Controls automatic version updates during migration.

```json
"version_update_rules": {
  "target_version": "25.1.200",
  "version_paths": [
    "global.commonlabels.vz.webscale.com/version",
    "global.version",
    "global.image.tag"
  ],
  "component_image_paths": [
    "*.image.tag",
    "*.inframonitor.image.tag",
    "*.sidecar.image.tag",
    "*.initcontainer.image.tag",
    "*.initsidecar.image.tag"
  ]
}
```

#### Field Descriptions:

| Field | Description | Example |
|-------|-------------|---------|
| `target_version` | New version to update to | `"25.1.200"` |
| `version_paths` | Exact paths to update | `"global.version"` |
| `component_image_paths` | Wildcard patterns for image tags | `"*.image.tag"` |

#### Wildcard Patterns:
- `*` matches any component name
- `*.image.tag` matches `mgm.image.tag`, `ndb.image.tag`, `api.image.tag`, etc.
- Patterns are expanded to match all existing paths in the configuration

#### Version Update Logic:
1. Identifies fields containing version numbers
2. Replaces old version (e.g., `25.1.102`) with target version
3. Preserves field structure and formatting
4. Only updates if old version is found in the value

### 6. Merge Strategies

**Purpose**: Defines how different types of configurations are merged.

```json
"merge_strategies": {
  "annotations": {
    "strategy": "smart_merge",
    "preserve_network_critical": true,
    "maintain_array_format": true
  },
  "labels": {
    "strategy": "preserve_with_enhancement",
    "preserve_network_critical": true
  },
  "commonlabels": {
    "strategy": "preserve_with_version_update",
    "update_version_field": true
  }
}
```

#### Available Strategies:

**Smart Merge (`smart_merge`)**:
- Intelligently combines old and new values
- Preserves network-critical entries
- Adds new template entries
- Maintains original format (array/dictionary)

**Preserve with Enhancement (`preserve_with_enhancement`)**:
- Keeps all old values
- Adds new template values that don't exist
- Network-critical values take precedence

**Preserve with Version Update (`preserve_with_version_update`)**:
- Preserves structure and values
- Updates version-related fields automatically
- Useful for metadata that needs version sync

#### Strategy Options:

| Option | Description | Default |
|--------|-------------|---------|
| `preserve_network_critical` | Preserve network-critical values | `true` |
| `maintain_array_format` | Keep original array/dict format | `true` |
| `update_version_field` | Update version numbers | `false` |

### 7. Validation Rules

**Purpose**: Post-migration validation to ensure network configurations are complete.

```json
"validation_rules": {
  "required_f5_labels": [
    "cis.f5.com/as3-tenant",
    "cis.f5.com/as3-app",
    "cis.f5.com/as3-pool"
  ],
  "required_service_labels": [
    "app"
  ],
  "network_connectivity_requirements": [
    "*.service.labels",
    "*.connectivityService.labels"
  ]
}
```

#### Validation Types:

**Required F5 Labels**: Ensures F5 load balancer integration is complete
**Required Service Labels**: Validates basic Kubernetes service labeling
**Network Connectivity Requirements**: Checks for essential networking configurations

#### Validation Process:
1. Runs after migration is complete
2. Scans output configuration for required elements
3. Reports missing or incomplete network configurations
4. Provides warnings for potential connectivity issues

---

## Configuration Examples

### Adding Support for New Load Balancer

To add support for AWS Load Balancer Controller:

```json
{
  "pattern": ".*service\\\\.beta\\\\.kubernetes\\\\.io/aws-load-balancer-.*",
  "category": "aws_load_balancer",
  "priority": 90,
  "description": "AWS Load Balancer Controller annotations"
}
```

Add to `network_annotation_patterns`:
```json
"service\\\\.beta\\\\.kubernetes\\\\.io/aws-load-balancer-.*"
```

### Adding Custom Company Annotations

For company-specific annotations like `mycompany.com/environment`:

```json
{
  "pattern": ".*mycompany\\\\.com/.*",
  "category": "company_custom",
  "priority": 75,
  "description": "Company-specific configuration annotations"
}
```

### Version Migration Configuration

To migrate from version 25.1.200 to 26.0.0:

```json
"version_update_rules": {
  "target_version": "26.0.0",
  "version_paths": [
    "global.commonlabels.vz.webscale.com/version",
    "global.version",
    "global.image.tag"
  ]
}
```

### Adding New Critical Annotation Path

For a new component `auth-service`:

```json
"critical_annotation_paths": [
  "auth-service.annotations",
  "auth-service.podAnnotations"
]
```

### Custom Validation Rules

To ensure all services have environment labels:

```json
"validation_rules": {
  "required_environment_labels": [
    "environment",
    "tier",
    "team"
  ]
}
```

---

## Best Practices

### 1. Pattern Design
- **Be Specific**: Use precise patterns to avoid false matches
- **Test Patterns**: Validate regex patterns before deployment
- **Document Intent**: Always include clear descriptions
- **Avoid Overlap**: Ensure patterns don't conflict with each other

### 2. Priority Assignment
- **Critical Infrastructure**: 90-100 (F5, MetalLB, core networking)
- **Service Mesh**: 70-90 (Istio, Linkerd)
- **Monitoring/Logging**: 50-70 (Prometheus, Fluentd)
- **Application Specific**: 30-50 (Custom business logic)

### 3. Category Organization
- Use consistent naming conventions
- Group related patterns together
- Keep categories focused and specific
- Document category purposes

### 4. Version Management
- Update target version for each migration cycle
- Test version updates in non-production first
- Maintain backward compatibility when possible
- Document version-specific changes

### 5. Validation Strategy
- Include all critical networking requirements
- Test validation rules against known configurations
- Provide clear error messages
- Balance thoroughness with performance

---

## Troubleshooting

### Common Issues

#### 1. Pattern Not Matching
**Symptom**: Network configuration not preserved
**Causes**:
- Incorrect regex escaping in JSON
- Pattern too specific or too broad
- Case sensitivity issues

**Solutions**:
```json
// Incorrect - single backslash
"pattern": ".*metallb\.universe\.tf/.*"

// Correct - double backslash for JSON
"pattern": ".*metallb\\\\.universe\\\\.tf/.*"
```

#### 2. Version Updates Not Applied
**Symptom**: Old version numbers remain after migration
**Causes**:
- Incorrect path specification
- Old version string not found
- Path doesn't exist in configuration

**Debug Steps**:
1. Verify path exists: `global.version`
2. Check old version string is present
3. Ensure target version is different

#### 3. Validation Failures
**Symptom**: Migration completes but validation warnings appear
**Causes**:
- Missing required labels/annotations
- Incomplete network configuration
- New template doesn't include required fields

**Solutions**:
- Add missing fields to validation rules
- Update template to include required configurations
- Adjust validation requirements for new template structure

#### 4. Format Preservation Issues
**Symptom**: Arrays become dictionaries or vice versa
**Causes**:
- `maintain_array_format` not set correctly
- Conflicting merge strategies
- Template format differs from original

**Solutions**:
```json
"annotations": {
  "strategy": "smart_merge",
  "maintain_array_format": true
}
```

### Debugging Tips

#### 1. Enable Verbose Logging
```bash
python src/config_migrator.py --verbose --golden-old config.yaml ...
```

#### 2. Test with Dry Run
```bash
python src/config_migrator.py --dry-run --golden-old config.yaml ...
```

#### 3. Validate JSON Syntax
```bash
python -m json.tool network_migration_rules.json
```

#### 4. Test Pattern Matching
```python
import re
pattern = r".*metallb\.universe\.tf/.*"
test_path = "api.service.annotations.metallb.universe.tf/address-pool"
if re.search(pattern, test_path, re.IGNORECASE):
    print("Pattern matches!")
```

---

## Advanced Usage

### 1. Conditional Rules

While not directly supported, you can create environment-specific rule files:

```bash
# Production rules
cp network_migration_rules.json network_rules_prod.json

# Development rules
cp network_migration_rules.json network_rules_dev.json
# Edit network_rules_dev.json with different priorities/patterns

# Use specific rules
python src/config_migrator.py --rules-file network_rules_prod.json ...
```

### 2. Rule Inheritance

Create a base rules file and extend it:

**base_rules.json** (common rules):
```json
{
  "network_critical_patterns": [
    {"pattern": ".*istio\\\\.io/.*", "category": "service_mesh", "priority": 75}
  ]
}
```

**environment_rules.json** (environment-specific):
```json
{
  "network_critical_patterns": [
    {"pattern": ".*istio\\\\.io/.*", "category": "service_mesh", "priority": 75},
    {"pattern": ".*company\\\\.com/.*", "category": "custom", "priority": 80}
  ]
}
```

### 3. Multi-Stage Migrations

For complex migrations, use multiple rule files:

```bash
# Stage 1: Infrastructure components
python src/config_migrator.py --rules-file rules_infrastructure.json ...

# Stage 2: Application components
python src/config_migrator.py --rules-file rules_applications.json ...
```

### 4. Custom Merge Strategies

While merge strategies are predefined, you can create configuration-specific behavior:

```json
"merge_strategies": {
  "critical_services": {
    "strategy": "preserve_with_enhancement",
    "preserve_network_critical": true
  },
  "monitoring_services": {
    "strategy": "smart_merge",
    "preserve_network_critical": false
  }
}
```

### 5. Pattern Priority Resolution

When multiple patterns match the same path:
1. Higher priority patterns take precedence
2. Among equal priorities, first match wins
3. Critical annotations always override pattern matches

### 6. Dynamic Version Detection

For automatic version detection from templates:

```json
"version_update_rules": {
  "auto_detect_version": true,
  "version_source_path": "global.image.tag",
  "version_regex": "([0-9]+\\.[0-9]+\\.[0-9]+)"
}
```

*Note: This is a future enhancement concept*

---

## Summary

The `network_migration_rules.json` file provides powerful, flexible configuration for network-aware YAML migrations. By understanding and properly configuring each section, you can:

- Ensure network connectivity survives template upgrades
- Customize migration behavior for your environment
- Validate post-migration network configurations
- Maintain infrastructure standards across versions

**Key Takeaways**:
1. **Test thoroughly** before production use
2. **Document changes** for team understanding
3. **Version control** rule files alongside configurations
4. **Monitor migration results** for continuous improvement
5. **Start simple** and add complexity as needed

For additional support or questions about network migration rules, consult the migration logs and enable verbose output for detailed debugging information.
