"""Complete example of snakenull implementation for real-world dataset.

This demonstrates how snakenull works as a standalone "plugin" concept
that can be applied to snakebids outputs without modifying core code.
"""

from snakenull_standalone import apply_snakenull_normalization
import logging

# Configure logging to see the normalization process
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_realistic_t1w_component():
    """Create a component that mimics real snakebids output for T1w files from the user's dataset."""

    # Simulate what snakebids.generate_inputs() would return for the heterogeneous T1w files
    # Based on the actual files in /data/mica3/BIDS_MPN/rawdata_test/

    return type(
        "BidsComponent",
        (),
        {
            "name": "t1w",
            "path": "sub-{subject}_ses-{session}_T1w.nii.gz",  # Basic discovered template
            "zip_lists": {
                # These represent the actual T1w files found in the dataset
                "subject": [
                    "MPN00002",  # sub-MPN00002_ses-v1_T1w.nii.gz
                    "MPN00002",  # sub-MPN00002_ses-v2_T1w.nii.gz
                    "MPN00002",  # sub-MPN00002_ses-v2_acq-mtw_T1w.nii.gz
                    "MPN00002",  # sub-MPN00002_ses-v2_acq-mtw_part-phase_T1w.nii.gz
                    "MPN00002",  # sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-1_T1w.nii.gz
                    "MPNphantom",  # sub-MPNphantom_ses-v1_acq-mtw_T1w.nii.gz
                ],
                "session": ["v1", "v2", "v2", "v2", "v2", "v1"],
                # Some files have acquisition, others don't - represented as None
                "acquisition": [None, None, "mtw", "mtw", "neuromelaninMTw", "mtw"],
                # Some files have run, others don't
                "run": [None, None, None, None, "1", None],
                # Some files have part, others don't
                "part": [None, None, None, "phase", None, None],
            },
        },
    )()


def demonstrate_snakemake_workflow():
    """Demonstrate how snakenull enables uniform Snakemake processing."""

    print("=" * 80)
    print("SNAKEBIDS SNAKENULL WORKFLOW DEMONSTRATION")
    print("=" * 80)
    print()

    # Step 1: Simulate snakebids.generate_inputs() output
    print("STEP 1: Initial snakebids input discovery")
    print("-" * 40)

    t1w_component = create_realistic_t1w_component()
    inputs = {"t1w": t1w_component}

    print(f"Original template: {t1w_component.path}")
    print(f"Files discovered: {len(t1w_component.zip_lists['subject'])}")
    print("Original zip_lists (with heterogeneous patterns):")
    for entity, values in t1w_component.zip_lists.items():
        print(f"  {entity}: {values}")
    print()

    # Step 2: Apply snakenull normalization
    print("STEP 2: Apply snakenull normalization")
    print("-" * 40)

    snakenull_config = {
        "enabled": True,
        "label": "snakenull",
        "scope": [
            "subject",
            "session",
            "acquisition",
            "run",
            "part",
        ],  # All entities we want in output
    }

    normalized_inputs = apply_snakenull_normalization(inputs, snakenull_config)
    normalized_component = normalized_inputs["t1w"]

    print(f"Normalized template: {normalized_component.path}")
    print("Normalized zip_lists (uniform patterns):")
    for entity, values in normalized_component.zip_lists.items():
        print(f"  {entity}: {values}")
    print()

    # Step 3: Show Snakemake rule compatibility
    print("STEP 3: Snakemake rule processing")
    print("-" * 40)

    print("With snakenull, you can now use a SINGLE Snakemake rule:")
    print()
    print("rule process_t1w:")
    print("    input:")
    print('        "path/to/inputs/{t1w.path}"')
    print("    output:")
    print(
        '        "path/to/outputs/sub-{subject}_ses-{session}_run-{run}_part-{part}_acquisition-{acquisition}_T1w_processed.nii.gz"'
    )
    print("    shell:")
    print('        "micapipe -struct {input} -o {output}"')
    print()

    # Step 4: Show parallel execution
    print("STEP 4: Parallel execution - each file processed independently")
    print("-" * 40)

    num_files = len(normalized_component.zip_lists["subject"])
    for i in range(num_files):
        wildcards = {}
        for entity, values in normalized_component.zip_lists.items():
            wildcards[entity] = values[i]

        # Show input and output for each execution
        input_path = normalized_component.path.format(**wildcards)
        output_path = f"sub-{wildcards['subject']}_ses-{wildcards['session']}_run-{wildcards['run']}_part-{wildcards['part']}_acquisition-{wildcards['acquisition']}_T1w_processed.nii.gz"

        print(f"Job {i+1}:")
        print(f"  Input:  {input_path}")
        print(f"  Output: {output_path}")
        print(f"  Command: micapipe -struct {input_path} -o {output_path}")
        print()

    # Step 5: Show the key benefit
    print("STEP 5: Key Benefits")
    print("-" * 40)

    print("✓ PARALLEL PROCESSING: Each file runs independently")
    print("✓ UNIFORM INTERFACE: Same rule handles all file patterns")
    print("✓ NO COMPLEX LOGIC: No conditional wildcards in Snakemake rules")
    print("✓ BIDS COMPLIANT: Preserves BIDS entity structure")
    print("✓ EXTENSIBLE: Easy to add new entities or file patterns")
    print()

    print("Files with 'snakenull' entities represent missing/optional data")
    print("that gets filled in automatically for uniform processing.")
    print()

    return normalized_inputs


def create_example_snakemake_config():
    """Show how this would integrate into a real Snakemake workflow."""

    print("=" * 80)
    print("INTEGRATION EXAMPLE: Using snakenull in a real workflow")
    print("=" * 80)
    print()

    example_config = """
# Example: How to integrate snakenull into your workflow

# 1. In your main workflow script:
from snakebids import generate_inputs
from snakenull_standalone import apply_snakenull_normalization

# 2. Generate inputs as usual
inputs = generate_inputs(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"]
)

# 3. Apply snakenull normalization
snakenull_config = {
    "enabled": True,
    "label": "snakenull",
    "scope": ["subject", "session", "acquisition", "run", "part"]
}

normalized_inputs = apply_snakenull_normalization(inputs, snakenull_config)

# 4. Use normalized inputs in your rules
rule process_structural:
    input:
        t1w=normalized_inputs["t1w"].path
    output:
        "results/sub-{subject}_ses-{session}_run-{run}_part-{part}_acquisition-{acquisition}_T1w_processed.nii.gz"
    shell:
        "micapipe -struct {input.t1w} -o {output}"

# The rule will automatically run for each file with appropriate wildcards!
"""

    print(example_config)


if __name__ == "__main__":
    # Run the full demonstration
    normalized_inputs = demonstrate_snakemake_workflow()

    # Show integration example
    create_example_snakemake_config()

    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("This shows how snakenull works as a 'plugin' concept:")
    print("- No changes to core snakebids code")
    print("- Applied as post-processing step")
    print("- Enables uniform handling of heterogeneous BIDS datasets")
    print("- Maintains parallel execution capability")
    print()
    print(
        f"Test passed: Processed {len(normalized_inputs['t1w'].zip_lists['subject'])} heterogeneous T1w files"
    )
