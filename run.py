#!/usr/bin/env python3
"""Snakebids app with snakenull plugin.

This is a minimal modification to add snakenull normalization to your
existing snakebids workflow. Just replace your existing run.py with this file.
"""

from pathlib import Path
from snakebids import bidsapp
from snakebids.plugins import SnakemakeBidsApp, SnakenullPlugin

app = bidsapp.app(
    [
        SnakemakeBidsApp(Path(__file__).resolve().parent),
        SnakenullPlugin(),  # Add snakenull normalization
    ]
)

if __name__ == "__main__":
    app.run()
