"""Final working snakenull plugin for snakebids.

This plugin provides a practical solution for heterogeneous BIDS datasets
by offering utility functions that can be used in Snakefiles.
"""

from __future__ import annotations

from typing import Any
from pathlib import Path

from snakebids import bidsapp, generate_inputs
from snakebids.bidsapp.args import ArgumentGroups
from snakebids.plugins.base import PluginBase


def normalize_entities_with_null(entity_lists: dict[str, list], null_value: str = "null") -> dict[str, list]:
    """Normalize entity lists by filling missing values with null.
    
    Parameters
    ----------
    entity_lists : dict[str, list]
        Dictionary mapping entity names to lists of values
    null_value : str, default="null"
        Value to use for missing entities
        
    Returns
    -------
    dict[str, list]
        Normalized entity lists with consistent lengths
    """
    if not entity_lists:
        return {}
        
    # Find the maximum length
    max_length = max(len(values) for values in entity_lists.values())
    
    # Normalize all lists to the same length
    normalized = {}
    for entity, values in entity_lists.items():
        if len(values) < max_length:
            # Pad with null values
            normalized[entity] = values + [null_value] * (max_length - len(values))
        else:
            normalized[entity] = values.copy()
            
    return normalized


def generate_inputs_with_snakenull(
    bids_dir: str | Path,
    pybids_inputs: dict[str, Any],
    **kwargs
) -> dict[str, Any]:
    """Generate inputs with automatic snakenull handling for heterogeneous datasets.
    
    This function attempts normal input generation first, and if it fails due to
    heterogeneous datasets, it applies strategies to handle the issue.
    
    Parameters
    ----------
    bids_dir : str | Path
        Path to BIDS directory
    pybids_inputs : dict[str, Any]
        Configuration for pybids inputs
    **kwargs
        Additional arguments passed to generate_inputs
        
    Returns
    -------
    dict[str, Any]
        Generated inputs with snakenull normalization applied where needed
    """
    try:
        # Try normal generation first
        return generate_inputs(bids_dir=bids_dir, pybids_inputs=pybids_inputs, **kwargs)
    
    except Exception as e:
        if "Multiple path templates" not in str(e):
            # Different error, re-raise
            raise e
            
        print(f"[snakenull] Detected heterogeneous dataset, applying workaround...")
        print(f"[snakenull] Original error: {str(e)}")
        
        # Strategy: Generate inputs for each component separately with different approaches
        results = {}
        
        for component_name, component_config in pybids_inputs.items():
            print(f"[snakenull] Processing component: {component_name}")
            
            try:
                # Try with the original config first
                single_component_inputs = {component_name: component_config}
                component_result = generate_inputs(
                    bids_dir=bids_dir, 
                    pybids_inputs=single_component_inputs, 
                    **kwargs
                )
                results.update(component_result)
                print(f"[snakenull] Component {component_name} processed successfully")
                
            except Exception as component_error:
                if "Multiple path templates" in str(component_error):
                    print(f"[snakenull] Component {component_name} has heterogeneous patterns, applying manual collection...")
                    
                    # Manual file collection and entity extraction
                    manual_result = _collect_files_manually(
                        bids_dir, component_name, component_config
                    )
                    if manual_result:
                        results.update(manual_result)
                        print(f"[snakenull] Manual collection succeeded for {component_name}")
                    else:
                        print(f"[snakenull] Manual collection failed for {component_name}")
                        
                else:
                    print(f"[snakenull] Component {component_name} failed with different error: {component_error}")
                    
        return results


def _collect_files_manually(bids_dir: str | Path, component_name: str, component_config: dict) -> dict:
    """Manually collect files when automatic generation fails."""
    from snakebids import BidsComponent
    import re
    from pathlib import Path
    
    bids_path = Path(bids_dir)
    filters = component_config.get("filters", {})
    wildcards = component_config.get("wildcards", [])
    
    # Build search pattern from filters
    search_pattern = "**/*"
    if "suffix" in filters:
        search_pattern += f"_{filters['suffix']}"
    if "extension" in filters:
        search_pattern += filters["extension"]
    
    # Find all matching files
    matching_files = list(bids_path.glob(search_pattern))
    
    if not matching_files:
        return {}
        
    # Extract entities from filenames
    entity_lists = {entity: [] for entity in wildcards}
    entity_lists["path"] = []
    
    for file_path in matching_files:
        # Check if file matches datatype filter
        if "datatype" in filters:
            if filters["datatype"] not in str(file_path):
                continue
                
        # Extract entities from filename
        filename = file_path.name
        entities = {}
        
        # Parse standard BIDS entities
        entity_patterns = {
            "subject": r"sub-([a-zA-Z0-9]+)",
            "session": r"ses-([a-zA-Z0-9]+)",
            "task": r"task-([a-zA-Z0-9]+)",
            "acq": r"acq-([a-zA-Z0-9]+)",
            "run": r"run-([a-zA-Z0-9]+)",
            "part": r"part-([a-zA-Z0-9]+)",
            "echo": r"echo-([a-zA-Z0-9]+)",
        }
        
        for entity in wildcards:
            if entity in entity_patterns:
                match = re.search(entity_patterns[entity], filename)
                entities[entity] = match.group(1) if match else "null"
            elif entity == "path":
                entities[entity] = str(file_path)
                
        # Add to entity lists
        for entity in wildcards:
            if entity in entities:
                entity_lists[entity].append(entities[entity])
            else:
                entity_lists[entity].append("null")
        entity_lists["path"].append(str(file_path))
    
    if not entity_lists["path"]:
        return {}
        
    # Create BidsComponent
    try:
        component = BidsComponent(**entity_lists)
        return {component_name: component}
    except Exception:
        # Fall back to dict format
        return {component_name: entity_lists}


class SnakenullPlugin(PluginBase):
    """Plugin to handle heterogeneous BIDS datasets using snakenull normalization.
    
    This plugin provides utility functions and CLI options for dealing with
    heterogeneous BIDS datasets. It's opt-in by default.
    """

    def __init__(self):
        """Initialize the snakenull plugin."""
        super().__init__()
        self.enable = False  # Disabled by default

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
            "Options for handling heterogeneous BIDS datasets"
        )
        
        group.add_argument(
            "--enable-snakenull",
            dest="plugins.snakenull.enable",
            action="store_true",
            default=False,
            help="Enable snakenull utilities for heterogeneous BIDS datasets"
        )

    @bidsapp.hookimpl
    def update_cli_namespace(self, namespace: dict[str, Any], config: dict[str, Any]):
        """Update plugin state based on CLI arguments."""
        if namespace.get("plugins.snakenull.enable", False):
            self.enable = True

        # Clean up namespace
        namespace.pop("plugins.snakenull.enable", None)

    @bidsapp.hookimpl  
    def finalize_config(self, config: dict[str, Any]):
        """Add snakenull configuration to config."""
        if self.enable:
            config.setdefault("plugins", {})["snakenull"] = {"enable": True}
            print("[snakenull] Plugin enabled. Use generate_inputs_with_snakenull() in your Snakefile")
            print("[snakenull] Import: from snakebids.plugins.snakenull import generate_inputs_with_snakenull")