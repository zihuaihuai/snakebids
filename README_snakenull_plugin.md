# Snakenull Plugin Integration Guide

## Understanding the Problem and Solution

### The Problem
When snakebids processes heterogeneous BIDS datasets, it discovers files and creates `zip_lists` containing entity combinations. However, if subjects have different sessions or runs, this creates incomplete combinations that can cause issues in snakemake workflows.

### The Solution: Post-Processing Plugin
The snakenull plugin hooks into snakebids **after** input discovery but **before** snakemake execution to normalize the inputs.

## How It Works

### 1. Plugin Hook Timing
```
snakebids app.run() lifecycle:
├── initialize_config     # Load config file
├── add_cli_arguments     # Add CLI args
├── finalize_config       # ← INPUT GENERATION HAPPENS HERE
│   ├── Standard plugins generate pybids_inputs
│   └── SnakenullPlugin normalizes the inputs ← OUR HOOK
└── run                   # Execute snakemake with normalized inputs
```

### 2. Integration with Your Existing Workflow

Your current `run.py` structure:
```python
app = snakebids.app(plugins=[SnakemakeBidsApp(...)])
app.run()
```

Updated with snakenull:
```python
from snakebids_snakenull_plugin import SnakenullPlugin

app = snakebids.app(plugins=[
    SnakemakeBidsApp(...),
    SnakenullPlugin(),  # ← Add this line
])
app.run()  # Snakenull now runs automatically
```

### 3. What the Plugin Does

1. **Waits for input generation**: The plugin hooks into `finalize_config`, which runs after snakebids discovers and processes all BIDS files.

2. **Normalizes zip_lists**: For each component in `pybids_inputs`, it:
   - Finds all unique combinations of entities (subject, session, run, etc.)
   - Ensures every possible combination is represented
   - Adds "SNAKENULL" for missing file paths

3. **Preserves existing behavior**: Files that exist are unchanged; only missing combinations get SNAKENULL placeholders.

## Example: Before and After

### Before (Original snakebids output):
```json
{
  "dwi": {
    "zip_lists": {
      "subject": ["01", "02", "01"],
      "session": ["01", "01", "02"],
      "run": ["1", "1", "1"],
      "path": [
        "/data/sub-01/ses-01/dwi/sub-01_ses-01_run-1_dwi.nii.gz",
        "/data/sub-02/ses-01/dwi/sub-02_ses-01_run-1_dwi.nii.gz",
        "/data/sub-01/ses-02/dwi/sub-01_ses-02_run-1_dwi.nii.gz"
      ]
    }
  }
}
```

### After (With snakenull plugin):
```json
{
  "dwi": {
    "zip_lists": {
      "subject": ["01", "01", "02", "02"],
      "session": ["01", "02", "01", "02"],
      "run": ["1", "1", "1", "1"],
      "path": [
        "/data/sub-01/ses-01/dwi/sub-01_ses-01_run-1_dwi.nii.gz",
        "/data/sub-01/ses-02/dwi/sub-01_ses-02_run-1_dwi.nii.gz",
        "/data/sub-02/ses-01/dwi/sub-02_ses-01_run-1_dwi.nii.gz",
        "SNAKENULL"  ← Missing sub-02/ses-02 combination
      ]
    }
  }
}
```

## Usage

### Basic Integration
```python
from pathlib import Path
import snakebids
from snakebids.plugins.snakemake import SnakemakeBidsApp
from snakebids_snakenull_plugin import SnakenullPlugin

def main():
    app = snakebids.app(
        plugins=[
            SnakemakeBidsApp(
                snakemake_dir=Path(__file__).parent.resolve(),
            ),
            SnakenullPlugin(),  # Enable snakenull normalization
        ]
    )
    app.run()

if __name__ == "__main__":
    main()
```

### CLI Options
The plugin adds CLI arguments:
```bash
# Disable snakenull (if you want original behavior)
python run.py --disable-snakenull [other args...]

# Explicitly enable snakenull (default anyway)
python run.py --enable-snakenull [other args...]
```

### Configuration
```python
# Disable by default
SnakenullPlugin(enable=False)

# Enable by default (default behavior)
SnakenullPlugin(enable=True)
```

## Testing

Run the test to see it in action:
```bash
python test_snakenull_plugin.py
```

This will show you:
- Original vs normalized inputs
- How many SNAKENULL entries were added
- All entity combinations that are represented

## Integration with Your Existing Workflow

To integrate with your current setup:

1. **Copy the plugin file**: Place `snakebids_snakenull_plugin.py` in your workflow directory

2. **Update your run.py**: Add the import and plugin to your existing code:
   ```python
   from snakebids_snakenull_plugin import SnakenullPlugin

   # In your app creation:
   app = snakebids.app(
       plugins=[
           # ... your existing plugins ...
           SnakenullPlugin(),  # Add this
       ]
   )
   ```

3. **Run normally**: Use your existing command structure - snakenull will be applied automatically

The beauty of this approach is that it requires **zero changes** to core snakebids code and works as a true post-processing step that runs at exactly the right time in the workflow lifecycle.
