#!/usr/bin/env python3
"""Test the snakenull plugin integration."""

import json
from snakebids_snakenull_plugin import SnakenullPlugin, apply_snakenull_to_inputs


def test_snakenull_plugin():
    """Test the snakenull plugin with realistic snakebids input data."""

    # Simulate snakebids pybids_inputs as they would appear in config
    mock_inputs = {
        "dwi": {
            "filters": {"suffix": "dwi", "extension": [".nii.gz", ".nii"]},
            "zip_lists": {
                "subject": ["01", "02", "01"],
                "session": ["01", "01", "02"],
                "run": ["1", "1", "1"],
                "path": [
                    "/data/sub-01/ses-01/dwi/sub-01_ses-01_run-1_dwi.nii.gz",
                    "/data/sub-02/ses-01/dwi/sub-02_ses-01_run-1_dwi.nii.gz",
                    "/data/sub-01/ses-02/dwi/sub-01_ses-02_run-1_dwi.nii.gz",
                ],
            },
        }
    }

    print("Original inputs:")
    print(json.dumps(mock_inputs, indent=2))
    print()

    # Apply snakenull normalization
    normalized_inputs = apply_snakenull_to_inputs(mock_inputs)

    print("Normalized inputs with snakenull:")
    print(json.dumps(normalized_inputs, indent=2))
    print()

    # Check the results
    dwi_zip_lists = normalized_inputs["dwi"]["zip_lists"]

    print("Analysis:")
    print(f"- Original combinations: {len(mock_inputs['dwi']['zip_lists']['subject'])}")
    print(f"- Normalized combinations: {len(dwi_zip_lists['subject'])}")

    # Count SNAKENULL entries
    null_count = sum(1 for path in dwi_zip_lists["path"] if path == "SNAKENULL")
    print(f"- SNAKENULL entries added: {null_count}")

    # Show unique combinations
    combinations = []
    for i in range(len(dwi_zip_lists["subject"])):
        combo = (
            dwi_zip_lists["subject"][i],
            dwi_zip_lists["session"][i],
            dwi_zip_lists["run"][i],
        )
        combinations.append(combo)

    print(f"- Unique combinations: {sorted(set(combinations))}")

    # Test plugin class
    plugin = SnakenullPlugin()

    # Simulate config as it would appear in snakebids
    test_config = {"pybids_inputs": mock_inputs}

    print("\nTesting plugin.finalize_config():")
    plugin.finalize_config(test_config)

    print("\nPlugin test completed successfully!")
    return normalized_inputs


if __name__ == "__main__":
    test_snakenull_plugin()
