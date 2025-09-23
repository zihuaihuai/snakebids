# Snakenull Plugin for Snakebids

## Overview

The snakenull plugin provides robust handling of heterogeneous BIDS datasets in Snakebids. When BIDS datasets have inconsistent entity patterns (e.g., some files have `run` entities while others don't), standard snakebids fails with "Multiple path templates" errors. This plugin automatically detects such cases and provides a workaround while maintaining full compatibility with existing micapipe code.

## Key Features

- **Automatic heterogeneous dataset detection**: Detects when standard snakebids fails due to inconsistent entity patterns
- **Opt-in design**: Disabled by default, must be explicitly enabled
- **Full micapipe compatibility**: Provides BidsComponent-compatible interface with `.expand()` and `.wildcards` methods
- **Robust entity extraction**: Handles various BIDS entity patterns including `acq`/`acquisition` mapping
- **Performance optimized**: Handles large datasets efficiently
- **Non-interfering**: Falls back to standard snakebids when possible

## Installation

The plugin is included in snakebids. No additional installation required.

## Usage

### 1. Basic Usage (replacing standard generate_inputs)

```python
# Instead of:
# from snakebids import generate_inputs

# Use:
from snakebids.plugins.snakenull import generate_inputs_with_snakenull

# In your run.py or Snakefile:
inputs = generate_inputs_with_snakenull(
    bids_dir=config["bids_dir"],
    pybids_inputs=config["pybids_inputs"],
    # ... other arguments same as generate_inputs
)
```

### 2. CLI Integration (for bidsapps)

Add the plugin to your bidsapp and enable via CLI:

```python
# In your run.py
from snakebids import bidsapp
from snakebids.plugins.snakenull import SnakenullPlugin

# Register the plugin
bidsapp.plugins.add(SnakenullPlugin())

# Run with --enable-snakenull flag
```

```bash
python run.py /data /output participant --enable-snakenull
```

### 3. Micapipe Integration

The plugin provides the exact interface micapipe expects:

```python
# Your existing micapipe code works unchanged:

# Wildcards access
subject = inputs['t1w'].wildcards['subject']
session = inputs['t1w'].wildcards['session']

# Expand operations
structural_outputs = inputs['t1w'].expand(
    get_structural_outputs(inputs, output_dir)
)

# Dictionary access
all_subjects = inputs['t1w']['subject']
all_paths = inputs['t1w']['path']
```

## How It Works

1. **Detection**: Tries standard `generate_inputs()` first
2. **Fallback**: If "Multiple path templates" error occurs, activates snakenull mode
3. **Manual collection**: Manually searches and parses BIDS files
4. **Entity extraction**: Uses regex patterns to extract entities from filenames and paths
5. **Wrapper creation**: Returns `BidsComponentWrapper` objects that provide BidsComponent-compatible interface
6. **Null handling**: Fills missing entities with "null" values for consistency

## Entity Mapping

The plugin handles various BIDS entity patterns:

- `sub-{subject}` or `sub{subject}` → `subject`
- `ses-{session}` or `ses{session}` → `session`
- `acq-{acquisition}` → `acquisition` (maps `acq-` pattern to `acquisition` wildcard)
- `run-{run}` → `run`
- `task-{task}` → `task`
- Missing entities → `"null"`

## Configuration

### Snakebids Config (snakebids.yml)

```yaml
pybids_inputs:
  t1w:
    filters:
      suffix: T1w
      extension: .nii.gz
      datatype: anat
    wildcards:
      - subject
      - session
      - acquisition  # Use 'acquisition' - plugin maps from 'acq-' patterns
      - run
```

### Example Micapipe Integration

```python
# run.py
from snakebids.plugins.snakenull import generate_inputs_with_snakenull

def main():
    # Load config
    config = load_config()

    # Generate inputs with snakenull support
    inputs = generate_inputs_with_snakenull(
        bids_dir=config["bids_dir"],
        pybids_inputs=config["pybids_inputs"],
        derivatives=config.get("derivatives", False),
        participant_label=config.get("participant_label"),
        exclude_participant_label=config.get("exclude_participant_label"),
    )

    # Rest of your code unchanged
    # ...
```

## Debugging

The plugin provides detailed logging when activated:

```
[snakenull] Detected heterogeneous dataset, applying workaround...
[snakenull] Original error: Multiple path templates for one component...
[snakenull] Processing component: t1w
[snakenull] Component t1w has heterogeneous patterns, applying manual collection...
[snakenull] BidsComponent creation failed, using BidsComponentWrapper for t1w
[snakenull] Manual collection succeeded for t1w
[snakenull] Final results summary:
  t1w: 6 files
    subject: ['MPNphantom', 'MPNphantom', 'MPN00003']
    session: ['v2', 'v1', 'v2']
    acquisition: ['neuromelaninMTw', 'mtw', 'mprage']
    run: ['01', 'null', 'null']
```

## Testing

The plugin includes comprehensive tests:

```bash
# Run plugin tests
poetry run poe test snakebids/tests/test_plugins/test_snakenull.py

# Run comprehensive integration tests
python comprehensive_test.py
python final_integration_test.py
```

## Performance

- **Small datasets**: Minimal overhead
- **Large datasets**: Optimized entity extraction and file processing
- **Memory usage**: Efficient dictionary storage instead of heavy BidsComponent objects
- **Speed**: Manual collection is faster than pybids for heterogeneous datasets

## Limitations

- Only activated when standard snakebids fails
- Requires heterogeneous datasets to trigger (single homogeneous datasets use standard snakebids)
- Some BIDS validation may be bypassed during manual collection
- Complex custom entity patterns may need manual regex updates

## Migration Guide

### From Standard Snakebids

1. Replace `generate_inputs` import:
```python
# Before
from snakebids import generate_inputs

# After
from snakebids.plugins.snakenull import generate_inputs_with_snakenull as generate_inputs
```

2. No other code changes needed!

### From Manual Snakenull Handling

If you were manually handling heterogeneous datasets:

1. Remove manual workarounds
2. Use `generate_inputs_with_snakenull`
3. Keep existing `.expand()` and `.wildcards` usage

## Support

- **Issues**: File issues on the snakebids repository
- **Documentation**: See snakebids documentation
- **Testing**: Comprehensive test suite included

## Example Datasets Supported

- **Micapipe datasets**: T1w with mixed acquisition patterns
- **Multi-modal studies**: Different run patterns across modalities
- **Longitudinal studies**: Inconsistent entity patterns over time
- **Multi-site studies**: Different acquisition protocols

The plugin ensures your workflows run reliably regardless of BIDS dataset heterogeneity!
