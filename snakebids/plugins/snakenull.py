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


class SnakemakeWildcards:
    """A wildcards class that supports both dictionary and attribute access."""

    def __init__(self, wildcard_dict: dict[str, str]):
        """Initialize with a dictionary of wildcards."""
        self._wildcards = wildcard_dict
        # Set attributes for dot notation access (wildcards.subject)
        for key, value in wildcard_dict.items():
            setattr(self, key, value)

    def __getitem__(self, key: str) -> str:
        """Support dictionary access: wildcards['subject']."""
        return self._wildcards[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return key in self._wildcards

    def get(self, key: str, default=None):
        """Support .get() method."""
        return self._wildcards.get(key, default)

    def items(self):
        """Support .items() iteration."""
        return self._wildcards.items()

    def keys(self):
        """Support .keys() method."""
        return self._wildcards.keys()

    def values(self):
        """Support .values() method."""
        return self._wildcards.values()

    def __str__(self):
        """Return string representation."""
        return str(self._wildcards)

    def __repr__(self):
        """Repr representation."""
        return f"SnakemakeWildcards({self._wildcards})"


class BidsComponentWrapper:
    """A wrapper that makes dictionary data look like a BidsComponent.

    This provides compatibility with existing code that expects BidsComponent
    methods like .expand() and .wildcards, while also supporting attribute-style
    access for micapipe compatibility.
    """

    def __init__(self, entity_dict: dict[str, list[str]], bids_component=None):
        """Initialize with entity dictionary and optional BidsComponent."""
        self._entities = entity_dict.copy()
        self._bids_component = bids_component

    @property
    def entities(self) -> dict[str, list[str]]:
        """Return the entities dictionary."""
        return self._entities

    @property
    def wildcards(self) -> SnakemakeWildcards:
        """Return wildcards in the format expected by micapipe code.

        This returns wildcards that support both dict access (wildcards['subject'])
        and attribute access (wildcards.subject) like Snakemake's wildcards.
        """
        if (
            not self._entities
            or "path" not in self._entities
            or not self._entities["path"]
        ):
            return SnakemakeWildcards({})

        # Return wildcards for the first file
        wildcard_dict = {}
        for entity, values in self._entities.items():
            if entity != "path" and values:
                wildcard_dict[entity] = values[0]
        return SnakemakeWildcards(wildcard_dict)

    def expand(self, template_func_result=None):
        """Expand templates using the entity data.

        This method is called by micapipe rules like:
        inputs['t1w'].expand(get_structural_outputs(inputs, output_dir))

        If we have a BidsComponent, delegate to it for proper Snakemake integration.
        Otherwise, use our fallback expansion method.
        """
        # If we have a BidsComponent, delegate to it for proper expansion
        if self._bids_component is not None:
            return self._bids_component.expand(template_func_result)

        # Fallback to manual expansion
        if template_func_result is None:
            return []

        if isinstance(template_func_result, str):
            # Single template string - expand it for each set of entities
            return self._expand_template_string(template_func_result)
        if isinstance(template_func_result, list):
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

    def __getattr__(self, name):
        """Provide attribute-style access to entity values (e.g., component.subject)."""
        if name in self._entities:
            return self._entities[name]
        msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
        raise AttributeError(msg)

    def __getitem__(self, key):
        """Allow dictionary-style access to entities."""
        return self._entities[key]

    def __contains__(self, key):
        """Check if entity exists."""
        return key in self._entities

    def get(self, key, default=None):
        """Get entity with default."""
        return self._entities.get(key, default)

    @property
    def zip_lists(self):
        """Provide zip_lists property for compatibility with BidsComponent."""
        # Exclude 'path' from zip_lists as per snakebids convention
        return {k: v for k, v in self._entities.items() if k != "path"}

    @property
    def entities(self):
        """Provide entities property for compatibility."""
        return self._entities


class FileBasedComponent:
    """A component that preserves exact file-to-entity mapping to prevent phantom combinations.
    
    Unlike BidsComponent, this doesn't apply a single template to all files.
    Instead, it stores the exact entities for each file and expands templates
    using only the entities that each file actually has.
    """
    
    def __init__(self, name: str, file_entity_mappings: list[dict[str, str]]):
        """Initialize with exact file-to-entity mappings.
        
        Parameters
        ----------
        name : str
            Name of the component
        file_entity_mappings : list[dict[str, str]]
            List of entity dictionaries, one per file. Each dict maps entity names
            to values for that specific file. Must include 'path' key.
        """
        self.name = name
        self.file_entity_mappings = file_entity_mappings
        
        # Build zip_lists for compatibility
        if not file_entity_mappings:
            self._zip_lists: dict[str, list[str]] = {}
            self._entities: dict[str, list[str]] = {}
            self._wildcards = SnakemakeWildcards({})
            return
            
        # Get all possible entities (excluding 'path')
        all_entities: set[str] = set()
        for mapping in file_entity_mappings:
            all_entities.update(mapping.keys())
        all_entities.discard('path')
        
        # Build zip_lists with exact values for each file
        zip_lists: dict[str, list[str]] = {}
        for entity in all_entities:
            zip_lists[entity] = [
                mapping.get(entity, 'snakenull') for mapping in file_entity_mappings
            ]
        
        self._zip_lists = zip_lists
        
        # Build entities dict (includes path)
        entities: dict[str, list[str]] = dict(zip_lists)
        entities['path'] = [mapping.get('path', '') for mapping in file_entity_mappings]
        self._entities = entities
        
        # Create wildcards dict for the first file
        if file_entity_mappings:
            first_file = file_entity_mappings[0]
            wildcard_dict: dict[str, str] = {k: f"{{{k}}}" for k in all_entities}
            self._wildcards = SnakemakeWildcards(wildcard_dict)
        else:
            self._wildcards = SnakemakeWildcards({})

    @property
    def zip_lists(self) -> dict[str, list[str]]:
        """Return zip_lists (excludes 'path')."""
        return self._zip_lists
        
    @property 
    def entities(self) -> dict[str, list[str]]:
        """Return entities dict (includes 'path')."""
        return self._entities
        
    @property
    def wildcards(self) -> SnakemakeWildcards:
        """Return wildcards for micapipe compatibility."""
        return self._wildcards

    def expand(self, template_func_result=None) -> list:
        """Expand templates using exact file-to-entity mappings.
        
        This is the key method that prevents phantom combinations.
        For each file, it only uses the entities that file actually has.
        """
        if template_func_result is None:
            return []
            
        if isinstance(template_func_result, str):
            return self._expand_template_string(template_func_result)
        elif isinstance(template_func_result, list):
            results = []
            for template in template_func_result:
                if isinstance(template, str):
                    results.extend(self._expand_template_string(template))
                else:
                    # Non-string result repeated for each file
                    results.extend([template] * len(self.file_entity_mappings))
            return results
        else:
            # Return as-is for other types, repeated for each file
            return [template_func_result] * len(self.file_entity_mappings)

    def _expand_template_string(self, template: str) -> list[str]:
        """Expand template for each file using only its actual entities."""
        results = []
        
        for mapping in self.file_entity_mappings:
            # For this specific file, only use entities it actually has
            # Skip entities that are 'snakenull' (i.e., don't exist in the original file)
            file_entities = {}
            
            for entity, value in mapping.items():
                if entity != 'path':
                    file_entities[entity] = value
            
            # Format template - but handle missing wildcards gracefully  
            try:
                formatted = template.format(**file_entities)
                results.append(formatted)
            except KeyError:
                # If template needs entities this file doesn't have, skip formatting those parts
                # This is the key difference from BidsComponent
                import re
                
                # Replace missing wildcards with empty strings to avoid phantom entities
                formatted = template
                
                # Find all wildcards in template
                wildcards_in_template = re.findall(r'\{(\w+)\}', template)
                
                for wildcard in wildcards_in_template:
                    if wildcard in file_entities:
                        # Replace with actual value
                        formatted = formatted.replace(f'{{{wildcard}}}', file_entities[wildcard])
                    else:
                        # Remove phantom entity entirely (don't add _entity-snakenull)
                        # Look for patterns like _entity-{wildcard} and remove them
                        pattern = f'_{wildcard}-{{{wildcard}}}'
                        formatted = re.sub(pattern, '', formatted)
                        
                        # Also handle bare {wildcard} without prefix
                        formatted = formatted.replace(f'{{{wildcard}}}', '')
                
                # Clean up any double underscores or trailing underscores
                formatted = re.sub(r'_+', '_', formatted)  # Multiple underscores -> single
                formatted = re.sub(r'_+\.', '.', formatted)  # Remove underscore before extension
                
                results.append(formatted)
                
        return results


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
            file_count = len(entities.get("path", []))
        elif hasattr(comp_data, "zip_lists"):
            # BidsComponent - get file count from zip_lists
            zip_lists = comp_data.zip_lists
            file_count = len(list(zip_lists.values())[0]) if zip_lists else 0
            entities = comp_data.entities
        elif hasattr(comp_data, "entities"):
            entities = comp_data.entities
            file_count = len(entities.get("path", []))
        else:
            entities = {}
            file_count = 0

        print(f"  {comp_name}: {file_count} files")
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

    bids_path = Path(bids_dir)
    filters = component_config.get("filters", {})
    wildcards = component_config.get("wildcards", [])

    # Build search pattern from filters
    search_pattern = "**/*"
    if "suffix" in filters:
        search_pattern += f"_{filters['suffix']}"
    if "extension" in filters:
        extensions = filters["extension"]
        if isinstance(extensions, list):
            # Use the first extension for glob pattern
            search_pattern += extensions[0]
        else:
            search_pattern += extensions

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

        # Add this file's specific entity combination to the lists
        # This maintains the correspondence: each index represents one actual file
        for entity in wildcards:
            entity_lists[entity].append(entities.get(entity, "null"))
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

    # Create a proper path template for BidsComponent
    # We need to construct a path template that matches the files we found
    if normalized_entity_lists["path"]:
        # Prepare zip_lists (exclude 'path') - these maintain exact file-to-entity correspondence
        zip_lists = {k: v for k, v in normalized_entity_lists.items() if k != "path"}

        # CRITICAL FIX: Create path template that includes ALL entities that have real values
        # Don't just use first file - analyze ALL files to see which entities are used

        # Find entities that have at least one real (non-snakenull) value
        entities_with_real_values = {}
        for entity, values in zip_lists.items():
            real_values = [v for v in values if v != "snakenull"]
            if real_values:
                entities_with_real_values[entity] = real_values[
                    0
                ]  # Use first real value as pattern

        print(
            f"[snakenull] Entities with real values: {list(entities_with_real_values.keys())}"
        )

        # Find a sample file that has as many real entities as possible
        sample_path = None
        max_real_entities = 0

        for i, file_path in enumerate(normalized_entity_lists["path"]):
            # Count how many real entities this file has
            real_entity_count = 0
            for entity in entities_with_real_values:
                if zip_lists[entity][i] != "snakenull":
                    real_entity_count += 1

            if real_entity_count > max_real_entities:
                max_real_entities = real_entity_count
                sample_path = file_path

        if not sample_path:
            sample_path = normalized_entity_lists["path"][0]  # Fallback to first file

        path_template = str(sample_path)
        print(f"[snakenull] Using sample path: {sample_path}")

        # Import BidsComponent here since we need it
        from snakebids import BidsComponent

        # CRITICAL INSIGHT: For BidsComponent compatibility, the path template must include
        # ALL entities that appear in zip_lists as wildcards. Create a template that 
        # includes all possible entities, even if some files don't have all entities.
        
        # Start with the sample path but make it generic for all entities
        path_parts = str(sample_path).split('/')
        filename = path_parts[-1]
        
        # Create a generic template with all entities as wildcards
        # Format: sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_..._T1w.nii.gz
        directory_template = "/".join(path_parts[:-1])  # Everything except filename
        
        # Replace directory parts with wildcards
        directory_template = directory_template.replace(f"sub-{entities_with_real_values['subject']}", "sub-{subject}")
        directory_template = directory_template.replace(f"ses-{entities_with_real_values['session']}", "ses-{session}")
        
        # Create filename template with ALL entities as optional wildcards
        filename_template = "sub-{subject}_ses-{session}"
        
        # Add other entities if they exist
        if 'acq' in zip_lists:
            filename_template += "_acq-{acq}"
        if 'run' in zip_lists:
            filename_template += "_run-{run}" 
        if 'part' in zip_lists:
            filename_template += "_part-{part}"
            
        # Add suffix and extension
        suffix_match = filename.split('_')[-1]  # e.g., "T1w.nii.gz"
        filename_template += f"_{suffix_match}"
        
        path_template = f"{directory_template}/{filename_template}"

        # CRITICAL: Don't filter zip_lists - BidsComponent needs ALL entities 
        # The key insight: if zip_lists contains exact file-to-entity mappings,
        # BidsComponent should not create phantom combinations even with cartesian product logic
        
        print(f"[snakenull] Using ALL normalized entities for BidsComponent: {list(zip_lists.keys())}")
        print(f"[snakenull] Path template: {path_template}")

        # Use ALL zip_lists entities - no filtering
        final_zip_lists = zip_lists

        # CRITICAL FIX: Instead of creating one template with ALL entities,
        # group files by their actual entity pattern and create separate BidsComponents
        print(f"[snakenull] Grouping files by entity patterns to prevent phantom combinations")
        
        # Group files by their actual entity signature (which entities they have)
        file_groups = {}
        
        for i, file_path in enumerate(normalized_entity_lists["path"]):
            # Create signature based on which entities this file actually has
            signature = []
            file_entities = {}
            
            for entity, values in zip_lists.items():
                if i < len(values) and values[i] != "snakenull":
                    signature.append(entity)
                    file_entities[entity] = values[i]
                elif entity in ['subject', 'session']:  # Always include required entities
                    signature.append(entity) 
                    file_entities[entity] = values[i] if i < len(values) else "snakenull"
            
            signature_key = tuple(sorted(signature))
            
            if signature_key not in file_groups:
                file_groups[signature_key] = {
                    'files': [],
                    'entities': {entity: [] for entity in signature}
                }
            
            file_groups[signature_key]['files'].append(file_path)
            for entity in signature:
                file_groups[signature_key]['entities'][entity].append(file_entities.get(entity, 'snakenull'))
        
        print(f"[snakenull] Found {len(file_groups)} different entity patterns:")
        for sig, group in file_groups.items():
            print(f"  Pattern {sig}: {len(group['files'])} files")
        
        # For simplicity, use the largest group to create the BidsComponent
        # This ensures most files match the template exactly
        largest_group = max(file_groups.values(), key=lambda g: len(g['files']))
        largest_signature = None
        for sig, group in file_groups.items():
            if group is largest_group:
                largest_signature = sig
                break
        
        print(f"[snakenull] Using largest group with pattern {largest_signature}")
        
        # Create path template based on largest group's pattern
        sample_file = largest_group['files'][0]
        path_parts = str(sample_file).split('/')
        filename_parts = path_parts[-1].split('_')
        
        # Build template with only entities from this pattern
        directory_template = "/".join(path_parts[:-1])
        
        # Replace directory wildcards
        if 'subject' in largest_signature:
            directory_template = directory_template.replace(
                f"sub-{largest_group['entities']['subject'][0]}", "sub-{subject}"
            )
        if 'session' in largest_signature:
            directory_template = directory_template.replace(
                f"ses-{largest_group['entities']['session'][0]}", "ses-{session}"
            )
        
        # Build filename template with only this pattern's entities
        filename_template = "sub-{subject}_ses-{session}"
        
        for entity in ['acq', 'run', 'part']:
            if entity in largest_signature:
                filename_template += f"_{entity}-{{{entity}}}"
        
        # Add suffix
        suffix = filename_parts[-1]  # e.g., "T1w.nii.gz"
        filename_template += f"_{suffix}"
        
        path_template = f"{directory_template}/{filename_template}"
        
        # Create zip_lists using ONLY files from the largest group
        # This prevents phantom combinations by ensuring all files match the template
        final_zip_lists = {}
        for entity in largest_signature:
            final_zip_lists[entity] = []
            
        # Add only files from the largest group
        for file_path in largest_group['files']:
            for entity in largest_signature:
                # Find the corresponding entity values for this file
                file_index = normalized_entity_lists["path"].index(file_path)
                if entity in zip_lists and file_index < len(zip_lists[entity]):
                    final_zip_lists[entity].append(zip_lists[entity][file_index])
                else:
                    final_zip_lists[entity].append('snakenull')
        
        print(f"[snakenull] Using entities for template: {list(largest_signature)}")
        print(f"[snakenull] Path template: {path_template}")
        print(f"[snakenull] Creating BidsComponent for {component_name}")
        print(f"[snakenull] Found {len(normalized_entity_lists['path'])} actual files")
        
        # Import BidsComponent here since we need it
        from snakebids import BidsComponent
        
        # Create standard BidsComponent - no wrappers or modifications
        component = BidsComponent(
            name=component_name,
            zip_lists=final_zip_lists,
            path=path_template
        )
        return {component_name: component}
    else:
        return {}


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
