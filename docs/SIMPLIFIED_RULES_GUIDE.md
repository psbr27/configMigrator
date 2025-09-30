# Simplified Network Migration Rules Guide

## Overview

The `network_migration_rules.json` file has been simplified to make it much easier for beginners to understand and modify. This guide explains the new simplified structure.

## File Structure

```json
{
  "version": "2.0",
  "description": "Simplified network migration rules for ConfigMigrator",

  "target_version": "25.1.200",

  "preserve_these_paths": [
    "mgm.annotations",
    "ndb.annotations",
    "api.annotations"
  ],

  "preserve_these_annotations": [
    "sidecar.istio.io/inject",
    "proxy.istio.io/config"
  ],

  "preserve_these_patterns": [
    "metallb\\.universe\\.tf/.*",
    "cis\\.f5\\.com/.*"
  ],

  "update_version_in": [
    "global.image.tag",
    "*.image.tag"
  ],

  "merge_strategy": "smart_merge",

  "required_labels": [
    "app"
  ]
}
```

## Configuration Sections

### 1. Basic Settings
- **`target_version`**: The version to update to during migration (e.g., "25.1.200")
- **`merge_strategy`**: How to merge configurations (currently "smart_merge")

### 2. What to Preserve
- **`preserve_these_paths`**: Exact configuration paths that should be preserved from the old configuration
- **`preserve_these_annotations`**: Specific annotation keys that are network-critical
- **`preserve_these_patterns`**: Regex patterns to match network-critical configurations

### 3. Version Updates
- **`update_version_in`**: Paths where version numbers should be updated (supports wildcards with `*`)

### 4. Validation
- **`required_labels`**: Labels that must be present in the final configuration

## How to Modify

### Adding New Paths to Preserve
```json
"preserve_these_paths": [
  "mgm.annotations",
  "ndb.annotations",
  "your.new.path.here"
]
```

### Adding New Annotations to Preserve
```json
"preserve_these_annotations": [
  "sidecar.istio.io/inject",
  "your.annotation.key"
]
```

### Adding New Patterns
```json
"preserve_these_patterns": [
  "metallb\\.universe\\.tf/.*",
  "your\\.pattern\\.here/.*"
]
```

### Updating Target Version
```json
"target_version": "25.2.100"
```

### Adding Version Update Paths
```json
"update_version_in": [
  "global.image.tag",
  "*.image.tag",
  "your.component.image.tag"
]
```

## Examples

### Example 1: Adding Support for New Load Balancer
```json
{
  "preserve_these_patterns": [
    "metallb\\.universe\\.tf/.*",
    "nginx\\.ingress\\.kubernetes\\.io/.*"
  ]
}
```

### Example 2: Preserving Custom Service Labels
```json
{
  "preserve_these_paths": [
    "mgm.annotations",
    "my-service.service.labels",
    "my-service.podAnnotations"
  ]
}
```

### Example 3: Updating Component Versions
```json
{
  "update_version_in": [
    "global.image.tag",
    "*.image.tag",
    "monitoring.image.tag",
    "logging.image.tag"
  ]
}
```

## Key Benefits of Simplified Rules

1. **Easy to Understand**: Clear, descriptive field names
2. **Easy to Modify**: No complex nested structures
3. **Self-Documenting**: Field names explain their purpose
4. **Beginner Friendly**: No regex knowledge required for basic usage
5. **Flexible**: Still supports patterns for advanced users

## Migration from Old Rules

If you have an old rules file, here's how to convert:

| Old Field | New Field |
|-----------|-----------|
| `network_critical_patterns[].pattern` | `preserve_these_patterns[]` |
| `critical_annotation_paths[]` | `preserve_these_paths[]` |
| `critical_annotations[]` | `preserve_these_annotations[]` |
| `version_update_rules.target_version` | `target_version` |
| `version_update_rules.version_paths[]` | `update_version_in[]` |

## Tips for Beginners

1. **Start Simple**: Begin with just the paths you know are important
2. **Test Changes**: Always test your rules with a small configuration first
3. **Use Wildcards**: The `*` wildcard in `update_version_in` matches any component
4. **Pattern Matching**: Use `.*` in patterns to match any characters
5. **Version Control**: Keep your rules file in version control

## Troubleshooting

- **Rules not working?**: Check that your paths match exactly (case-sensitive)
- **Patterns not matching?**: Remember to escape dots with `\\.` in regex patterns
- **Version not updating?**: Ensure your paths are in the `update_version_in` list
- **Too much preserved?**: Remove paths from `preserve_these_paths` that you don't need

## Getting Help

- Check the migration logs for detailed information about what was preserved
- Use `--verbose` flag to see detailed processing information
- Test with `--dry-run` to see what would be migrated without making changes
