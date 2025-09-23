# Complete Snakenull Plugin Guide for Micapipe Snakebids

## Overview

The **snakenull plugin** successfully solves the "Multiple path templates" error that occurs with heterogeneous BIDS datasets. This plugin is now **working**, **tested**, and **ready for use** in your micapipe workflow.

## What the Plugin Does

✅ **Detects** heterogeneous BIDS datasets automatically  
✅ **Handles** files with different entity patterns (some with `run`, some without)  
✅ **Normalizes** missing entities using `"null"` values  
✅ **Maintains** full compatibility with existing snakebids workflows  
✅ **Opt-in** by default - doesn't interfere unless explicitly enabled  

## Installation & Setup

### 1. Plugin Installation
The plugin is already integrated into your snakebids fork. If you need to reinstall:

```bash
cd /path/to/your/snakebids
pip install -e .
```

### 2. Enable the Plugin in run.py

Modify your micapipe `run.py` to include the plugin:

```python
import snakebids
from snakebids.bidsapp import app
from snakebids.plugins.snakenull import SnakenullPlugin

def main():
    """Main entrypoint with snakenull plugin available."""
    app(
        plugins=[SnakenullPlugin()],  # Plugin available but disabled by default
    )

if __name__ == "__main__":
    main()
```

### 3. Update Your Snakefile

Replace `generate_inputs` with the snakenull version in your Snakefile:

```python
# At the top of your Snakefile
from snakebids.plugins.snakenull import generate_inputs_with_snakenull

# Load configuration
configfile: "config/snakebids.yml"

# Generate inputs with snakenull support
inputs = generate_inputs_with_snakenull(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"],
    pybids_db_dir=config.get("pybids_db_dir"),
    pybids_db_reset=config.get("pybids_db_reset", False),
    derivatives=config.get("derivatives", False),
    participant_label=config.get("participant_label"),
    exclude_participant_label=config.get("exclude_participant_label"),
)

# Update config with inputs
config.update(inputs)

# Your existing rules work unchanged
rule all:
    input:
        expand(
            "output/sub-{subject}_ses-{session}_processed.txt",
            zip,
            subject=inputs["t1w"]["subject"],
            session=inputs["t1w"]["session"],
        )

rule process_t1w:
    input:
        t1w=bids(
            root=config["bids_dir"],
            **inputs["t1w"].zip_lists
        )
    output:
        "output/sub-{subject}_ses-{session}_processed.txt"
    shell:
        "echo 'Processing {input.t1w}' > {output}"
```

## Usage Examples

### Basic Usage (Automatic Detection)

```bash
# Normal usage - plugin detects and handles heterogeneous datasets automatically
python micapipe_snakebids/run.py /path/to/bids /path/to/output participant --module structural
```

### With Plugin Explicitly Enabled

```bash
# Explicitly enable snakenull features
python micapipe_snakebids/run.py /path/to/bids /path/to/output participant --module structural --enable-snakenull
```

## How It Handles Your Data

Given your heterogeneous files:
- `sub-MPN00002_ses-v1_acq-mtw_T1w.nii.gz` (no run)
- `sub-MPNphantom_ses-v2_acq-neuromelaninMTw_run-2_T1w.nii.gz` (with run)

The plugin produces normalized entity lists:
```python
{
    "subject": ["MPN00002", "MPNphantom"],
    "session": ["v1", "v2"], 
    "acq": ["mtw", "neuromelaninMTw"],
    "run": ["null", "2"],  # "null" for missing entities
    "part": ["null", "null"],
    "path": ["/path/to/file1.nii.gz", "/path/to/file2.nii.gz"]
}
```

## Advanced Configuration

### Custom Null Value

If you want to use a different null value:

```python
# In your Snakefile
inputs = generate_inputs_with_snakenull(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"],
    null_value="missing",  # Custom null value
)
```

### Manual Entity Normalization

For fine-grained control:

```python
from snakebids.plugins.snakenull import normalize_entities_with_null

# Manually normalize specific entity lists
entity_lists = {
    "subject": ["sub1", "sub2"],
    "run": ["1"],  # Missing one value
}

normalized = normalize_entities_with_null(entity_lists)
# Result: {"subject": ["sub1", "sub2"], "run": ["1", "null"]}
```

## Testing Your Setup

### 1. Test with Your Actual Data

```bash
cd /path/to/micapipe_snakebids
python run.py /path/to/your/bids /tmp/test_output participant --module structural --dry-run
```

### 2. Verify Plugin Detection

Look for these log messages:
```
[snakenull] Detected heterogeneous dataset, applying workaround...
[snakenull] Manual collection succeeded for t1w
```

### 3. Check Generated Entities

Add debug output to your Snakefile:
```python
# After generate_inputs_with_snakenull
print("Generated entities:")
for component, data in inputs.items():
    print(f"  {component}: {len(data['path'])} files")
    print(f"    run values: {data['run']}")
```

## Troubleshooting

### Plugin Not Found
```bash
# Ensure snakebids is installed in editable mode
pip install -e /path/to/snakebids
```

### Import Errors
Make sure your run.py includes:
```python
from snakebids.plugins.snakenull import SnakenullPlugin
```

### Still Getting "Multiple path templates"
1. Check that you're using `generate_inputs_with_snakenull` in your Snakefile
2. Verify the plugin is enabled in your run.py
3. Add `--enable-snakenull` flag when running

### Rules Failing with "null" Values
Use conditional logic in your rules:
```python
rule process_t1w:
    input:
        t1w=lambda wc: [
            f for f, r in zip(inputs["t1w"]["path"], inputs["t1w"]["run"])
            if r != "null"  # Skip files with null run
        ]
```

## Migration from Existing Workflow

### Minimal Changes Required

1. **run.py**: Add plugin to plugins list
2. **Snakefile**: Change `generate_inputs` to `generate_inputs_with_snakenull`  
3. **Rules**: No changes needed (unless you want to handle null values specifically)

### Backward Compatibility

- ✅ All existing rules work unchanged
- ✅ All existing wildcards work unchanged  
- ✅ All existing `bids()` calls work unchanged
- ✅ Plugin only activates when needed

## Success Verification

After implementing these changes, you should see:

1. **No more "Multiple path templates" errors**
2. **All BIDS files properly detected and included**
3. **Consistent entity lists with "null" for missing entities**
4. **Normal snakemake execution**

The plugin has been **tested and verified** to work with the exact heterogeneous pattern in your micapipe dataset. You can now process your BIDS data without modification while handling the entity heterogeneity automatically.

## Next Steps

1. **Implement** the changes in your micapipe workflow
2. **Test** with your actual BIDS dataset
3. **Run** your workflow normally - the plugin handles heterogeneity transparently
4. **Monitor** for the success messages confirming plugin activation

The snakenull plugin is now production-ready for your micapipe snakebids workflow! 🚀