"""Standalone snakenull implementation for snakebids.

This module provides snakenull functionality as a standalone solution that can be
applied to snakebids inputs without modifying the core snakebids code.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Set

_logger = logging.getLogger(__name__)


def apply_snakenull_normalization(
    inputs: Dict[str, Any], snakenull_config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Apply snakenull normalization to snakebids inputs.

    This function takes the output from snakebids.generate_inputs() and creates
    a unified template with placeholder values for missing entities, allowing
    each file to be processed independently and in parallel.

    Parameters
    ----------
    inputs : Dict[str, Any]
        Dictionary of snakebids components (output from generate_inputs)
    snakenull_config : Dict[str, Any], optional
        Configuration for snakenull processing:
        - enabled: bool (default True)
        - label: str (default "snakenull")
        - scope: str|List[str] (default "all")

    Returns
    -------
    Dict[str, Any]
        Modified inputs with snakenull normalization applied
    """
    if not snakenull_config:
        snakenull_config = {"enabled": True, "label": "snakenull", "scope": "all"}

    if not snakenull_config.get("enabled", True):
        return inputs

    label = snakenull_config.get("label", "snakenull")
    scope = snakenull_config.get("scope", "all")

    _logger.info("Applying snakenull normalization with label '%s'", label)

    # Process each component
    for component_name, component in inputs.items():
        if not hasattr(component, "zip_lists") or not component.zip_lists:
            _logger.warning("Component %s has no zip_lists, skipping", component_name)
            continue

        _logger.info("Processing component: %s", component_name)

        # Analyze the component to understand entity patterns
        zip_lists = component.zip_lists
        num_files = len(list(zip_lists.values())[0]) if zip_lists else 0

        if num_files == 0:
            _logger.warning("Component %s has no files, skipping", component_name)
            continue

        # Determine which entities should be normalized
        entities_to_normalize = _get_entities_in_scope(zip_lists.keys(), scope)

        # Apply normalization: create unified zip_lists where each file
        # has consistent entity coverage with placeholders for missing entities
        normalized_zip_lists = _normalize_zip_lists(
            zip_lists, entities_to_normalize, label, num_files
        )

        # Update the component template to include all entities
        updated_template = _update_component_template(
            component.path, normalized_zip_lists.keys()
        )

        # Update component with normalized data
        component.zip_lists = normalized_zip_lists
        component.path = updated_template

        _logger.info(
            "Normalized component %s: %d files with %d entities",
            component_name,
            num_files,
            len(normalized_zip_lists),
        )

    return inputs


def _get_entities_in_scope(
    available_entities: List[str], scope: str | List[str]
) -> Set[str]:
    """Determine which entities should be processed based on scope."""
    if scope == "all":
        return set(available_entities)
    elif isinstance(scope, (list, tuple)):
        return set(scope) & set(available_entities)
    else:
        return {scope} & set(available_entities)


def _normalize_zip_lists(
    zip_lists: Dict[str, List[str]],
    entities_to_normalize: Set[str],
    label: str,
    num_files: int,
) -> Dict[str, List[str]]:
    """Create normalized zip_lists with placeholder values for missing entities.

    The key insight: each position in the zip_lists corresponds to one input file.
    We need to ensure that for each file, all requested entities have values
    (either real values or snakenull placeholders).
    """
    # Start with existing zip_lists
    normalized = dict(zip_lists)

    # For each entity that should be normalized
    for entity in entities_to_normalize:
        if entity not in normalized:
            # Entity is completely missing - add it with all placeholders
            normalized[entity] = [label] * num_files
            _logger.debug(
                "Added missing entity '%s' with %d placeholders", entity, num_files
            )
        else:
            # Entity exists but may have missing values (None) for some files
            entity_values = normalized[entity]

            # Replace None values with snakenull placeholders
            for i in range(len(entity_values)):
                if entity_values[i] is None:
                    entity_values[i] = label

            # Check if we need to extend the list to match number of files
            if len(entity_values) < num_files:
                # Extend with placeholders to match number of files
                while len(entity_values) < num_files:
                    entity_values.append(label)

            normalized[entity] = entity_values
            _logger.debug("Normalized entity '%s' to %d values", entity, num_files)

    return normalized


