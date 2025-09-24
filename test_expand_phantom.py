#!/usr/bin/env python3
"""Test the expand functionality to see if it generates phantom combinations."""

import sys
import tempfile
from pathlib import Path

from snakebids.plugins.snakenull import (
    generate_inputs_with_snakenull,  # type: ignore[reportUnknownVariableType]
)


def test_expand_phantom_bug():
    """Test if the expand method generates phantom combinations."""
    print("=== Testing Expand Method Phantom Bug ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        bids_dir = Path(tmpdir) / "bids"

        # Create specific files to test expansion
        server_files = [
            # File WITHOUT part entity
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-2_T1w.nii.gz",
            # File WITH part entity  
            "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_part-phase_T1w.nii.gz",
        ]

        for file_path in server_files:
            full_path = bids_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("dummy")

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

        # Generate inputs
        result = generate_inputs_with_snakenull(
            bids_dir=str(bids_dir),
            pybids_inputs=config["pybids_inputs"],
            snakenull=config["snakenull"],
        )

        component = result["t1w"]
        
        print(f"zip_lists: {component.zip_lists}")
        print(f"Component path template: {component.path}")
        
        # Test what happens when we call expand like micapipe does
        print(f"\n=== Testing Expand Method ===")
        
        # This simulates micapipe's usage pattern
        # Create a template function that only uses entities present in the component
        def mock_structural_outputs_func(wildcards, output_dir):
            # Only use entities that are actually present in the component
            component_entities = set(component.zip_lists.keys())
            if 'part' in component_entities:
                return output_dir + "/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_acq-{acq}_run-{run}_part-{part}_space-nativepro_T1w.nii.gz"
            else:
                return output_dir + "/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_acq-{acq}_run-{run}_space-nativepro_T1w.nii.gz"
        
        # Test expand method
        output_dir = "/test/output"
        template = mock_structural_outputs_func({}, output_dir)
        print(f"Template: {template}")
        
        expanded = component.expand(template)
        print(f"Expanded paths ({len(expanded)}):")
        
        real_filenames = {Path(f).name.replace('_T1w.nii.gz', '') for f in server_files}
        print(f"Real file prefixes: {real_filenames}")
        
        phantom_count = 0
        for i, path in enumerate(expanded):
            filename = Path(path).name
            # Extract the core part before _space-nativepro
            core_part = filename.split('_space-nativepro')[0]
            print(f"  {i}: {filename}")
            print(f"     Core: {core_part}")
            
            # Check if this core part corresponds to a real file
            real_match = False
            for real_prefix in real_filenames:
                if real_prefix in core_part:
                    real_match = True
                    break
                    
            if not real_match:
                phantom_count += 1
                print(f"     ❌ PHANTOM!")
            else:
                print(f"     ✅ REAL")
        
        print(f"\n=== RESULT ===")
        print(f"Expanded paths: {len(expanded)}")
        print(f"Phantom expansions: {phantom_count}")
        
        if phantom_count > 0:
            print("🚨 EXPAND METHOD BUG REPRODUCED!")
            return False
        else:
            print("✅ Expand method works correctly!")
            return True


if __name__ == "__main__":
    success = test_expand_phantom_bug()
    sys.exit(0 if success else 1)