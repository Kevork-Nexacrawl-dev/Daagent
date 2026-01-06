"""
Prompt layer loading and composition system.

Loads YAML-based prompt layers from the prompts/ directory and composes them
into a final system prompt. Supports priority-based ordering.

Priority ranges:
  0-9:     Core identity (agent fundamental behavior)
  10-29:   Behavioral traits (philosophies, attitudes)
  30-49:   Tool usage patterns (how to use available tools)
  50-99:   Domain-specific tasks (specialized behavior for domains)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml

logger = logging.getLogger(__name__)


class PromptLayer:
    """Represents a single prompt layer with metadata."""

    def __init__(self, name: str, priority: int, content: str, description: str = ""):
        self.name = name
        self.priority = priority
        self.content = content
        self.description = description

    def __repr__(self):
        return f"PromptLayer(name={self.name}, priority={self.priority})"

    def __lt__(self, other):
        """Support sorting by priority."""
        return self.priority < other.priority


def load_prompts(base_path: Path = None) -> List[PromptLayer]:
    """
    Load all prompt layers from YAML files.

    Args:
        base_path: Root path to search for prompts/ directory.
                   Defaults to current working directory.

    Returns:
        List of PromptLayer objects sorted by priority (ascending).

    Raises:
        FileNotFoundError: If prompts directory doesn't exist.
    """

    if base_path is None:
        base_path = Path.cwd()

    prompts_dir = base_path / "prompts"

    if not prompts_dir.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

    layers = []

    # Recursively search for YAML files
    yaml_files = list(prompts_dir.rglob("*.yaml")) + list(prompts_dir.rglob("*.yml"))

    logger.info(f"Found {len(yaml_files)} prompt layer files")

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            if data is None:
                logger.warning(f"Empty YAML file: {yaml_file}")
                continue

            # Extract required fields
            name = data.get("name")
            priority = data.get("priority")
            content = data.get("content")
            description = data.get("description", "")

            # Validate required fields
            if not all([name, priority is not None, content]):
                logger.warning(
                    f"Skipping {yaml_file}: missing required fields "
                    f"(name, priority, content)"
                )
                continue

            # Create layer
            layer = PromptLayer(name, int(priority), content, description)
            layers.append(layer)

            logger.info(
                f"Loaded layer: {name} (priority={priority}) "
                f"from {yaml_file.relative_to(base_path)}"
            )

        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {yaml_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading {yaml_file}: {e}")

    # Sort by priority
    layers.sort(key=lambda x: x.priority)

    logger.info(f"Loaded {len(layers)} prompt layers total")

    return layers


def compose_prompt(layers: List[PromptLayer]) -> str:
    """
    Compose final system prompt from layers.

    Layers are joined with double newlines and sorted by priority.
    Assumes layers are already sorted (from load_prompts).

    Args:
        layers: List of PromptLayer objects.

    Returns:
        Composed system prompt string.
    """

    if not layers:
        raise ValueError("Cannot compose prompt from empty layer list")

    # Ensure sorted by priority
    sorted_layers = sorted(layers, key=lambda x: x.priority)

    # Extract content from each layer
    parts = [layer.content for layer in sorted_layers]

    # Join with double newlines
    composed = "\n\n".join(parts)

    logger.info(f"Composed prompt from {len(sorted_layers)} layers")

    return composed


def load_and_compose(base_path: Path = None) -> str:
    """
    Convenience function: load all prompts and compose into final prompt.

    Args:
        base_path: Root path to search for prompts/ directory.

    Returns:
        Composed system prompt string.
    """

    layers = load_prompts(base_path)
    return compose_prompt(layers)
