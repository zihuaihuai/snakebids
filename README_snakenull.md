# Snakenull Plugin for Snakebids

This implements snakenull functionality as a standalone "plugin" that can be applied to snakebids outputs without modifying the core snakebids code.

## What is Snakenull?

Snakenull is a normalization system that enables uniform processing of heterogeneous BIDS datasets. It works by:

1. **Identifying** files with different entity patterns (some have `run`, others don't; some have `acquisition`, others don't)
2. **Normalizing** these patterns by filling missing entities with placeholder values (default: "snakenull")
3. **Creating** a unified template that allows each file to be processed independently in parallel

## Key Benefits

- ✅ **Parallel Processing**: Each file runs independently with the same Snakemake rule
- ✅ **Uniform Interface**: No complex conditional logic in workflows
- ✅ **BIDS Compliant**: Preserves BIDS entity structure
- ✅ **No Core Changes**: Works as post-processing on existing snakebids outputs

## Example

**Before Snakenull** (heterogeneous patterns):
```
sub-01_T1w.nii.gz                           # Basic file
sub-01_ses-01_T1w.nii.gz                    # Has session
sub-01_ses-01_acq-MPRAGE_T1w.nii.gz         # Has session + acquisition
sub-01_acq-MPRAGE_T1w.nii.gz                # Has acquisition only
```

**After Snakenull** (unified processing):
```
sub-01_ses-snakenull_acq-snakenull_T1w_processed.nii.gz
sub-01_ses-01_acq-snakenull_T1w_processed.nii.gz
sub-01_ses-01_acq-MPRAGE_T1w_processed.nii.gz
sub-01_ses-snakenull_acq-MPRAGE_T1w_processed.nii.gz
```

Each file processed with the **same Snakemake rule** in **parallel**.

## Usage

```python
from snakebids import generate_inputs
from snakenull_standalone import apply_snakenull_normalization

# 1. Generate inputs as usual
inputs = generate_inputs(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"]
)

# 2. Apply snakenull normalization
snakenull_config = {
    "enabled": True,
    "label": "snakenull",  # Placeholder for missing entities
    "scope": ["subject", "session", "acquisition", "run", "part"]  # Entities to normalize
}

normalized_inputs = apply_snakenull_normalization(inputs, snakenull_config)

# 3. Use in Snakemake rules
rule process_t1w:
    input:
        normalized_inputs["t1w"].path
    output:
        "results/sub-{subject}_ses-{session}_acquisition-{acquisition}_run-{run}_part-{part}_T1w_processed.nii.gz"
    shell:
        "micapipe -struct {input} -o {output}"
```

## Configuration Options

- `enabled`: Turn snakenull on/off (default: True)
- `label`: Placeholder value for missing entities (default: "snakenull")
- `scope`: Which entities to normalize - "all" or list of entity names

## Test with Real Dataset

The implementation has been tested with heterogeneous T1w files from `/data/mica3/BIDS_MPN/rawdata_test/`:

- `sub-MPN00002_ses-v1_T1w.nii.gz` (basic)
- `sub-MPN00002_ses-v2_acq-mtw_T1w.nii.gz` (with acquisition)
- `sub-MPN00002_ses-v2_acq-mtw_part-phase_T1w.nii.gz` (with acquisition + part)
- `sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-1_T1w.nii.gz` (with acquisition + run)

All files are successfully normalized and can be processed with a single Snakemake rule.

## Files

- `snakenull_standalone.py`: Core snakenull implementation
- `snakenull_demo.py`: Complete demonstration with your dataset
- `README.md`: This documentation

## Running the Demo

```bash
python snakenull_demo.py
```

This will show the complete workflow from heterogeneous file discovery through parallel processing setup.
