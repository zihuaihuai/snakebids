"""Snakenull plugin for snakebids - handles heterogeneous BIDS datasets.

This plugin provides functionality to normalize BIDS entity lists when dealing
with heterogeneous datasets where some files have different entity patterns.
"""

from __future__ import annotations

from typing import Any

from snakebids import bidsapp
from snakebids.bidsapp.args import ArgumentGroups
from snakebids.plugins.base import PluginBase


def snakenull_generate_inputs(*args, **kwargs):
    """Wrapper for generate_inputs that applies snakenull normalization.
    
    This function can be used as a drop-in replacement for snakebids.generate_inputs
    when dealing with heterogeneous BIDS datasets.
    """
    # Import here to avoid circular imports
    from snakebids import generate_inputs
    
    try:
        # Try normal generation first
        inputs = generate_inputs(*args, **kwargs)
        return inputs
    except Exception as e:
        if "Multiple path templates" in str(e):
            print("[snakenull] Detected heterogeneous dataset, applying normalization...")
            
            # Apply snakenull strategy: use a more permissive approach
            kwargs_modified = kwargs.copy()
            
            # If pybids_inputs is in kwargs, modify it to be more permissive
            if "pybids_inputs" in kwargs_modified:
                pybids_inputs = kwargs_modified["pybids_inputs"].copy()
                original_components = list(pybids_inputs.items())  # Create a list to avoid iteration issues
                
                for component_name, component_config in original_components:
                    if isinstance(component_config, dict) and "wildcards" in component_config:
                        wildcards = component_config["wildcards"]
                        
                        # Create separate components for different entity patterns
                        # This is a more aggressive approach that handles heterogeneity
                        base_filters = component_config.get("filters", {}).copy()
                        
                        # Remove the problematic component and add split versions
                        component_configs = []
                        
                        # Pattern 1: Files without run/part
                        config_no_optional = component_config.copy()
                        config_no_optional["wildcards"] = [w for w in wildcards if w not in ["run", "part"]]
                        component_configs.append((f"{component_name}_no_optional", config_no_optional))
                        
                        # Pattern 2: Files with run but no part
                        config_with_run = component_config.copy()
                        config_with_run["wildcards"] = [w for w in wildcards if w != "part"]
                        filters_with_run = base_filters.copy()
                        # This is challenging - we need run to be present
                        component_configs.append((f"{component_name}_with_run", config_with_run))
                        
                        # Pattern 3: Files with all entities
                        config_full = component_config.copy()
                        component_configs.append((f"{component_name}_full", config_full))
                        
                        # Remove original component and add split versions
                        del pybids_inputs[component_name]
                        for new_name, new_config in component_configs:
                            pybids_inputs[new_name] = new_config
                
                kwargs_modified["pybids_inputs"] = pybids_inputs
                
                try:
                    # Try with modified config
                    inputs = generate_inputs(*args, **kwargs_modified)
                    
                    # Merge the split components back together with normalization
                    merged_inputs = merge_and_normalize_components(inputs)
                    return merged_inputs
                    
                except Exception as e2:
                    print(f"[snakenull] Modified generation also failed: {e2}")
                    # Fall back to original error
                    raise e
            else:
                # No pybids_inputs to modify, re-raise original error
                raise e
        else:
            # Different error, re-raise
            raise e


def merge_and_normalize_components(inputs):
    """Merge split components and apply snakenull normalization."""
    from snakebids import BidsDataset, BidsComponent
    
    merged = BidsDataset()
    component_groups = {}
    
    # Group split components back together
    for component_name, component_data in inputs.items():
        if "_no_optional" in component_name:
            base_name = component_name.replace("_no_optional", "")
        elif "_with_run" in component_name:
            base_name = component_name.replace("_with_run", "")
        elif "_full" in component_name:
            base_name = component_name.replace("_full", "")
        else:
            base_name = component_name
            
        if base_name not in component_groups:
            component_groups[base_name] = []
        component_groups[base_name].append((component_name, component_data))
    
    # Merge and normalize each group
    for base_name, components in component_groups.items():
        if len(components) == 1:
            # Single component, just rename
            _, component_data = components[0]
            merged[base_name] = component_data
        else:
            # Multiple components, need to merge with normalization
            merged_component = merge_components_with_snakenull(components)
            merged[base_name] = merged_component
    
    return merged


