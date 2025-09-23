#!/usr/bin/env python3
"""Debug the exact call pattern that micapipe uses."""

import sys
import os

sys.path.insert(0, "/Users/enningyang/CodeProj/snakebids")


def check_micapipe_integration():
    """Check how micapipe calls the plugin."""

    print("=== Checking snakebids installation paths ===")

    # Check if this version is being used
    import snakebids

    print(f"Snakebids location: {snakebids.__file__}")
    print(f"Snakebids version: {getattr(snakebids, '__version__', 'unknown')}")

    # Check the plugin
    try:
        from snakebids.plugins.snakenull import generate_inputs_with_snakenull

        print(f"Plugin location: {generate_inputs_with_snakenull.__module__}")
        print("Plugin imported successfully!")

        # Check if the plugin has our normalization code
        import inspect

        source = inspect.getsource(generate_inputs_with_snakenull)
        if "snakenull" in source and "_collect_files_manually" in source:
            print("✓ Plugin contains normalization code")
            print(f"  Found {source.count('snakenull')} snakenull references")
        else:
            print("✗ Plugin does NOT contain normalization code!")

    except ImportError as e:
        print(f"Plugin import failed: {e}")

    print("\n=== Checking where micapipe snakebids is installed ===")

    # This is the path from the error message
    micapipe_snakebids_path = "/home/bic/eyang/Documents/snakebids"
    print(f"Error points to: {micapipe_snakebids_path}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"This repo location: /Users/enningyang/CodeProj/snakebids")

    print(
        "\nThe issue is likely that micapipe is using a different snakebids installation!"
    )
    print("You need to:")
    print("1. Check what snakebids micapipe is actually using")
    print("2. Either update that installation or point micapipe to use this one")

    # Show how to check the version being used
    print("\n=== Commands to run on your server ===")
    print("cd /home/bic/eyang/Documents/micapipe/micapipe_snakebids")
    print('python -c "import snakebids; print(snakebids.__file__)"')
    print(
        "python -c \"from snakebids.plugins.snakenull import generate_inputs_with_snakenull; print('Plugin found')\""
    )


if __name__ == "__main__":
    check_micapipe_integration()
