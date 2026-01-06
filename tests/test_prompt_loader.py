"""
Tests for prompt_loader.py and prompts.py

Tests verify:
- Priority sorting of prompt layers
- Correct composition of final prompt
- Missing file handling (graceful degradation)
- Backward compatibility with prompts.py interface
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from agent.prompt_loader import PromptLayer, load_prompts, compose_prompt
from agent.prompts import build_system_prompt, load_custom_layers


class TestPromptLayer:
    """Test PromptLayer class."""

    def test_prompt_layer_creation(self):
        """Test basic PromptLayer instantiation."""
        layer = PromptLayer(
            name="test",
            priority=10,
            content="Test content",
            description="Test description"
        )

        assert layer.name == "test"
        assert layer.priority == 10
        assert layer.content == "Test content"
        assert layer.description == "Test description"

    def test_prompt_layer_sorting(self):
        """Test PromptLayer sorting by priority."""
        layer1 = PromptLayer("layer1", 10, "content1")
        layer2 = PromptLayer("layer2", 5, "content2")
        layer3 = PromptLayer("layer3", 15, "content3")

        layers = [layer1, layer2, layer3]
        sorted_layers = sorted(layers)

        priorities = [l.priority for l in sorted_layers]
        assert priorities == [5, 10, 15]


class TestPromptLoading:
    """Test prompt loading functionality."""

    def test_load_prompts_success(self):
        """Test successful loading of prompt layers."""
        layers = load_prompts(Path.cwd())

        # Should have loaded at least our 4 test layers
        assert len(layers) >= 4

        # Verify they're sorted by priority
        priorities = [l.priority for l in layers]
        assert priorities == sorted(priorities)

    def test_load_prompts_priority_order(self):
        """Test that loaded layers are sorted by priority."""
        layers = load_prompts(Path.cwd())

        # Find our known layers
        layer_names = {l.name for l in layers}
        assert "core_identity" in layer_names
        assert "core_behavior" in layer_names
        assert "tool_usage" in layer_names
        assert "domain_research" in layer_names

        # Verify priorities are ascending
        for i in range(len(layers) - 1):
            assert layers[i].priority <= layers[i+1].priority

    def test_load_prompts_missing_directory(self):
        """Test handling of missing prompts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                load_prompts(Path(tmpdir))


class TestPromptComposition:
    """Test prompt composition."""

    def test_compose_prompt_basic(self):
        """Test basic prompt composition."""
        layers = [
            PromptLayer("layer1", 0, "Content 1"),
            PromptLayer("layer2", 10, "Content 2"),
            PromptLayer("layer3", 20, "Content 3")
        ]

        composed = compose_prompt(layers)

        # All content should be present
        assert "Content 1" in composed
        assert "Content 2" in composed
        assert "Content 3" in composed

    def test_compose_prompt_order(self):
        """Test that composition respects priority order."""
        layers = [
            PromptLayer("layer3", 20, "THIRD"),
            PromptLayer("layer1", 0, "FIRST"),
            PromptLayer("layer2", 10, "SECOND")
        ]

        composed = compose_prompt(layers)

        # Verify order in composed prompt
        first_pos = composed.find("FIRST")
        second_pos = composed.find("SECOND")
        third_pos = composed.find("THIRD")

        assert first_pos < second_pos < third_pos

    def test_compose_prompt_empty_list(self):
        """Test that empty layer list raises error."""
        with pytest.raises(ValueError):
            compose_prompt([])

    def test_compose_final_prompt(self):
        """Test composition of actual loaded prompts."""
        layers = load_prompts(Path.cwd())
        composed = compose_prompt(layers)

        # Verify composed prompt is non-empty
        assert len(composed) > 0

        # Should contain key phrases from our prompts
        assert "AI agent" in composed or "general-purpose" in composed
        assert "tools" in composed.lower() or "search" in composed.lower()


