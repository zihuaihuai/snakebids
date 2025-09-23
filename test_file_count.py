#!/usr/bin/env python3

"""Test the final fix with proper file count reporting."""

from pathlib import Path
from snakebids.plugins.snakenull import generate_inputs_with_snakenull

def test_final_fix():
    print("=== TEST FINAL FIX ===")
    
    # Create test directory 
    test_dir = Path("test_file_count_fix")
    test_dir.mkdir(exist_ok=True)
    
    # Create files
    sample_files = [
        "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-neuromelaninMTw_run-2_part-snakenull_T1w.nii.gz",
        "sub-MPNphantom/ses-v1/anat/sub-MPNphantom_ses-v1_acq-mtw_run-snakenull_part-snakenull_T1w.nii.gz", 
        "sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_acq-snakenull_run-snakenull_part-snakenull_T1w.nii.gz",
    ]
    
    for file_path in sample_files:
        full_path = test_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()
    
    print(f"Created {len(sample_files)} test files")
    
    # Test with snakenull enabled
    pybids_inputs = {
        "t1w": {
            "filters": {
                "suffix": "T1w",
                "extension": ".nii.gz",
                "datatype": "anat"
            },
            "wildcards": ["subject", "session", "acq", "run", "part"]
        }
    }
    
    kwargs = {
        "snakenull": {"enabled": True}
    }
    
    # This should now correctly report the number of files
    results = generate_inputs_with_snakenull(
        bids_dir=test_dir,
        pybids_inputs=pybids_inputs,
        **kwargs
    )
    
    # Check if the file count is now correct
    if "t1w" in results:
        component = results["t1w"]
        if hasattr(component, 'zip_lists'):
            zip_lists = component.zip_lists
            actual_file_count = len(list(zip_lists.values())[0]) if zip_lists else 0
            print(f"\nVerification: BidsComponent has {actual_file_count} files in zip_lists")
            
            if actual_file_count == len(sample_files):
                print(f"✅ SUCCESS: File count is correct!")
            else:
                print(f"❌ File count mismatch: expected {len(sample_files)}, got {actual_file_count}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    test_final_fix()