"""Template-based approach for handling heterogeneous BIDS datasets.

This approach modifies Snakemake rule templates instead of manipulating zip_lists.
"""

def create_flexible_template(original_template: str, optional_entities: list[str]) -> str:
    """Create a template that handles optional entities.
    
    Parameters
    ----------
    original_template : str
        Original file template like "sub-{subject}_ses-{session}_run-{run}_T1w.nii.gz"
    optional_entities : list[str]
        Entities that might be missing, e.g., ['run', 'part']
        
    Returns
    -------
    str
        Flexible template that handles missing entities
    """
    # Example transformation:
    # "sub-{subject}_ses-{session}_run-{run}_T1w.nii.gz"
    # becomes:
    # "sub-{subject}_ses-{session}{run_part}T1w.nii.gz"
    # where run_part = "_run-{run}" if run != "snakenull" else ""
    
    flexible_template = original_template
    
    for entity in optional_entities:
        # Replace {entity} with conditional logic
        entity_pattern = f"_{entity}-{{{entity}}}"
        if entity_pattern in flexible_template:
            # Replace with conditional wildcard
            conditional_part = f"{{run_part if {entity} != 'snakenull' else ''}}"
            flexible_template = flexible_template.replace(
                entity_pattern, 
                conditional_part
            )
    
    return flexible_template

def create_snakemake_rule_with_flexible_input():
    """Example of how to handle heterogeneous inputs in Snakemake rules."""
    rule_example = '''
rule process_t1w:
    input:
        # Use lambda to handle optional entities
        t1w=lambda wildcards: (
            f"sub-{wildcards.subject}_ses-{wildcards.session}"
            + (f"_run-{wildcards.run}" if wildcards.run != "snakenull" else "")
            + (f"_part-{wildcards.part}" if wildcards.part != "snakenull" else "")
            + "_T1w.nii.gz"
        )
    output:
        "processed/sub-{subject}_ses-{session}_run-{run}_part-{part}_processed.nii.gz"
    shell:
        "process_t1w {input.t1w} {output}"
    '''
    return rule_example

if __name__ == "__main__":
    # Example usage
    original = "sub-{subject}_ses-{session}_run-{run}_part-{part}_T1w.nii.gz"
    flexible = create_flexible_template(original, ['run', 'part'])
    print("Original template:", original)
    print("Flexible template:", flexible)
    print("\nSnakemake rule example:")
    print(create_snakemake_rule_with_flexible_input())