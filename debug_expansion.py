#!/usr/bin/env python3
"""Debug the actual expand error that's happening in micapipe."""

import sys
import os

sys.path.insert(0, "/Users/enningyang/CodeProj/snakebids")

from snakebids.plugins.snakenull import generate_inputs_with_snakenull
from pathlib import Path


def debug_expansion_error():
    """Reproduce the exact error from micapipe."""

    # Mock a simple BIDS directory with mixed acq patterns
    test_dir = Path("/tmp/test_bids_debug")
    test_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (test_dir / "sub-MPN001" / "anat").mkdir(parents=True, exist_ok=True)

    # Create files with mixed acq patterns (like your MPN dataset)
    files_to_create = [
        "sub-MPN001/anat/sub-MPN001_T1w.nii.gz",  # No acq
        "sub-MPN001/anat/sub-MPN001_acq-mtw_T1w.nii.gz",  # Has acq
    ]

    for file_path in files_to_create:
        full_path = test_dir / file_path
        full_path.touch()
        print(f"Created: {full_path}")

    # Try the same pybids_inputs as micapipe
    pybids_inputs = {
        "t1w": {
            "filters": {"datatype": "anat", "suffix": "T1w", "extension": ".nii.gz"},
            "wildcards": ["subject", "session", "acq", "run", "part"],
        }
    }

    print("\n=== Testing generate_inputs_with_snakenull ===")

    try:
        inputs = generate_inputs_with_snakenull(
            bids_dir=test_dir, pybids_inputs=pybids_inputs
        )

        print(f"Success! Generated inputs: {list(inputs.keys())}")

        # Check the t1w component
        if "t1w" in inputs:
            t1w = inputs["t1w"]
            print(f"t1w type: {type(t1w)}")

            if hasattr(t1w, "entities"):
                print(f"t1w entities: {t1w.entities}")

                # Try to trigger the expand error like micapipe does
                print("\n=== Testing expand() method ===")

                # Simulate what happens in structural.smk line 72
                # This is likely where the error occurs
                try:
                    # Test simple string expansion
                    test_template = "output/sub-{subject}_acq-{acq}_T1w.nii.gz"
                    expanded = t1w.expand(test_template)
                    print(f"Expanded template: {expanded}")

                    # Test accessing wildcards like micapipe does
                    if hasattr(t1w, "wildcards"):
                        print(f"Wildcards: {t1w.wildcards}")

                        # Check if acq is properly populated
                        if "acq" in t1w.wildcards:
                            print(f"acq value: {t1w.wildcards['acq']}")
                        else:
                            print("ERROR: 'acq' not in wildcards!")

                except Exception as expand_error:
                    print(f"EXPAND ERROR: {expand_error}")
                    print(f"This matches your micapipe error!")

                    # Show the internal state
                    if hasattr(t1w, "entities"):
                        for entity, values in t1w.entities.items():
                            print(f"  {entity}: {values}")

            else:
                print("No entities attribute found")

    except Exception as e:
        print(f"Error in generate_inputs_with_snakenull: {e}")

    # Cleanup
    import shutil

    shutil.rmtree(test_dir)


if __name__ == "__main__":
    debug_expansion_error()
