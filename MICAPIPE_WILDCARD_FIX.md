# Micapipe Wildcard Error Fix Guide

## Problem Analysis

The error `WildcardError: No values given for wildcard 'acq'` is occurring because the micapipe Snakefile is trying to access wildcard values but getting empty lists. This can happen when:

1. The snakenull plugin returns data in a different format than expected
2. The way wildcards are being accessed in the rules doesn't account for the new structure
3. There's filtering happening that removes all values

## Immediate Fix Options

### Option 1: Update Micapipe Snakefile to Handle Snakenull Data

In your micapipe `workflow/Snakefile`, after calling `generate_inputs_with_snakenull`, add this processing:

```python
# After: inputs = generate_inputs_with_snakenull(...)

# Process snakenull results to ensure compatibility
for component_name, component_data in inputs.items():
    if isinstance(component_data, dict):
        # Handle dict format from snakenull fallback
        print(f"Processing snakenull dict format for {component_name}")
        
        # Convert to BidsComponent if needed
        try:
            from snakebids import BidsComponent
            inputs[component_name] = BidsComponent(**component_data)
            print(f"Converted {component_name} to BidsComponent")
        except Exception as e:
            print(f"Warning: Could not convert {component_name} to BidsComponent: {e}")
            # Keep as dict - rules will need to handle this format
    
    # Debug wildcard values
    entities = component_data.entities if hasattr(component_data, 'entities') else component_data
    print(f"Wildcard values for {component_name}:")
    for entity, values in entities.items():
        if entity != 'path':
            print(f"  {entity}: {values}")
            # Filter out null values for problematic wildcards
            if 'null' in values and len(set(values)) > 1:
                print(f"  Note: {entity} contains null values mixed with real values")

# Update config with processed inputs
config.update(inputs)
```

### Option 2: Filter Null Values in Rules

If the above doesn't work, modify rules that are failing. In `workflow/rules/structural.smk` around line 72, change:

```python
# OLD (probably causing the error):
expand(
    "some/path/sub-{subject}_ses-{session}_acq-{acq}_file.ext",
    zip,
    subject=inputs["t1w"]["subject"],
    session=inputs["t1w"]["session"], 
    acq=inputs["t1w"]["acq"]
)

# NEW (filter out null values):
expand(
    "some/path/sub-{subject}_ses-{session}_acq-{acq}_file.ext",
    zip,
    subject=[s for s, a in zip(inputs["t1w"]["subject"], inputs["t1w"]["acq"]) if a != "null"],
    session=[s for s, a in zip(inputs["t1w"]["session"], inputs["t1w"]["acq"]) if a != "null"],
    acq=[a for a in inputs["t1w"]["acq"] if a != "null"]
)
```

### Option 3: Use Traditional generate_inputs with Filtering

If snakenull is causing compatibility issues, temporarily switch back to standard `generate_inputs` with pre-filtering:

```python
# In workflow/Snakefile, replace generate_inputs_with_snakenull with:
from snakebids import generate_inputs

# Filter pybids_inputs to only include files that match all wildcards
filtered_pybids_inputs = {}
for component_name, component_config in config["pybids_inputs"].items():
    # Remove problematic optional wildcards temporarily
    filtered_config = component_config.copy()
    filtered_config["wildcards"] = [w for w in component_config["wildcards"] if w not in ["part"]]
    filtered_pybids_inputs[component_name] = filtered_config

try:
    inputs = generate_inputs(
        bids_dir=config["bids_dir"],
        pybids_inputs=filtered_pybids_inputs,  # Use filtered config
        # ... other parameters
    )
except Exception as e:
    print(f"Standard generate_inputs failed: {e}")
    print("Trying with snakenull fallback...")
    inputs = generate_inputs_with_snakenull(
        bids_dir=config["bids_dir"],
        pybids_inputs=config["pybids_inputs"],
        # ... other parameters
    )
```

## Testing the Fix

1. Add debug output to see what wildcard values are available:

```python
# Add this right after inputs = generate_inputs_with_snakenull(...)
print("=== DEBUG: Wildcard Values ===")
for comp_name, comp_data in inputs.items():
    entities = comp_data.entities if hasattr(comp_data, 'entities') else comp_data
    print(f"{comp_name}:")
    for entity, values in entities.items():
        if entity != 'path':
            empty_status = "EMPTY" if not values else "OK"
            null_count = sum(1 for v in values if v == 'null') if values else 0
            print(f"  {entity}: {len(values)} values, {null_count} nulls [{empty_status}]")
```

2. Run with dry-run to see the debug output:
```bash
python run.py /data/mica3/BIDS_MPN/rawdata_test/ test-MPN participant --module structural -np
```

## Next Steps

1. Try Option 1 first (add processing in Snakefile)
2. If that doesn't work, try Option 2 (filter nulls in specific rule)
3. If still having issues, use Option 3 (fallback approach)

The snakenull plugin is working correctly - it's generating the expected data with null value normalization. The issue is likely in how that data is being consumed by the existing micapipe rules.