def merge_components_with_snakenull(components):
    """Merge multiple BidsComponents and apply snakenull normalization."""
    from snakebids import BidsComponent
    
    # Collect all entities from all components
    all_entities = {}
    all_paths = []
    
    # Get union of all entity names
    entity_names = set()
    for _, component in components:
        if hasattr(component, 'entities'):
            entity_names.update(component.entities.keys())
        elif isinstance(component, dict):
            entity_names.update(component.keys())
    
    # Initialize entity lists
    for entity in entity_names:
        all_entities[entity] = []
    
    # Collect data from all components
    for _, component in components:
        if hasattr(component, 'entities'):
            # BidsComponent object
            component_entities = component.entities
            paths = getattr(component, 'path', [])
        elif isinstance(component, dict):
            # Dict format
            component_entities = {k: v for k, v in component.items() if k != 'path'}
            paths = component.get('path', [])
        else:
            continue
            
        all_paths.extend(paths)
        
        # Add entity values, using 'null' for missing entities
        num_files = len(paths)
        for entity in entity_names:
            if entity in component_entities:
                all_entities[entity].extend(component_entities[entity])
            else:
                # Missing entity - fill with 'null'
                all_entities[entity].extend(['null'] * num_files)
    
    # Add path
    all_entities['path'] = all_paths
    
    # Create new BidsComponent with normalized entities
    try:
        return BidsComponent(**all_entities)
    except Exception:
        # Fall back to dict format
        return all_entities


class SnakenullPlugin(PluginBase):
    """Plugin to handle heterogeneous BIDS datasets using snakenull normalization.
    
    This plugin provides snakenull normalization to handle cases where BIDS files
    have different entity patterns (e.g., some files have 'run' entity, others don't).
    
    The plugin is opt-in by default and only activates when explicitly enabled.
    """

    def __init__(self):
        """Initialize the snakenull plugin."""
        super().__init__()
        self.enable = False  # Disabled by default (opt-in)

    @bidsapp.hookimpl
    def add_cli_arguments(
        self,
        parser,
        config: dict[str, Any],
        argument_groups: ArgumentGroups,
    ):
        """Add snakenull-specific CLI arguments."""
        group = argument_groups.get_or_create_group(
            "snakenull",
            "Options for snakenull heterogeneous dataset handling"
        )
        
        group.add_argument(
            "--enable-snakenull",
            dest="plugins.snakenull.enable",
            action="store_true",
            default=False,
            help="Enable snakenull normalization for heterogeneous BIDS datasets"
        )
        
        group.add_argument(
            "--snakenull-null-value",
            dest="plugins.snakenull.null_value", 
            default="null",
            help="Value to use for missing BIDS entities (default: null)"
        )

    @bidsapp.hookimpl
    def update_cli_namespace(self, namespace: dict[str, Any], config: dict[str, Any]):
        """Update the plugin state based on CLI arguments."""
        if namespace.get("plugins.snakenull.enable", False):
            self.enable = True
            print("[snakenull] Plugin enabled via --enable-snakenull")

        # Store null value setting
        self.null_value = namespace.get("plugins.snakenull.null_value", "null")

        # Remove from namespace to avoid conflicts
        namespace.pop("plugins.snakenull.enable", None)
        namespace.pop("plugins.snakenull.null_value", None)

    @bidsapp.hookimpl
    def finalize_config(self, config: dict[str, Any]):
        """Add snakenull configuration to the config."""
        if not self.enable:
            return
            
        # Add plugin configuration
        if "plugins" not in config:
            config["plugins"] = {}
        config["plugins"]["snakenull"] = {
            "enable": True,
            "null_value": getattr(self, "null_value", "null")
        }
        
        print(f"[snakenull] Plugin enabled with null_value='{self.null_value}'")
        print("[snakenull] Use snakenull_generate_inputs() instead of generate_inputs() in your Snakefile")
        print("[snakenull] Or import: from snakebids.plugins.snakenull import snakenull_generate_inputs as generate_inputs")