def _update_component_template(
    original_template: str, normalized_entities: Set[str]
) -> str:
    """Update the component template to include all normalized entities.

    This ensures the template can handle all the entities in our normalized zip_lists.
    """
    import re

    # Extract existing wildcards from template
    existing_wildcards = set(re.findall(r"\{(\w+)\}", original_template))

    # Find entities that need to be added to the template
    missing_entities = normalized_entities - existing_wildcards

    if not missing_entities:
        return original_template

    # Add missing entities to the template in BIDS-compliant order
    # This is a simplified approach - in practice, you'd want proper BIDS ordering
    template = original_template

    # Insert new entities before the file extension
    for entity in sorted(missing_entities):  # Simple alphabetical order for now
        # Find the position before the file extension
        if "." in template:
            parts = template.rsplit(".", 1)
            base = parts[0]
            ext = "." + parts[1]
            template = f"{base}_{entity}-{{{entity}}}{ext}"
        else:
            template = f"{template}_{entity}-{{{entity}}}"

    _logger.debug("Updated template from '%s' to '%s'", original_template, template)
    return template


# Example usage and test function
def test_snakenull_with_t1w_dataset():
    """Test snakenull functionality with T1w files from the user's dataset."""

    # Mock the heterogeneous T1w files from the dataset
    # This simulates the real heterogeneous patterns from your dataset

    # These are the actual T1w files from your dataset with different entity patterns:
    # 1. sub-MPN00002_ses-v1_T1w.nii.gz (basic: subject, session only)
    # 2. sub-MPN00002_ses-v2_T1w.nii.gz (basic: subject, session only)
    # 3. sub-MPN00002_ses-v2_acq-mtw_T1w.nii.gz (adds acquisition)
    # 4. sub-MPN00002_ses-v2_acq-mtw_part-phase_T1w.nii.gz (adds acquisition + part)
    # 5. sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-1_T1w.nii.gz (adds acquisition + run)
    # 6. sub-MPNphantom_ses-v1_acq-mtw_T1w.nii.gz (phantom with acquisition)

    # Create separate components to represent the different patterns
    # In real snakebids, these would be discovered as different templates

    # Component 1: Basic T1w files (subject + session only)
    basic_t1w = type(
        "MockComponent",
        (),
        {
            "name": "t1w_basic",
            "path": "sub-{subject}_ses-{session}_T1w.nii.gz",
            "zip_lists": {
                "subject": ["MPN00002", "MPN00002"],
                "session": ["v1", "v2"],
            },
        },
    )()

    # Component 2: T1w with acquisition
    acq_t1w = type(
        "MockComponent",
        (),
        {
            "name": "t1w_acq",
            "path": "sub-{subject}_ses-{session}_acq-{acquisition}_T1w.nii.gz",
            "zip_lists": {
                "subject": ["MPN00002", "MPNphantom"],
                "session": ["v2", "v1"],
                "acquisition": ["mtw", "mtw"],
            },
        },
    )()

    # Component 3: T1w with acquisition + part
    acq_part_t1w = type(
        "MockComponent",
        (),
        {
            "name": "t1w_acq_part",
            "path": "sub-{subject}_ses-{session}_acq-{acquisition}_part-{part}_T1w.nii.gz",
            "zip_lists": {
                "subject": ["MPN00002"],
                "session": ["v2"],
                "acquisition": ["mtw"],
                "part": ["phase"],
            },
        },
    )()

    # Component 4: T1w with acquisition + run
    acq_run_t1w = type(
        "MockComponent",
        (),
        {
            "name": "t1w_acq_run",
            "path": "sub-{subject}_ses-{session}_acq-{acquisition}_run-{run}_T1w.nii.gz",
            "zip_lists": {
                "subject": ["MPN00002"],
                "session": ["v2"],
                "acquisition": ["neuromelaninMTw"],
                "run": ["1"],
            },
        },
    )()

    # Test each component separately first
    components = [
        ("Basic T1w", basic_t1w),
        ("T1w with acquisition", acq_t1w),
        ("T1w with acquisition + part", acq_part_t1w),
        ("T1w with acquisition + run", acq_run_t1w),
    ]

    print("=== Testing Snakenull with T1w Dataset ===")
    print(
        "This demonstrates how snakenull creates unified templates from heterogeneous files\n"
    )

    # Test each component type to show the different patterns
    for component_name, component in components:
        print(f"--- {component_name} ---")
        print(f"Template: {component.path}")
        print(f"Files: {len(list(component.zip_lists.values())[0])}")
        print(f"Entities: {list(component.zip_lists.keys())}")
        print()

    # Now demonstrate the key snakenull functionality:
    # Merge all these different patterns into one unified component
    print("=== SNAKENULL MAGIC: Creating Unified Component ===")

    # Combine all files into one component with all possible entities
    all_entities = ["subject", "session", "acquisition", "run", "part"]

    # Collect all files from all components
    all_files = []

    # From basic_t1w: files with only subject + session
    for i in range(len(basic_t1w.zip_lists["subject"])):
        file_entities = {
            "subject": basic_t1w.zip_lists["subject"][i],
            "session": basic_t1w.zip_lists["session"][i],
            "acquisition": None,  # Missing
            "run": None,  # Missing
            "part": None,  # Missing
        }
        all_files.append(file_entities)

    # From acq_t1w: files with subject + session + acquisition
    for i in range(len(acq_t1w.zip_lists["subject"])):
        file_entities = {
            "subject": acq_t1w.zip_lists["subject"][i],
            "session": acq_t1w.zip_lists["session"][i],
            "acquisition": acq_t1w.zip_lists["acquisition"][i],
            "run": None,  # Missing
            "part": None,  # Missing
        }
        all_files.append(file_entities)

    # From acq_part_t1w: files with subject + session + acquisition + part
    for i in range(len(acq_part_t1w.zip_lists["subject"])):
        file_entities = {
            "subject": acq_part_t1w.zip_lists["subject"][i],
            "session": acq_part_t1w.zip_lists["session"][i],
            "acquisition": acq_part_t1w.zip_lists["acquisition"][i],
            "run": None,  # Missing
            "part": acq_part_t1w.zip_lists["part"][i],
        }
        all_files.append(file_entities)

    # From acq_run_t1w: files with subject + session + acquisition + run
    for i in range(len(acq_run_t1w.zip_lists["subject"])):
        file_entities = {
            "subject": acq_run_t1w.zip_lists["subject"][i],
            "session": acq_run_t1w.zip_lists["session"][i],
            "acquisition": acq_run_t1w.zip_lists["acquisition"][i],
            "run": acq_run_t1w.zip_lists["run"][i],
            "part": None,  # Missing
        }
        all_files.append(file_entities)

    print(f"Total files collected: {len(all_files)}")
    print("Original file patterns:")
    for i, file_entities in enumerate(all_files, 1):
        original_entities = {k: v for k, v in file_entities.items() if v is not None}
        print(f"  File {i}: {original_entities}")

    # Create unified component for snakenull processing
    unified_zip_lists = {}
    for entity in all_entities:
        unified_zip_lists[entity] = [
            file_entities[entity] for file_entities in all_files
        ]

    unified_component = type(
        "MockComponent",
        (),
        {
            "name": "t1w_unified",
            "path": "sub-{subject}_ses-{session}_T1w.nii.gz",  # Start with basic template
            "zip_lists": unified_zip_lists,
        },
    )()

    mock_inputs = {"t1w": unified_component}

    print(f"\nUnified component before snakenull:")
    print(f"Template: {unified_component.path}")
    print(f"Zip lists with None values:")
    for entity, values in unified_component.zip_lists.items():
        print(f"  {entity}: {values}")

    # Apply snakenull normalization
    snakenull_config = {
        "enabled": True,
        "label": "snakenull",
        "scope": all_entities,  # Process all entities
    }

    print(f"\n=== Applying Snakenull Normalization ===")
    normalized_inputs = apply_snakenull_normalization(mock_inputs, snakenull_config)

    print("\n=== After Snakenull Normalization ===")
    t1w_component = normalized_inputs["t1w"]
    print(f"Normalized template: {t1w_component.path}")
    print(f"Normalized zip_lists:")
    for entity, values in t1w_component.zip_lists.items():
        print(f"  {entity}: {values}")

    print(
        f"\nNumber of files after normalization: {len(t1w_component.zip_lists['subject'])}"
    )

    # Show what the output files would look like with snakenull
    print("\n=== Expected Output Files (each processed independently) ===")
    num_files = len(t1w_component.zip_lists["subject"])
    for i in range(num_files):
        wildcards = {}
        for entity, values in t1w_component.zip_lists.items():
            wildcards[entity] = values[i]

        # Format the template with these wildcards
        output_file = t1w_component.path.format(**wildcards)
        # Convert to processed output (example)
        processed_file = output_file.replace("_T1w.nii.gz", "_T1w_processed.nii.gz")

        print(f"  File {i+1}: {processed_file}")
        print(f"    Wildcards: {wildcards}")

    print("\n=== KEY INSIGHT ===")
    print("Each file can now be processed independently with the SAME Snakemake rule!")
    print(
        "Files with missing entities get 'snakenull' placeholders, enabling parallel processing."
    )


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Run the test
    test_snakenull_with_t1w_dataset()
