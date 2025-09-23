#!/usr/bin/env python3
"""Simple test to understand the micapipe input structure."""

def mock_micapipe_inputs():
    """Mock the actual inputs from your micapipe run based on the error message."""
    
    # Based on your error output, this is what snakebids is seeing
    return {
        "t1w": {  # or whatever the component is called
            "filters": {"suffix": "T1w", "extension": [".nii.gz"]},
            "zip_lists": {
                "subject": ["MPN00002", "MPNphantom"],
                "session": ["v1", "v2"], 
                "acquisition": ["mtw", "neuromelaninMTw"],
                "run": ["1", "2"],
                "part": ["phase", "snakenull"],  # This looks wrong already
                "path": [
                    "/data/mica3/BIDS_MPN/rawdata_test/sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_acq-mtw_T1w.nii.gz",
                    "/data/mica3/BIDS_MPN/rawdata_test/sub-MPNphantom/ses-v2/anat/sub-MPNphantom_ses-v2_acq-neuromelaninMTw_run-2_T1w.nii.gz"
                ]
            }
        }
    }

if __name__ == "__main__":
    from snakebids.plugins.snakenull import apply_snakenull_to_inputs
    
    inputs = mock_micapipe_inputs()
    
    print("Original inputs:")
    for comp_name, comp_data in inputs.items():
        print(f"  {comp_name}:")
        for entity, values in comp_data["zip_lists"].items():
            print(f"    {entity}: {values}")
    print()
    
    print("Applying snakenull...")
    normalized = apply_snakenull_to_inputs(inputs)
    
    print("Normalized inputs:")
    for comp_name, comp_data in normalized.items():
        print(f"  {comp_name}:")
        for entity, values in comp_data["zip_lists"].items():
            print(f"    {entity}: {values}")
    print()
    
    print("Analysis:")
    t1w_zip = normalized["t1w"]["zip_lists"]
    print(f"Total combinations: {len(t1w_zip['subject'])}")
    null_count = sum(1 for p in t1w_zip["path"] if p == "SNAKENULL")
    print(f"SNAKENULL paths: {null_count}")
    
    print("\nPaths:")
    for i, path in enumerate(t1w_zip["path"]):
        entities = {k: v[i] for k, v in t1w_zip.items() if k != "path"}
        print(f"  {i+1}: {path}")
        print(f"      Entities: {entities}")