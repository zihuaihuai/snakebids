# Optional Entity Filtering Implementation

This branch implements the optional entity filtering functionality as requested in the GitHub issue.

## What was implemented

### 1. New `optional_entities` field in `InputConfig`
- Added `optional_entities: list[str]` field to the `InputConfig` TypedDict in `types.py`
- This field tracks which entities are considered optional for a component

### 2. Updated `ComponentEdit` plugin behavior
- Modified `update_cli_namespace()` in `plugins/component_edit.py`
- When `entity:optional` is specified via CLI, the entity is:
  - **Removed** from the `filters` dict
  - **Added** to the `optional_entities` list
- Updated documentation and help text to reflect the new behavior

### 3. Input generation logic changes
- Modified `_get_component()` in `core/input_generation.py`
- Before processing a file, check if it has all optional entities
- **Skip files entirely** if they're missing any optional entities
- This effectively excludes subjects that don't have the required optional entities

### 4. Updated tests
- Modified existing test in `test_plugins/test_component_edit.py`
- Test now verifies that optional filters are moved to `optional_entities` list
- Added comprehensive integration tests demonstrating the functionality

## How it works

### Difference from existing functionality:

1. **Regular filtering**: `entity=value` - only includes files with that specific value
2. **Required filtering**: `entity:required` - only includes files that have the entity (any value)
3. **None filtering**: `entity:none` - only includes files that DON'T have the entity
4. **NEW: Optional filtering**: `entity:optional` - **excludes entire subjects** that don't have the entity

### Example behavior:

Consider a dataset with:
- `sub-001`: has `ses-01`, `ses-02`
- `sub-002`: has `ses-01`, `ses-02`
- `sub-003`: no sessions
- `sub-004`: no sessions

With `session:optional`:
- **Result**: `sub-001 ses-01`, `sub-001 ses-02`, `sub-002 ses-01`, `sub-002 ses-02`
- **Excluded**: `sub-003`, `sub-004` (because they lack the optional entity `session`)

This is different from:
- **No filtering**: would include all subjects (including `sub-003`, `sub-004`)
- **`session:required`**: would only include files that have sessions (same result as optional in this case)
- **snakenull**: would include all subjects but add placeholder values for missing entities

## Key differences from snakenull

- **Optional filtering**: **Excludes** subjects missing optional entities
- **Snakenull**: **Includes** all subjects but adds placeholder values for missing entities

Optional filtering is useful when you want to analyze only subjects that have certain data types, while snakenull is useful when you want to analyze all subjects but need to handle missing/inconsistent entity labeling.

## Usage

### Via CLI:
```bash
snakebids-app --filter-T1w session:optional input output participant
```

### Via config:
```yaml
pybids_inputs:
  T1w:
    wildcards: [subject, session]
    filters:
      suffix: T1w
    optional_entities: [session]  # Exclude subjects without sessions
```

## Testing

The implementation includes:
1. Unit tests for the `ComponentEdit` plugin behavior
2. Integration tests demonstrating end-to-end functionality
3. Validation that subjects missing optional entities are properly excluded

All existing tests continue to pass, ensuring backward compatibility.
