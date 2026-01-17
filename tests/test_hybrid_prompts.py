"""
Tests for hybrid prompt layering system.
"""

import sys
import os
import tempfile
import yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.prompt_loader import PromptLayer, compose_prompt


def test_prompt_layer_creation():
    """Test PromptLayer creation with new fields"""
    print("\n🧪 Testing PromptLayer creation...")

    # Test with explicit fields
    layer = PromptLayer("test", 10, "content", "desc", "stackable", "behavior")
    assert layer.name == "test"
    assert layer.priority == 10
    assert layer.mode == "stackable"
    assert layer.priority_group == "behavior"

    # Test auto-detection
    layer2 = PromptLayer("test2", 25, "content2", "desc2")
    assert layer2.priority_group == "tool_instructions"  # 20-30 range

    print("✅ PromptLayer creation working\n")


def test_mode_validation():
    """Test mode validation"""
    print("\n🧪 Testing mode validation...")

    try:
        PromptLayer("test", 10, "content", mode="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid mode" in str(e)
        print("✅ Mode validation working\n")


def test_stackable_composition():
    """Test stackable mode composition"""
    print("\n🧪 Testing stackable composition...")

    layers = [
        PromptLayer("layer1", 10, "Content 1", mode="stackable", priority_group="behavior"),
        PromptLayer("layer2", 15, "Content 2", mode="stackable", priority_group="behavior"),
    ]

    result = compose_prompt(layers)
    assert "Content 1" in result
    assert "Content 2" in result
    assert result.count("\n\n") == 1  # Should be joined with double newline

    print("✅ Stackable composition working\n")


def test_hierarchical_composition():
    """Test hierarchical mode composition"""
    print("\n🧪 Testing hierarchical composition...")

    layers = [
        PromptLayer("safe", 20, "Safe mode", mode="hierarchical", priority_group="tool_instructions"),
        PromptLayer("aggressive", 25, "Aggressive mode", mode="hierarchical", priority_group="tool_instructions"),
    ]

    result = compose_prompt(layers)
    assert "Aggressive mode" in result
    assert "Safe mode" not in result  # Should be excluded

    print("✅ Hierarchical composition working\n")


def test_mixed_modes():
    """Test mixed stackable and hierarchical modes"""
    print("\n🧪 Testing mixed modes...")

    layers = [
        # Stackable group
        PromptLayer("identity", 5, "Identity", mode="stackable", priority_group="behavior"),
        PromptLayer("behavior", 8, "Behavior", mode="stackable", priority_group="behavior"),
        # Hierarchical group
        PromptLayer("safe", 20, "Safe", mode="hierarchical", priority_group="tool_instructions"),
        PromptLayer("aggressive", 25, "Aggressive", mode="hierarchical", priority_group="tool_instructions"),
    ]

    result = compose_prompt(layers)
    # Stackable: both should be included
    assert "Identity" in result
    assert "Behavior" in result
    # Hierarchical: only aggressive should be included
    assert "Aggressive" in result
    assert "Safe" not in result

    print("✅ Mixed modes working\n")


def test_backward_compatibility():
    """Test backward compatibility with old YAML files"""
    print("\n🧪 Testing backward compatibility...")

    # Create layer without mode (should default to stackable)
    layer = PromptLayer("old_layer", 10, "content")
    assert layer.mode == "stackable"
    assert layer.priority_group == "behavior"  # Auto-detected

    print("✅ Backward compatibility working\n")


def test_priority_group_ranges():
    """Test priority group auto-detection"""
    print("\n🧪 Testing priority group ranges...")

    test_cases = [
        (5, "behavior"),
        (15, "expertise"),
        (25, "tool_instructions"),
        (35, "error_handling"),
        (45, "response_format"),
        (55, "memory_context"),
        (65, "execution_mode"),
        (75, "safety_ethics"),
        (85, "user_overrides"),
        (95, "debug_emergency"),
        (150, "custom"),  # Out of range
    ]

    for priority, expected_group in test_cases:
        layer = PromptLayer(f"test_{priority}", priority, "content")
        assert layer.priority_group == expected_group, f"Priority {priority} should be {expected_group}, got {layer.priority_group}"

    print("✅ Priority group ranges working\n")


if __name__ == "__main__":
    test_prompt_layer_creation()
    test_mode_validation()
    test_stackable_composition()
    test_hierarchical_composition()
    test_mixed_modes()
    test_backward_compatibility()
    test_priority_group_ranges()

    print("🎉 All hybrid prompt tests passed!")