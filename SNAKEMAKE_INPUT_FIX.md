# Snakemake Rule Input/Output Issue Fix

## The Problem

The error occurs because the micapipe Snakemake rule is trying to find input files with malformed paths like:
```
/data/mica3/BIDS_MPN/rawdata_test/sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_acq-mtw_run-1_T1w_part-phase_acquisition-mtw.nii.gz
```

This path contains BOTH:
- `acq-mtw` (original BIDS format)
- `acquisition-mtw` (config entity format)

This creates an impossible filename that doesn't exist.

## Root Cause

The issue is in how the micapipe Snakemake rules reference input files. The rules are incorrectly trying to modify the input file paths with additional wildcards.

## The Solution

### Option 1: Fix the micapipe Snakefile (Recommended)

The micapipe rules should be changed to use input files directly:

```python
# CURRENT (WRONG):
rule proc_structural:
    input:
        t1w = lambda wc: some_function_that_builds_wrong_path(wc)  # Creates malformed paths
    output:
        "output/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_run-{run}_part-{part}_space-nativepro_acquisition-{acquisition}_T1w.nii.gz"

# CORRECT:
rule proc_structural:
    input:
        t1w = lambda wc, input=inputs: get_input_file(input['t1w'], wc)  # Use existing BIDS files
    output:
        "output/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_run-{run}_part-{part}_space-nativepro_acquisition-{acquisition}_T1w.nii.gz"
```

Where `get_input_file()` finds the correct input file from the `inputs['t1w']['path']` list based on the wildcards.

### Option 2: Use Helper Functions (Current Workaround)

Use the provided helper functions in your Snakefile:

```python
from snakebids.plugins.snakenull import generate_inputs_with_snakenull
from micapipe_wildcard_helper import get_structural_input

# Generate inputs with snakenull plugin
inputs = generate_inputs_with_snakenull(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"]
)

rule proc_structural:
    input:
        t1w = lambda wc: get_structural_input(inputs, wc)
    output:
        "output/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_run-{run}_part-{part}_space-nativepro_acquisition-{acquisition}_T1w.nii.gz"
```

## Key Points

1. **Input files**: Use the original BIDS file paths from `inputs['t1w']['path']`
2. **Output files**: Use the normalized wildcard names (`acquisition`, not `acq`)
3. **Never modify input file paths** with additional wildcards - they should be used as-is
4. **The snakenull plugin is working correctly** - it provides both the original file paths and normalized entity values

## Example Helper Function

```python
def get_structural_input(inputs, wildcards):
    """Get the correct input file path for given wildcards."""
    t1w_data = inputs['t1w']

    # Find the index that matches the wildcards
    for i in range(len(t1w_data['subject'])):
        if (t1w_data['subject'][i] == wildcards.subject and
            t1w_data['session'][i] == wildcards.session and
            t1w_data['acquisition'][i] == wildcards.acquisition and
            t1w_data['run'][i] == wildcards.run and
            t1w_data['part'][i] == wildcards.part):
            return t1w_data['path'][i]

    raise ValueError(f"No input file found for wildcards: {wildcards}")
```