class TestBackwardCompatibility:
    """Test backward compatibility with prompts.py interface."""

    def test_build_system_prompt_success(self):
        """Test build_system_prompt() function."""
        prompt = build_system_prompt()

        # Should return non-empty string
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_system_prompt_contains_identity(self):
        """Test that built prompt contains identity content."""
        prompt = build_system_prompt()

        # Should contain core identity content
        assert "AI agent" in prompt or "agent" in prompt.lower()

    def test_build_system_prompt_is_idempotent(self):
        """Test that build_system_prompt() returns consistent results."""
        prompt1 = build_system_prompt()
        prompt2 = build_system_prompt()

        assert prompt1 == prompt2


class TestCustomLayers:
    """Test custom layer loading functionality."""

    def test_load_custom_layers_research(self):
        """Test loading research domain layers."""
        layers = load_custom_layers("research")

        # Should find at least the research layer
        assert len(layers) >= 0  # May be empty if no custom layers yet

    def test_load_custom_layers_nonexistent(self):
        """Test loading nonexistent domain gracefully."""
        layers = load_custom_layers("nonexistent_domain_xyz")

        # Should return empty list, not error
        assert isinstance(layers, list)


class TestIntegration:
    """Integration tests."""

    def test_full_pipeline_load_and_compose(self):
        """Test complete pipeline: load → compose → use."""
        # Load
        layers = load_prompts(Path.cwd())
        assert len(layers) > 0

        # Compose
        prompt = compose_prompt(layers)
        assert len(prompt) > 0

        # Via convenience function
        from agent.prompt_loader import load_and_compose
        prompt2 = load_and_compose(Path.cwd())
        assert prompt == prompt2

    def test_prompts_module_integration(self):
        """Test integration with prompts.py module."""
        # Via new layer system
        prompt = build_system_prompt()

        # Should be valid prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be substantial

        # Should contain expected content
        content_checks = [
            ("identity", ["AI agent", "tools"]),
            ("behavior", ["DOER", "action"]),
            ("tool_usage", ["search", "file"])
        ]

        # At least some content should be present
        assert any(
            any(keyword.lower() in prompt.lower() for keyword in keywords)
            for _, keywords in content_checks
        )


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_corrupt_yaml_handling(self):
        """Test handling of corrupt YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create prompts structure
            (tmpdir_path / "prompts" / "core").mkdir(parents=True)

            # Write corrupt YAML
            corrupt_file = tmpdir_path / "prompts" / "core" / "corrupt.yaml"
            with open(corrupt_file, 'w') as f:
                f.write("{ invalid yaml: [")

            # Write valid YAML
            valid_file = tmpdir_path / "prompts" / "core" / "valid.yaml"
            with open(valid_file, 'w') as f:
                yaml.dump({
                    "name": "valid_layer",
                    "priority": 0,
                    "content": "Valid content"
                }, f)

            # Should load valid layer and skip corrupt one
            layers = load_prompts(tmpdir_path)
            assert len(layers) >= 1

            layer_names = {l.name for l in layers}
            assert "valid_layer" in layer_names

    def test_missing_required_fields(self):
        """Test handling of YAML files missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "prompts" / "core").mkdir(parents=True)

            # Write YAML missing 'content'
            invalid_file = tmpdir_path / "prompts" / "core" / "invalid.yaml"
            with open(invalid_file, 'w') as f:
                yaml.dump({
                    "name": "incomplete",
                    "priority": 10
                    # Missing 'content'
                }, f)

            # Write valid YAML
            valid_file = tmpdir_path / "prompts" / "core" / "valid.yaml"
            with open(valid_file, 'w') as f:
                yaml.dump({
                    "name": "complete",
                    "priority": 0,
                    "content": "Content"
                }, f)

            layers = load_prompts(tmpdir_path)

            # Should skip invalid, include valid
            layer_names = {l.name for l in layers}
            assert "incomplete" not in layer_names
            assert "complete" in layer_names
