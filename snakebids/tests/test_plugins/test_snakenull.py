"""Tests for the snakenull plugin."""

import tempfile
from pathlib import Path
import pytest

from snakebids.plugins.snakenull import (
    generate_inputs_with_snakenull,
    BidsComponentWrapper,
    SnakenullPlugin,
    normalize_entities_with_null,
)


class TestBidsComponentWrapper:
    """Test the BidsComponentWrapper class."""

    def test_empty_wrapper(self):
        """Test wrapper with empty data."""
        wrapper = BidsComponentWrapper({})
        assert wrapper.wildcards == {}
        assert wrapper.expand("test") == []
        assert wrapper.expand(["test1", "test2"]) == []

    def test_basic_functionality(self):
        """Test basic wrapper functionality."""
        entities = {
            "subject": ["001", "002"],
            "session": ["v1", "v2"],
            "path": ["/path1.nii.gz", "/path2.nii.gz"],
        }
        wrapper = BidsComponentWrapper(entities)

        # Test wildcards (first file)
        assert wrapper.wildcards["subject"] == "001"
        assert wrapper.wildcards["session"] == "v1"

        # Test dictionary access
        assert wrapper["subject"] == ["001", "002"]
        assert wrapper["session"] == ["v1", "v2"]
        assert "subject" in wrapper
        assert wrapper.get("subject") == ["001", "002"]
        assert wrapper.get("nonexistent", "default") == "default"

    def test_template_expansion(self):
        """Test template string expansion."""
        entities = {
            "subject": ["001", "002"],
            "session": ["v1", "v2"],
            "path": ["/path1.nii.gz", "/path2.nii.gz"],
        }
        wrapper = BidsComponentWrapper(entities)

        template = "/output/sub-{subject}_ses-{session}_result.txt"
        expanded = wrapper.expand(template)

        expected = [
            "/output/sub-001_ses-v1_result.txt",
            "/output/sub-002_ses-v2_result.txt",
        ]
        assert expanded == expected

    def test_list_expansion(self):
        """Test expansion of list inputs."""
        entities = {
            "subject": ["001", "002"],
            "path": ["/path1.nii.gz", "/path2.nii.gz"],
        }
        wrapper = BidsComponentWrapper(entities)

        templates = [
            "/output1/sub-{subject}_result1.txt",
            "/output2/sub-{subject}_result2.txt",
        ]
        expanded = wrapper.expand(templates)

        expected = [
            "/output1/sub-001_result1.txt",
            "/output1/sub-002_result1.txt",
            "/output2/sub-001_result2.txt",
            "/output2/sub-002_result2.txt",
        ]
        assert expanded == expected

    def test_non_string_expansion(self):
        """Test expansion with non-string inputs."""
        entities = {
            "subject": ["001", "002"],
            "path": ["/path1.nii.gz", "/path2.nii.gz"],
        }
        wrapper = BidsComponentWrapper(entities)

        # Test with non-string that should be repeated
        result = wrapper.expand(42)
        assert result == [42, 42]

    def test_missing_entity_handling(self):
        """Test handling of missing entities in templates."""
        entities = {"subject": ["001"], "path": ["/path1.nii.gz"]}
        wrapper = BidsComponentWrapper(entities)

        # Template with missing entity should be skipped
        template = "/output/sub-{subject}_ses-{session}_result.txt"
        expanded = wrapper.expand(template)
        assert expanded == []  # Skipped due to missing session


class TestNormalizeEntitiesWithNull:
    """Test the normalize_entities_with_null function."""

    def test_equal_lengths(self):
        """Test with already equal length lists."""
        entities = {"subject": ["001", "002"], "session": ["v1", "v2"]}
        result = normalize_entities_with_null(entities)
        assert result == entities

    def test_unequal_lengths(self):
        """Test with unequal length lists."""
        entities = {
            "subject": ["001", "002", "003"],
            "session": ["v1"],
            "run": ["01", "02"],
        }
        result = normalize_entities_with_null(entities)

        expected = {
            "subject": ["001", "002", "003"],
            "session": ["v1", "null", "null"],
            "run": ["01", "02", "null"],
        }
        assert result == expected

    def test_empty_input(self):
        """Test with empty input."""
        result = normalize_entities_with_null({})
        assert result == {}

    def test_custom_null_value(self):
        """Test with custom null value."""
        entities = {"subject": ["001"], "session": ["v1", "v2"]}
        result = normalize_entities_with_null(entities, null_value="missing")

        expected = {"subject": ["001", "missing"], "session": ["v1", "v2"]}
        assert result == expected


