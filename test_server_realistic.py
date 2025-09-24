#!/usr/bin/env python3
"""Server-realistic integration test that would have caught the wildcards bug.

This test recreates the exact conditions that caused the server failure.
"""

import sys
import tempfile
from pathlib import Path

from snakebids.plugins.snakenull import (
    generate_inputs_with_snakenull,  # type: ignore[reportUnknownVariableType]
)


def test_server_realistic_integration():  # noqa: PLR0912, PLR0915
    """Test with server-like data, config, and usage pattern."""
    print("=== Server-Realistic Integration Test ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        bids_dir = Path(tmpdir) / "bids"

        # Recreate EXACT server dataset structure from conversation
        # This includes the 'part' entity that was missing from local tests!
        server_files = [
            # MPNphantom subject
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-2_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-3_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-1_T1w.nii.gz",
            # KEY: has 'part'!
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_part-phase_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-4_T1w.nii.gz",
            # MPN00002 subject
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-2_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-1_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-3_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-4_T1w.nii.gz",
            # Missing acq, run
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_T1w.nii.gz",
            # Missing run
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-mtw_T1w.nii.gz",
            # KEY: has 'part'!
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-mtw_part-phase_T1w.nii.gz",
            # Missing acq, run, part
            "sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_T1w.nii.gz",
        ]

        for file_path in server_files:
            full_path = bids_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("dummy")

        # Use EXACT micapipe config including 'part' wildcard
        # that was missing from local tests
        micapipe_config = {
            "pybids_inputs": {
                "t1w": {
                    "filters": {
                        "suffix": "T1w",
                        "extension": ".nii.gz",
                        "datatype": "anat",
                    },
                    # CRITICAL: This includes 'part' which was missing from local tests!
                    "wildcards": ["subject", "session", "acq", "run", "part"],
                }
            },
            "snakenull": {"enabled": True},
        }

        print(f"Created {len(server_files)} server-realistic files")
        print("Key differences from local tests:")
        print("  - Complex acquisition names: neuromelaninMTw")
        print("  - 'part' entity included in wildcards")
        print("  - Files with part-phase entity")
        print("  - Realistic subject names: MPNphantom, MPN00002")
        print("  - 14 files vs 3-5 in local tests")

        # Test with server-like usage pattern
        print("\n=== Micapipe-style usage ===")
        result = generate_inputs_with_snakenull(
            bids_dir=str(bids_dir),
            pybids_inputs=micapipe_config["pybids_inputs"],
            snakenull=micapipe_config["snakenull"],
        )

        # Test the exact access pattern that failed on server
        print("Testing server failure scenario...")
        component = result["t1w"]

        # These are the exact attributes accessed by micapipe that failed
        print(f"Component type: {type(component)}")
        print(f"Has wildcards: {hasattr(component, 'wildcards')}")

        if hasattr(component, "wildcards"):
            wildcards = component.wildcards
            print(f"Wildcards: {wildcards}")

            # Test specific attribute access that caused AttributeError
            try:
                subject_wildcard = wildcards.get("subject", None)
                print(f"Subject wildcard: {subject_wildcard}")
                print("✅ Wildcards access succeeded")
            except AttributeError as e:
                print(f"❌ Wildcards access failed: {e}")
                return False
        else:
            print("❌ Missing wildcards attribute - this would cause server error!")
            return False

        # Check that all required entities are present
        required_entities = ["subject", "session", "acq", "run", "part"]
        missing_entities = []

        if hasattr(component, "zip_lists"):
            present_entities = list(component.zip_lists.keys())
            missing_entities = [
                e for e in required_entities if e not in present_entities
            ]

        if missing_entities:
            print(f"❌ Missing entities from zip_lists: {missing_entities}")
            return False

        # Check for phantom combinations
        print("\n=== Phantom Check ===")
        real_files = {Path(f).name for f in server_files}
        phantom_count = 0

        for i in range(len(component.zip_lists["subject"])):
            combo = {
                "subject": component.zip_lists["subject"][i],
                "session": component.zip_lists["session"][i],
                "acq": component.zip_lists["acq"][i],
                "run": component.zip_lists["run"][i],
                "part": component.zip_lists["part"][i],
            }

            # Construct expected filename
            filename_parts = [f"sub-{combo['subject']}", f"ses-{combo['session']}"]
            if combo["acq"] != "snakenull":
                filename_parts.append(f"acq-{combo['acq']}")
            if combo["run"] != "snakenull":
                filename_parts.append(f"run-{combo['run']}")
            if combo["part"] != "snakenull":
                filename_parts.append(f"part-{combo['part']}")
            filename_parts.append("T1w.nii.gz")
            expected_filename = "_".join(filename_parts)

            if expected_filename not in real_files:
                phantom_count += 1

        print(f"Files processed: {len(component.zip_lists['subject'])}")
        print(f"Phantom combinations: {phantom_count}")

        success = (
            hasattr(component, "wildcards")
            and len(missing_entities) == 0
            and phantom_count == 0
        )

        print("\n=== RESULT ===")
        if success:
            print("🎉 SUCCESS: Server-realistic test passed!")
            print("✅ All required attributes present")
            print("✅ No missing entities")
            print("✅ No phantom combinations")
        else:
            print("❌ FAILURE: Would have caught the server bug!")

        return success


if __name__ == "__main__":
    success = test_server_realistic_integration()
    result = "would have caught" if not success else "validates"
    print(f"\nThis test {result} the server bug.")
    sys.exit(0 if success else 1)
