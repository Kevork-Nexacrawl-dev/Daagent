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

    def __init__(self, name: str, priority: int, content: str, 
                 description: str = "", mode: str = "stackable", 
                 priority_group: str = None):
        self.name = name
        self.priority = priority
        self.content = content
        self.description = description
        self.mode = mode  # NEW: "stackable" or "hierarchical"
        self.priority_group = priority_group  # NEW: Group name for organization
        
        # Validate mode
        if self.mode not in ["stackable", "hierarchical"]:
            raise ValueError(f"Invalid mode '{self.mode}'. Must be 'stackable' or 'hierarchical'")
        
        # Auto-detect priority group if not provided
        if self.priority_group is None:
            self.priority_group = self._detect_priority_group()
    
    def _detect_priority_group(self) -> str:
        """Auto-detect priority group based on priority number."""
        if 0 <= self.priority <= 10:
            return "behavior"
        elif 11 <= self.priority <= 19:
            return "expertise"
        elif 20 <= self.priority <= 30:
            return "tool_instructions"
        elif 31 <= self.priority <= 39:
            return "error_handling"
        elif 40 <= self.priority <= 50:
            return "response_format"
        elif 51 <= self.priority <= 59:
            return "memory_context"
        elif 60 <= self.priority <= 70:
            return "execution_mode"
        elif 71 <= self.priority <= 79:
            return "safety_ethics"
        elif 80 <= self.priority <= 90:
            return "user_overrides"
        elif 91 <= self.priority <= 100:
            return "debug_emergency"
        else:
            return "custom"
    
    def __repr__(self):
        return (f"PromptLayer(name={self.name}, priority={self.priority}, "
                f"mode={self.mode}, group={self.priority_group})")

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
            mode = data.get("mode", "stackable")  # NEW: Default to stackable
            priority_group = data.get("priority_group")  # NEW: Optional

            # Validate required fields
            if not all([name, priority is not None, content]):
                logger.warning(
                    f"Skipping {yaml_file}: missing required fields "
                    f"(name, priority, content)"
                )
                continue

            # Create layer with new fields
            layer = PromptLayer(name, int(priority), content, description, 
                              mode, priority_group)
            layers.append(layer)

            logger.info(
                f"Loaded layer: {name} (priority={priority}, mode={mode}, "
                f"group={layer.priority_group}) from {yaml_file.relative_to(base_path)}"
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
    Compose final system prompt from layers using hybrid mode.
    
    Hybrid composition:
    - Stackable mode: All prompts in group are concatenated
    - Hierarchical mode: Only highest priority in group is used
    
    Args:
        layers: List of PromptLayer objects.

    Returns:
        Composed system prompt string.
    """

    if not layers:
        raise ValueError("Cannot compose prompt from empty layer list")

    # Ensure sorted by priority
    sorted_layers = sorted(layers, key=lambda x: x.priority)
    
    # Group layers by priority_group
    from collections import defaultdict
    groups = defaultdict(list)
    
    for layer in sorted_layers:
        groups[layer.priority_group].append(layer)
    
    # Process each group
    final_parts = []
    
    # Process groups in priority order (using lowest priority in each group)
    group_priorities = {
        group: min(layer.priority for layer in layers_in_group)
        for group, layers_in_group in groups.items()
    }
    
    sorted_groups = sorted(groups.items(), key=lambda x: group_priorities[x[0]])
    
    for group_name, group_layers in sorted_groups:
        # Check mode of first layer (all in group should have same mode)
        mode = group_layers[0].mode
        
        if mode == "stackable":
            # Stack all prompts in this group
            for layer in sorted(group_layers, key=lambda x: x.priority):
                final_parts.append(layer.content)
                logger.debug(f"Stacked: {layer.name} (priority={layer.priority})")
        
        elif mode == "hierarchical":
            # Only use highest priority prompt in group
            highest_priority_layer = max(group_layers, key=lambda x: x.priority)
            final_parts.append(highest_priority_layer.content)
            logger.debug(
                f"Hierarchical: Selected {highest_priority_layer.name} "
                f"(priority={highest_priority_layer.priority}) from group {group_name}"
            )
            
            # Log which prompts were skipped
            skipped = [l for l in group_layers if l != highest_priority_layer]
            if skipped:
                logger.debug(
                    f"  Skipped: {[l.name for l in skipped]} "
                    f"(lower priority in hierarchical group)"
                )
    
    # Join with double newlines
    composed = "\n\n".join(final_parts)

    logger.info(
        f"Composed prompt from {len(sorted_layers)} layers "
        f"({len(final_parts)} parts in final output)"
    )

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
