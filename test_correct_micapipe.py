#!/usr/bin/env python3
"""Test to understand the correct structure for micapipe inputs."""

def correct_micapipe_inputs():
    """What the inputs SHOULD look like based on actual files."""
    
    return {
        "t1w": {
            "filters": {"suffix": "T1w", "extension": [".nii.gz"]},
            "zip_lists": {
                "subject": ["MPN00002", "MPNphantom"],
                "session": ["v1", "v2"], 
                "acquisition": ["mtw", "neuromelaninMTw"],
                "run": [None, "2"],  # Only the second file has run
                # No "part" entity - doesn't exist in these files
                "path": [
                    "/data/mica3/BIDS_MPN/rawdata_test/sub-MPN00002/ses-v1/anat/sub-MPN00002_ses-v1_acq-mtw_T1w.nii.gz",
                    "/data/mica3/BIDS_MPN/rawdata_test/sub-MPNphantom/ses-v2/anat/sub-MPNphantom_ses-v2_acq-neuromelaninMTw_run-2_T1w.nii.gz"
                ]
            }
        }
    }

if __name__ == "__main__":
    from snakebids.plugins.snakenull import apply_snakenull_to_inputs
    
    inputs = correct_micapipe_inputs()
    
    print("Correct input structure:")
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