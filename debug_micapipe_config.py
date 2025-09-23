#!/usr/bin/env python
"""Test script to debug micapipe workflow config structure."""

import sys
import subprocess
import json
from pathlib import Path

def run_micapipe_debug():
    """Run micapipe with debug to capture config structure."""
    
    # Temporary patch to capture config
    debug_script = '''
import snakebids
import json
import sys

# Monkey patch to capture config
original_finalize_config = snakebids.app.finalize_config

def debug_finalize_config(config):
    print("=== DEBUG CONFIG STRUCTURE ===")
    print("Config keys:", list(config.keys()))
    
    # Check for different input structures
    for key in ["pybids_inputs", "inputs", "input_lists", "bids_inputs"]:
        if key in config:
            print(f"\\nFound {key}:")
            data = config[key]
            if isinstance(data, dict):
                for comp_name, comp_data in data.items():
                    print(f"  {comp_name}: {type(comp_data)}")
                    if isinstance(comp_data, dict):
                        print(f"    Keys: {list(comp_data.keys())}")
                        if "zip_lists" in comp_data:
                            zip_lists = comp_data["zip_lists"]
                            print(f"    zip_lists keys: {list(zip_lists.keys())}")
                            for entity, values in zip_lists.items():
                                print(f"      {entity}: {values[:3]}{'...' if len(values) > 3 else ''}")
    
    print("=== END DEBUG ===")
    return original_finalize_config(config)

snakebids.app.finalize_config = debug_finalize_config

# Continue with normal app
if __name__ == "__main__":
    import snakebids.app
    snakebids.app.main()
'''
    
    # Write debug script
    with open("debug_micapipe.py", "w") as f:
        f.write(debug_script)
    
    # Run with debug
    cmd = [
        sys.executable, "debug_micapipe.py", 
        "run.py",
        "/data/mica3/BIDS_MPN/rawdata_test/", 
        "test-MPN", 
        "participant", 
        "--module", "structural",
        "-np",  # no actual processing
        "--dry-run"  # Don't actually run
    ]
    
    print("Running micapipe debug...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")  
        print(result.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running debug: {e}")
        return 1

if __name__ == "__main__":
    run_micapipe_debug()