"""Helper functions for micapipe to handle snakenull plugin compatibility."""


def get_structural_input(inputs, wildcards, component_name="t1w"):
    """Get the correct input file path for given wildcards.

    This function resolves the input file path from the snakenull plugin
    output to work with micapipe's Snakemake rules.

    Parameters
    ----------
    inputs : dict
        The inputs dict from generate_inputs_with_snakenull
    wildcards : snakemake.wildcards
        The wildcards from the Snakemake rule
    component_name : str
        The component to get input for (default: "t1w")

    Returns
    -------
    str
        The path to the actual BIDS input file
    """
    if component_name not in inputs:
        raise ValueError(f"Component {component_name} not found in inputs")

    component = inputs[component_name]

    # Handle both dict and BidsComponent formats
    if hasattr(component, "entities"):
        # BidsComponent format
        entities = component.entities
    else:
        # Dict format (from snakenull plugin)
        entities = component

    # Find the index that matches the wildcards
    for i in range(len(entities["subject"])):
        match = True

        # Check each wildcard
        if (
            hasattr(wildcards, "subject")
            and entities["subject"][i] != wildcards.subject
        ):
            match = False
        if (
            hasattr(wildcards, "session")
            and entities["session"][i] != wildcards.session
        ):
            match = False
        if (
            hasattr(wildcards, "acquisition")
            and entities["acquisition"][i] != wildcards.acquisition
        ):
            match = False
        if hasattr(wildcards, "run") and entities["run"][i] != wildcards.run:
            match = False
        if hasattr(wildcards, "part") and entities["part"][i] != wildcards.part:
            match = False

        if match:
            return entities["path"][i]

    raise ValueError(f"No input file found for wildcards: {wildcards}")


def map_wildcards_for_micapipe(inputs, component_name="t1w"):
    """Map snakebids wildcards to micapipe's expected names.

    Parameters
    ----------
    inputs : dict
        The inputs dict from generate_inputs_with_snakenull
    component_name : str
        The component to map (default: "t1w")

    Returns
    -------
    dict
        Mapped wildcards suitable for expand() functions
    """
    if component_name not in inputs:
        return {}

    component = inputs[component_name]

    # Handle both dict and BidsComponent formats
    if hasattr(component, "entities"):
        # BidsComponent format
        entities = component.entities
    else:
        # Dict format (from snakenull plugin)
        entities = component

    # Map the wildcards with proper naming
    mapped = {
        "subject": entities.get("subject", []),
        "session": entities.get("session", []),
        "acquisition": entities.get("acq", []),  # Map acq -> acquisition
        "run": entities.get("run", []),
        "part": entities.get("part", []),
    }

    # Filter out empty lists to avoid expand() issues
    filtered = {k: v for k, v in mapped.items() if v}

    return filtered


# Example usage in your output functions:
def get_all_structural_outputs(inputs, output_dir):
    """Get all structural outputs with proper wildcard mapping."""
    wildcards = map_wildcards_for_micapipe(inputs, "t1w")

    if not wildcards:
        return []

    outputs = expand(
        f"{output_dir}/sub-{{subject}}/ses-{{session}}/anat/sub-{{subject}}_ses-{{session}}_run-{{run}}_part-{{part}}_space-nativepro_acquisition-{{acquisition}}_T1w.nii.gz",
        zip,
        **wildcards,
    )

    return outputs


# Alternative: Filter out null values if needed
def map_wildcards_for_micapipe_no_nulls(inputs, component_name="t1w"):
    """Map wildcards and filter out null values."""
    wildcards = map_wildcards_for_micapipe(inputs, component_name)

    # Filter out entries where any wildcard is "null"
    filtered_wildcards = {k: [] for k in wildcards.keys()}

    # Get length of first list to know how many entries we have
    if wildcards:
        first_key = next(iter(wildcards.keys()))
        num_entries = len(wildcards[first_key])

        for i in range(num_entries):
            # Check if this entry has any null values
            has_null = any(wildcards[k][i] == "null" for k in wildcards.keys())

            if not has_null:
                # Add this entry to filtered wildcards
                for k in wildcards.keys():
                    filtered_wildcards[k].append(wildcards[k][i])

    return filtered_wildcards
