## **Design Document: Automated Configuration Migration Tool (ConfigMigrator)**

This document outlines the design for an automated tool, **ConfigMigrator**, that generates a new **V\_NEW Golden Configuration** by systematically comparing and merging three input YAML files while logging all conflicts and structural changes.

---

## **1\. Goal and Scope**

**Goal:** To fully automate the migration of operational settings from a production configuration version (**V\_OLD**) to a new target configuration schema version (**V\_NEW**), ensuring data integrity and providing a clear audit log of all decisions and conflicts.

**Input Files:**

1. **Golden Config (V\_OLD):** The current production configuration (contains custom operational data).
2. **Engineering Template (V\_OLD):** The baseline schema for the current production version.
3. **Engineering Template (V\_NEW):** The target schema for the new version.

**Output Files:**

1. **Golden Config (V\_NEW):** The final, merged configuration file ready for deployment.
2. **Conflict Log (JSON/CSV):** A structured log detailing every modification, addition, deletion, and conflict resolution.

---

## **2\. Tool Architecture and Technology Stack**

### **A. Technology Stack**

* **Language:** Python (Recommended for its robust YAML processing).
* **YAML Library:** `PyYAML` or `ruamel.yaml` (The latter preserves comments and ordering, if required).
* **CLI Handling:** `argparse` for robust command-line argument management.
* **Data Structures:** Standard Python dictionaries and lists for in-memory representation of YAML data.

### **B. Execution Flow**

1. **Initialization:** Load files and parse arguments.
2. **Schema Analysis:** Determine structural changes (deletions/renames/additions) between the **V\_OLD** and **V\_NEW** templates.
3. **Custom Data Extraction:** Identify and isolate operational customizations from the **V\_OLD Golden Config**.
4. **Merge Phase:** Apply custom data onto the new **V\_NEW Template**.
5. **Logging & Output:** Write the final config and the conflict log.

---

## **3\. Detailed Data Structures**

### **A. Conflict Log Schema**

The log is the core output for auditing and must be highly structured. It will be stored as a list of dictionaries, suitable for outputting to JSON or CSV.

| Field | Data Type | Description |
| :---- | :---- | :---- |
| `path` | String | Dotted path to the key (e.g., `service.api.port`). |
| `action_type` | String | One of: `OVERWRITE`, `DELETED`, `ADDED`, `STRUCTURAL_MISMATCH`, `MIGRATED`. |
| `source_value` | Any | The value from the **V\_OLD Golden Config** (if applicable). |
| `target_value` | Any | The final value written to the **V\_NEW Golden Config**. |
| `new_default_value` | Any | The default value in the **V\_NEW Template** (used for `OVERWRITE` context). |
| `reason` | String | Human-readable explanation of the action taken. |
| `manual_review` | Boolean | `True` if the conflict requires mandatory human inspection (e.g., structure or type change). |

### **B. Internal Data Maps**

An internal **Custom Data Map** will store only the key/value pairs that are different between the two **V\_OLD** files, representing the user's customizations.

| Key | Value | Description |
| :---- | :---- | :---- |
| `path.to.key` | `custom_value` | Represents a setting in **V\_OLD Golden Config** that differs from **V\_OLD Template**. |

---

## **4\. Step-by-Step Automation Logic**

### **A. Step 1: Initialization and Parsing**

1. Read CLI arguments for the three input file paths.
2. Parse all three YAML files into `dict` objects:
   * `config_old_golden`
   * `template_old`
   * `template_new`
3. Initialize `final_config_new` as a deep copy of `template_new`.
4. Initialize an empty list for the `conflict_log`.

### **B. Step 2: Structural Analysis (Template-to-Template Diff)**

This step identifies schema changes (deletions and additions) and prepares for deletion logging.

1. **Identify Deletions:** Recursively traverse `template_old`. If a path exists in `template_old` but is **missing** in `template_new`, mark it as a potential deletion.
2. **Identify Additions:** Recursively traverse `template_new`. If a path exists in `template_new` but is **missing** in `template_old`, these are new keys. The script will use the `template_new` default value for these keys unless the user specifically provides custom values for them.
3. **Identify Renames/Migrations (Optional):** If a mapping of old-path-to-new-path is provided (e.g., in a separate input file), record these for explicit migration handling in Step 3\.

### **C. Step 3: Custom Data Extraction and Conflict Resolution**

This is the core merge logic, applying customization from the old config to the new structure.

1. **Recursively Traverse `config_old_golden`:** Iterate through every configuration key path.
2. **Check for Customization:**
   * Compare the value at the current path in `config_old_golden` against `template_old`.
   * If **different** → It is a **Custom Value**. Proceed to Conflict Check.
   * If **same** → Skip.
3. **Conflict Check and Resolution for Custom Values:**
   * **Case 1: Key Deleted in V\_NEW:** The path is marked as deleted (from Step 2).
     * **Action:** **Do NOT** apply the custom value.
     * **Log:** Record a `DELETED` entry, noting the custom value that was lost.
   * **Case 2: Simple Custom Overwrite:** The path exists in `template_new`. The custom value is applied.
     * **Action:** Apply the custom value to `final_config_new`.
     * **Log:** Record an `OVERWRITE` entry if the custom value differs from the new default (`template_new`value).
   * **Case 3: Structural Mismatch:** The path exists, but the expected **data type** (e.g., scalar vs. sequence) or the expected **sub-structure** has changed fundamentally between `template_old` and `template_new`.
     * **Action:** **Do NOT** apply the custom value. Retain the `template_new` default.
     * **Log:** Record a `STRUCTURAL_MISMATCH` entry. Set `manual_review=True`.
   * **Case 4: Key Renamed (Migration):** The path is in the known migration list (from Step 2).
     * **Action:** Apply the custom value to the **new path** in `final_config_new`.
     * **Log:** Record a `MIGRATED` entry, detailing the old and new paths.

### **D. Step 4: Finalization and Output**

1. **Validation:** Perform a basic YAML syntax check on `final_config_new`.
2. **Output Write:**
   * Write `final_config_new` to the specified output path (`V_NEW-golden.yaml`).
   * Serialize the `conflict_log` list to a structured JSON file (`migration-log.json`).

---

## **5\. Deployment and Usage**

### **A. Command Line Interface (CLI)**

The tool will be executed via a single command, passing the required file paths via CLI arguments:

Bash
python config\_migrator.py \\
  \--golden-old ./configs/V\_OLD-golden.yaml \\
  \--template-old ./templates/V\_OLD-template.yaml \\
  \--template-new ./templates/V\_NEW-template.yaml \\
  \--output-config ./output/V\_NEW-golden.yaml \\
  \--output-log ./output/migration-log.json

### **B. Post-Migration Review**

The final step in the workflow is the mandatory review by an engineer:

1. **Review the ConfigMigrator Log:** Engineers must review the `migration-log.json`, specifically filtering for entries where `manual_review` is **True** (e.g., structural changes or critical deletions).
2. **Functional Testing:** The generated `V_NEW-golden.yaml` must be deployed to a staging environment and undergo comprehensive functional and performance testing before production rollout.
