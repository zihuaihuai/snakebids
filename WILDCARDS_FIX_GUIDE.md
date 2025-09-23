# Micapipe Wildcards Fix

The issue you're experiencing is that your Snakemake version doesn't support attribute access on `Wildcards` objects (e.g., `wildcards.subject`), while micapipe rules expect this functionality.

## Root Cause

The snakenull plugin now works correctly and creates proper `BidsComponent` objects. However, when Snakemake executes rules, it creates its own `Wildcards` objects from the component data, and older Snakemake versions don't support attribute access on these objects.

## Solution 1: Update Micapipe Rules (Recommended)

In your micapipe `workflow/rules/structural.smk`, modify the rule to handle both dict and attribute access:

```python
# At the top of the file, add this helper function:
def get_wildcard_value(wildcards, key):
    """Get wildcard value supporting both dict and attribute access."""
    if hasattr(wildcards, key):
        return getattr(wildcards, key)
    else:
        return wildcards[key]

# Then in your rule, replace:
# -sub sub-{wildcards.subject} -ses {wildcards.session}
# With:
# -sub sub-{get_wildcard_value(wildcards, 'subject')} -ses {get_wildcard_value(wildcards, 'session')}
```

Or use this more elegant approach:

```python
# At the top of the file:
class WildcardWrapper:
    def __init__(self, wildcards):
        self._wildcards = wildcards
    
    def __getattr__(self, name):
        if hasattr(self._wildcards, name):
            return getattr(self._wildcards, name)
        else:
            return self._wildcards[name]
    
    def __getitem__(self, key):
        return self._wildcards[key]

# Then in your rule:
rule proc_structural:
    run:
        w = WildcardWrapper(wildcards)
        command = f"-sub sub-{w.subject} -out {{output_args}} -bids {{bids_args}} -proc_structural -T1wStr {{params.T1wStr}} -mf {{params.MF}} {{params.UNI}} -ses {w.session} -threads {{threads}} -fs_licence {{fs_licence_args}}"
        # Use the command...
```

## Solution 2: Snakebids Plugin Enhancement (Advanced)

I can also add a compatibility layer in the snakebids plugin that monkey-patches Snakemake's wildcard handling, but this is more complex and potentially fragile.

## Quick Test

To verify this is the issue, try this in a Python shell on your server:

```python
from snakemake.io import Wildcards
w = Wildcards(fromdict={'subject': 'test', 'session': 'v1'})
print(w.subject)  # This will fail on older Snakemake versions
```

## Recommendation

Use Solution 1 to update your micapipe rules. This is the most robust approach and will work across all Snakemake versions. The snakenull plugin is now working correctly and creating proper `BidsComponent` objects with normalized entities.