class TestGenerateInputsWithSnakenull:
    """Test the main generate_inputs_with_snakenull function."""

    def create_heterogeneous_dataset(self, base_dir: Path) -> None:
        """Create a test dataset with heterogeneous patterns."""
        files = [
            "sub-01/ses-v1/anat/sub-01_ses-v1_acq-mtw_T1w.nii.gz",
            "sub-01/ses-v2/anat/sub-01_ses-v2_acq-neuromelaninMTw_run-01_T1w.nii.gz",
            "sub-02/ses-v1/anat/sub-02_ses-v1_acq-mprage_T1w.nii.gz",
        ]

        for file_path in files:
            full_path = base_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()

    def test_heterogeneous_dataset_handling(self):
        """Test handling of heterogeneous datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bids_dir = Path(temp_dir)
            self.create_heterogeneous_dataset(bids_dir)

            config = {
                "t1w": {
                    "filters": {"suffix": "T1w", "extension": ".nii.gz"},
                    "wildcards": ["subject", "session", "acquisition", "run"],
                }
            }

            # Should not raise an error
            inputs = generate_inputs_with_snakenull(
                bids_dir=str(bids_dir), pybids_inputs=config
            )

            assert "t1w" in inputs
            t1w = inputs["t1w"]

            # Should be a BidsComponentWrapper
            assert isinstance(t1w, BidsComponentWrapper)

            # Should have the expected interface
            assert hasattr(t1w, "wildcards")
            assert hasattr(t1w, "expand")
            assert hasattr(t1w, "__getitem__")

            # Should have extracted entities
            assert len(t1w["path"]) == 3
            assert len(t1w["subject"]) == 3
            assert t1w["subject"] == ["01", "01", "02"]
            assert t1w["session"] == ["v1", "v2", "v1"]

    def test_empty_dataset(self):
        """Test with empty dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bids_dir = Path(temp_dir)

            config = {
                "t1w": {
                    "filters": {"suffix": "T1w", "extension": ".nii.gz"},
                    "wildcards": ["subject", "session"],
                }
            }

            # Should handle empty dataset gracefully
            inputs = generate_inputs_with_snakenull(
                bids_dir=str(bids_dir), pybids_inputs=config
            )

            # Should return something (even if empty)
            assert isinstance(inputs, dict)

    def test_acquisition_entity_mapping(self):
        """Test that acquisition entity is properly mapped from acq- patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bids_dir = Path(temp_dir)

            # Create heterogeneous files to trigger snakenull plugin
            files = [
                "sub-01/ses-v1/anat/sub-01_ses-v1_acq-mtw_T1w.nii.gz",
                "sub-01/ses-v2/anat/sub-01_ses-v2_acq-neuromelaninMTw_run-01_T1w.nii.gz",  # Different pattern
            ]

            for file_path in files:
                full_path = bids_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()

            config = {
                "t1w": {
                    "filters": {"suffix": "T1w", "extension": ".nii.gz"},
                    "wildcards": ["subject", "session", "acquisition"],
                }
            }

            inputs = generate_inputs_with_snakenull(
                bids_dir=str(bids_dir), pybids_inputs=config
            )

            if "t1w" in inputs:
                t1w = inputs["t1w"]
                # Should extract acquisition from acq- pattern
                assert "mtw" in t1w["acquisition"]
                assert "neuromelaninMTw" in t1w["acquisition"]


class TestSnakenullPlugin:
    """Test the SnakenullPlugin class."""

    def test_plugin_initialization(self):
        """Test plugin initializes correctly."""
        plugin = SnakenullPlugin()
        assert plugin.enable == False  # Disabled by default

    def test_plugin_disabled_by_default(self):
        """Test that plugin is opt-in (disabled by default)."""
        plugin = SnakenullPlugin()

        # Mock namespace without enable flag
        namespace = {}
        config = {}

        plugin.update_cli_namespace(namespace, config)
        assert plugin.enable == False

    def test_plugin_can_be_enabled(self):
        """Test that plugin can be enabled via CLI."""
        plugin = SnakenullPlugin()

        # Mock namespace with enable flag
        namespace = {"plugins.snakenull.enable": True}
        config = {}

        plugin.update_cli_namespace(namespace, config)
        assert plugin.enable == True

        # Should clean up namespace
        assert "plugins.snakenull.enable" not in namespace

    def test_finalize_config_when_enabled(self):
        """Test config finalization when enabled."""
        plugin = SnakenullPlugin()
        plugin.enable = True

        config = {}
        plugin.finalize_config(config)

        assert "plugins" in config
        assert "snakenull" in config["plugins"]
        assert config["plugins"]["snakenull"]["enable"] == True


if __name__ == "__main__":
    pytest.main([__file__])
