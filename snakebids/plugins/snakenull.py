"""Final working snakenull plugin for snakebids.

This plugin provides a practical solution for heterogeneous BIDS datasets
by offering utility functions that can be used in Snakefiles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from snakebids import bidsapp, generate_inputs
from snakebids.bidsapp.args import ArgumentGroups
from snakebids.plugins.base import PluginBase


class BidsComponentWrapper:
    """A wrapper that makes dictionary data look like a BidsComponent.

    This provides compatibility with existing code that expects BidsComponent
    methods like .expand() and .wildcards.
    """

    def __init__(self, entity_dict: dict[str, list[str]]):
        """Initialize with entity dictionary."""
        self._entities = entity_dict.copy()

    @property
    def entities(self) -> dict[str, list[str]]:
        """Return the entities dictionary."""
        return self._entities

    @property
    def wildcards(self) -> dict[str, Any]:
        """Return wildcards in the format expected by micapipe code.

        This returns the entities for the first file, which is what
        the micapipe code expects when accessing inputs['t1w'].wildcards.
        """
        if (
            not self._entities
            or "path" not in self._entities
            or not self._entities["path"]
        ):
            return {}

        # Return wildcards for the first file
        wildcards = {}
        for entity, values in self._entities.items():
            if entity != "path" and values:
                wildcards[entity] = values[0]
        return wildcards

    def expand(self, template_func_result=None):
        """Expand templates using the entity data.

        This method is called by micapipe rules like:
        inputs['t1w'].expand(get_structural_outputs(inputs, output_dir))

        It returns a list of the expanded results for each file.
        """
        if template_func_result is None:
            return []

        if isinstance(template_func_result, str):
            # Single template string - expand it for each set of entities
            return self._expand_template_string(template_func_result)
        elif isinstance(template_func_result, list):
            # List of templates - expand each one
            results = []
            for template in template_func_result:
                if isinstance(template, str):
                    results.extend(self._expand_template_string(template))
                else:
                    # For each file, add this non-string result
                    num_files = len(self._entities.get("path", []))
                    results.extend([template] * num_files)
            return results
        else:
            # Return as-is for other types, repeated for each file
            num_files = len(self._entities.get("path", []))
            return [template_func_result] * num_files

    def _expand_template_string(self, template: str) -> list[str]:
        """Expand a template string for each set of entities."""
        if not self._entities or "path" not in self._entities:
            return []

        results = []
        num_files = len(self._entities["path"])

        for i in range(num_files):
            # Get entities for this file index
            file_entities = {}
            for entity, values in self._entities.items():
                if entity != "path" and i < len(values):
                    file_entities[entity] = values[i]

            # Format the template
            try:
                formatted = template.format(**file_entities)
                results.append(formatted)
            except KeyError as e:
                # If template needs entities we don't have, skip
                print(f"[snakenull] Warning: Template needs entity {e} not available")
                continue

        return results

    def __getitem__(self, key):
        """Allow dictionary-style access to entities."""
        return self._entities[key]

    def __contains__(self, key):
        """Check if entity exists."""
        return key in self._entities

    def get(self, key, default=None):
        """Get entity with default."""
        return self._entities.get(key, default)


def normalize_entities_with_null(
    entity_lists: dict[str, list], null_value: str = "null"
) -> dict[str, list]:
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
    bids_dir: str | Path, pybids_inputs: dict[str, Any], **kwargs
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

    # Check if snakenull is enabled in config
    snakenull_config = kwargs.get("snakenull", {})
    if not snakenull_config.get("enabled", False):
        # Snakenull disabled, use normal generation
        return generate_inputs(bids_dir=bids_dir, pybids_inputs=pybids_inputs, **kwargs)

    print("[snakenull] Snakenull enabled, checking for heterogeneous datasets...")

    # Strategy: Always use manual collection when snakenull is enabled
    # This ensures we find ALL files, not just those matching a single template
    results = {}

    for component_name, component_config in pybids_inputs.items():
        print(f"[snakenull] Processing component: {component_name}")

        # Use manual collection to ensure we get all files
        manual_result = _collect_files_manually(
            bids_dir, component_name, component_config
        )
        if manual_result:
            results.update(manual_result)
            print(f"[snakenull] Manual collection succeeded for {component_name}")
        else:
            print(f"[snakenull] Manual collection failed for {component_name}")

            # Fall back to normal generation for this component
            try:
                single_component_inputs = {component_name: component_config}
                component_result = generate_inputs(
                    bids_dir=bids_dir, pybids_inputs=single_component_inputs, **kwargs
                )
                results.update(component_result)
                print(f"[snakenull] Fallback succeeded for {component_name}")
            except Exception as fallback_error:
                print(
                    f"[snakenull] Fallback also failed for {component_name}: {fallback_error}"
                )

    print(f"[snakenull] Final results summary:")
    for comp_name, comp_data in results.items():
        if isinstance(comp_data, dict):
            entities = comp_data
        elif hasattr(comp_data, "entities"):
            entities = comp_data.entities
        else:
            entities = {}

        print(f"  {comp_name}: {len(entities.get('path', []))} files")
        for entity, values in entities.items():
            if entity != "path":
                print(f"    {entity}: {values}")

    return results


def _collect_files_manually(
    bids_dir: str | Path, component_name: str, component_config: dict
) -> dict:
    """Manually collect files when automatic generation fails."""
    import re
    from pathlib import Path

    from snakebids import BidsComponent

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

        # Parse standard BIDS entities with robust patterns
        entity_patterns = {
            "subject": r"sub-([a-zA-Z0-9]+)",
            "session": r"ses-([a-zA-Z0-9]+)",
            "task": r"task-([a-zA-Z0-9]+)",
            "acq": r"acq-([a-zA-Z0-9]+)",
            "acquisition": r"acq-([a-zA-Z0-9]+)",  # Map acquisition to acq- pattern
            "run": r"run-([a-zA-Z0-9]+)",
            "part": r"part-([a-zA-Z0-9]+)",
            "echo": r"echo-([a-zA-Z0-9]+)",
        }

        for entity in wildcards:
            if entity in entity_patterns:
                match = re.search(entity_patterns[entity], filename)
                entities[entity] = match.group(1) if match else "null"
            elif entity == "path":
                # Store the actual file path directly for path entity
                entities[entity] = str(file_path)
            else:
                # For unknown entities, try to extract from path
                if entity in ["subject", "sub"]:
                    # Extract from path structure sub-{subject}/ or sub{subject}/
                    path_match = re.search(r"/sub-?([a-zA-Z0-9]+)/", str(file_path))
                    entities[entity] = path_match.group(1) if path_match else "null"
                elif entity in ["session", "ses"]:
                    # Extract from path structure ses-{session}/ or ses{session}/
                    path_match = re.search(r"/ses-?([a-zA-Z0-9]+)/", str(file_path))
                    entities[entity] = path_match.group(1) if path_match else "null"
                else:
                    entities[entity] = "null"

        # Add to entity lists
        for entity in wildcards:
            if entity in entities:
                entity_lists[entity].append(entities[entity])
            else:
                entity_lists[entity].append("null")
        entity_lists["path"].append(str(file_path))

    if not entity_lists["path"]:
        return {}

    # Normalize entities by adding fake values for missing entities
    # This ensures all files have the same template pattern
    normalized_entity_lists = {"path": entity_lists["path"]}

    for entity, values in entity_lists.items():
        if entity != "path":
            # Replace "null" values with fake "snakenull" values to create uniform templates
            normalized_values = []
            for val in values:
                if val == "null":
                    normalized_values.append("snakenull")
                else:
                    normalized_values.append(val)
            normalized_entity_lists[entity] = normalized_values

            # Report what we're doing
            null_count = sum(1 for v in values if v == "null")
            if null_count > 0:
                print(
                    f"[snakenull] Normalized {null_count} missing '{entity}' entities to 'snakenull'"
                )

    # Create BidsComponent
    try:
        component = BidsComponent(**normalized_entity_lists)
        print(f"[snakenull] Created BidsComponent for {component_name}")
        print(
            f"[snakenull] Entity summary: {[(k, len(v)) for k, v in normalized_entity_lists.items() if k != 'path']}"
        )
        return {component_name: component}
    except Exception:
        # Fall back to BidsComponentWrapper format
        print(
            f"[snakenull] BidsComponent creation failed, using BidsComponentWrapper for {component_name}"
        )
        print(
            f"[snakenull] Entity summary: {[(k, len(v)) for k, v in normalized_entity_lists.items() if k != 'path']}"
        )
        wrapper = BidsComponentWrapper(normalized_entity_lists)
        return {component_name: wrapper}


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
        # Create a new argument group for snakenull options
        group = parser.add_argument_group(
            "snakenull", "Options for handling heterogeneous BIDS datasets"
        )

        group.add_argument(
            "--enable-snakenull",
            dest="plugins.snakenull.enable",
            action="store_true",
            default=False,
            help="Enable snakenull utilities for heterogeneous BIDS datasets",
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
            print(
                "[snakenull] Plugin enabled. Use generate_inputs_with_snakenull() in your Snakefile"
            )
            print(
                "[snakenull] Import: from snakebids.plugins.snakenull import generate_inputs_with_snakenull"
            )
