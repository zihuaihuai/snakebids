# Snakenull Plugin Integration Guide

## Quick Start

### 1. Installation
The snakenull plugin is now integrated into snakebids. Just reinstall:

```bash
cd /path/to/snakebids
pip install -e .
```

### 2. Using in Your Existing Project

**Option A: Simple Replacement**

Replace your existing `run.py` with this:

```python
#!/usr/bin/env python3
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
```

**Option B: Modify Existing run.py**

If you have a more complex `run.py`, just add the import and plugin:

```python
# Add this import
from snakebids.plugins import SnakenullPlugin

# Modify your app creation to include the plugin
app = bidsapp.app(
    [
        SnakemakeBidsApp(Path(__file__).resolve().parent),
        # ... your other plugins ...
        SnakenullPlugin(),  # Add this line
    ]
)
```

### 3. Run Your Workflow

Use your normal command:

```bash
python run.py /path/to/bids /path/to/output participant [other args...]
```

The snakenull normalization will be applied automatically after input discovery.

## CLI Options

The plugin adds these CLI arguments:

```bash
# Disable snakenull (if you want original behavior)
python run.py --disable-snakenull [other args...]

# Explicitly enable snakenull (default anyway)  
python run.py --enable-snakenull [other args...]
```

## What It Does

The plugin:

1. **Waits for snakebids input generation** - Hooks into `finalize_config` after standard input discovery
2. **Normalizes zip_lists** - Ensures all entity combinations are represented
3. **Adds SNAKENULL for missing files** - Missing combinations get "SNAKENULL" paths
4. **Preserves existing behavior** - Real files are unchanged

### Example Output

```
Applying snakenull normalization to inputs...
  dwi: 4 total combinations (1 normalized with SNAKENULL)
  func: 8 total combinations (2 normalized with SNAKENULL)
```

## Testing

### Test the Plugin Directly

```bash
python test_integrated_snakenull.py
```

### Test in Real Workflow

```bash
# Create a minimal test
python run.py --help  # Should show snakenull options

# Run with your actual data
python run.py /path/to/bids /path/to/output participant --enable-snakenull
```

## Advanced Configuration

```python
# Disable by default
SnakenullPlugin(enable=False)

# Enable by default (default)
SnakenullPlugin(enable=True)
```

## Files to Copy/Modify for Your Project

1. **Copy this `run.py`** to your project root:
   ```bash
   cp /Users/enningyang/CodeProj/snakebids/run.py /path/to/your/project/run.py
   ```

2. **Or modify your existing run.py** to add:
   ```python
   from snakebids.plugins import SnakenullPlugin
   
   # Add SnakenullPlugin() to your app plugins list
   ```

3. **Test it works**:
   ```bash
   cd /path/to/your/project
   python run.py --help  # Should show snakenull options
   ```

## Integration Notes

- ✅ **Zero changes to core snakebids code** - True plugin architecture
- ✅ **Runs at perfect timing** - After input discovery, before snakemake  
- ✅ **CLI configurable** - Can enable/disable as needed
- ✅ **Backward compatible** - Existing workflows unchanged unless plugin added
- ✅ **Package integrated** - Available after `pip install -e .`

The plugin is now a first-class part of snakebids and can be used in any project that installs the updated package.