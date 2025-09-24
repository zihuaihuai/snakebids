#!/usr/bin/env python3
"""Test that reproduces the exact server phantom combination bug with all 14 files."""

import sys
import tempfile
from pathlib import Path

from snakebids.plugins.snakenull import (
    generate_inputs_with_snakenull,  # type: ignore[reportUnknownVariableType]
)


def test_exact_server_phantom_bug():
    """Reproduce the exact phantom combination bug from server with all 14 files."""
    print("=== Testing Exact Server Phantom Bug ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        bids_dir = Path(tmpdir) / "bids"

        # Create EXACT 14 files from server log
        server_files = [
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-2_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-3_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-1_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_part-phase_T1w.nii.gz",
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-4_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-2_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-1_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-3_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-neuromelaninMTw_run-4_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-mtw_T1w.nii.gz",
            "sub-MPN00002/ses-v2/anat/sub-MPN00002_ses-v2_acq-mtw_part-phase_T1w.nii.gz",
            "sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_T1w.nii.gz",
        ]

        for file_path in server_files:
            full_path = bids_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("dummy")

        # Use EXACT micapipe config
        config = {
            "pybids_inputs": {
                "t1w": {
                    "filters": {
                        "suffix": "T1w",
                        "extension": ".nii.gz",
                        "datatype": "anat",
                    },
                    "wildcards": ["subject", "session", "acq", "run", "part"],
                }
            },
            "snakenull": {"enabled": True},
        }

        print(f"Created {len(server_files)} server files")

        # Generate inputs
        result = generate_inputs_with_snakenull(
            bids_dir=str(bids_dir),
            pybids_inputs=config["pybids_inputs"],
            snakenull=config["snakenull"],
        )

        component = result["t1w"]
        real_filenames = {Path(f).name for f in server_files}

        print(f"\nReal files: {len(real_filenames)}")

        print(f"Generated combinations: {len(component.zip_lists['subject'])}")

        # Check for phantom combinations
        phantom_count = 0
        phantom_files = []

        for i in range(len(component.zip_lists["subject"])):
            combo = {
                "subject": component.zip_lists["subject"][i],
                "session": component.zip_lists["session"][i],
                "acq": component.zip_lists["acq"][i]
                if "acq" in component.zip_lists
                else "snakenull",
                "run": component.zip_lists["run"][i]
                if "run" in component.zip_lists
                else "snakenull",
                "part": component.zip_lists["part"][i]
                if "part" in component.zip_lists
                else "snakenull",
            }

            # Construct expected filename from combination
            filename_parts = [f"sub-{combo['subject']}", f"ses-{combo['session']}"]

            if combo["acq"] != "snakenull":
                filename_parts.append(f"acq-{combo['acq']}")
            if combo["run"] != "snakenull":
                filename_parts.append(f"run-{combo['run']}")
            if combo["part"] != "snakenull":
                filename_parts.append(f"part-{combo['part']}")

            filename_parts.append("T1w.nii.gz")
            expected_filename = "_".join(filename_parts)

            print(f"  Combo {i:2d}: {expected_filename}")

            if expected_filename not in real_filenames:
                phantom_count += 1
                phantom_files.append(expected_filename)
                print(f"    ❌ PHANTOM!")
            else:
                print(f"    ✅ REAL")

        print(f"\n=== RESULT ===")
        print(f"Real files: {len(real_filenames)}")
        print(f"Generated combinations: {len(component.zip_lists['subject'])}")
        print(f"Phantom combinations: {phantom_count}")

        if phantom_count > 0:
            print("\n🚨 BUG REPRODUCED!")
            print("First few phantom files:")
            for pf in phantom_files[:5]:
                print(f"  - {pf}")
            return False
        else:
            print("✅ No phantom combinations found!")
            return True


if __name__ == "__main__":
    success = test_exact_server_phantom_bug()
    sys.exit(0 if success else 1)
