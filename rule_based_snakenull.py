"""Example Snakemake workflow with conditional logic for heterogeneous BIDS.

This shows how to handle missing entities directly in Snakemake rules
without manipulating the input structure.
"""

# Example Snakemake rule that handles optional entities
rule_with_conditionals = '''
rule process_heterogeneous_t1w:
    input:
        # Handle heterogeneous inputs with conditional logic
        t1w=lambda wildcards: get_t1w_path(wildcards)
    output:
        "derivatives/sub-{subject}/ses-{session}/anat/"
        "sub-{subject}_ses-{session}_processed.nii.gz"
    params:
        # Pass optional parameters conditionally
        run_param=lambda wildcards: f"--run {wildcards.run}" if hasattr(wildcards, 'run') and wildcards.run != "snakenull" else "",
        part_param=lambda wildcards: f"--part {wildcards.part}" if hasattr(wildcards, 'part') and wildcards.part != "snakenull" else ""
    shell:
        "process_t1w {input.t1w} {output} {params.run_param} {params.part_param}"

def get_t1w_path(wildcards):
    """Helper function to build input path conditionally."""
    base_path = f"sub-{wildcards.subject}/ses-{wildcards.session}/anat/"
    filename = f"sub-{wildcards.subject}_ses-{wildcards.session}"
    
    # Add optional entities if they exist and aren't snakenull
    if hasattr(wildcards, 'acquisition') and wildcards.acquisition != "snakenull":
        filename += f"_acq-{wildcards.acquisition}"
    if hasattr(wildcards, 'run') and wildcards.run != "snakenull":
        filename += f"_run-{wildcards.run}"
    if hasattr(wildcards, 'part') and wildcards.part != "snakenull":
        filename += f"_part-{wildcards.part}"
    
    filename += "_T1w.nii.gz"
    return base_path + filename

# Alternative: Use input functions with error handling
def safe_t1w_input(wildcards):
    """Input function that handles missing files gracefully."""
    import os
    
    # Try different combinations to find existing file
    possible_paths = [
        f"sub-{wildcards.subject}_ses-{wildcards.session}_T1w.nii.gz",
        f"sub-{wildcards.subject}_ses-{wildcards.session}_acq-{getattr(wildcards, 'acquisition', 'NONE')}_T1w.nii.gz",
        f"sub-{wildcards.subject}_ses-{wildcards.session}_run-{getattr(wildcards, 'run', 'NONE')}_T1w.nii.gz",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Fallback or raise informative error
    raise FileNotFoundError(f"No T1w file found for {wildcards.subject}/{wildcards.session}")
'''

print("Rule-based conditional logic approach:")
print(rule_with_conditionals)