#!/usr/bin/env python3
"""Example integration of snakenull plugin with existing snakebids workflow.

This shows how to modify your existing run.py to include the snakenull plugin.
"""

from pathlib import Path
import snakebids
from snakebids.plugins.snakemake import SnakemakeBidsApp

# Import the snakenull plugin
from snakebids_snakenull_plugin import SnakenullPlugin


def get_parser():
    """Build parser object"""
    return snakebids.generate_parser(
        "snakebids_app",
        "0.1.0",
        plugins=[
            # Standard snakebids plugins
            SnakemakeBidsApp(
                snakemake_dir=Path(__file__).parent.resolve(),
                plugins=None,
            ),
            # Add the snakenull plugin
            SnakenullPlugin(),
        ],
    )


def main():
    """Run the snakebids app with snakenull plugin."""
    # Create the app with snakenull plugin included
    app = snakebids.app(
        plugins=[
            SnakemakeBidsApp(
                snakemake_dir=Path(__file__).parent.resolve(),
            ),
            # Add snakenull plugin - it will run in finalize_config
            SnakenullPlugin(),
        ]
    )
    
    # Run the app - snakenull will be applied automatically
    app.run()


if __name__ == "__main__":
    main()