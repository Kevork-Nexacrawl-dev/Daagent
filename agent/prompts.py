"""
System prompt management for the Daagent agent.

This module now uses a layered prompt system where individual prompt components
are composed from YAML files in the prompts/ directory. This allows non-developers
to modify agent behavior without touching Python code.

For backward compatibility, the build_system_prompt() function maintains its
original signature and behavior.
"""

import logging
from pathlib import Path
from typing import List, Dict
from agent.prompt_loader import load_prompts, compose_prompt

logger = logging.getLogger(__name__)


def build_system_prompt() -> str:
    """
    Build the complete system prompt for the agent.

    This function loads all prompt layers from the prompts/ directory,
    sorts them by priority, and composes them into a final system prompt.

    Returns:
        Complete system prompt string ready for use with LLM API.

    Backward compatible with original function signature.
    """

    try:
        # Load all prompt layers
        layers = load_prompts(Path.cwd())

        # Compose into final prompt
        final_prompt = compose_prompt(layers)

        logger.info(f"Built system prompt from {len(layers)} layers")

        return final_prompt

    except Exception as e:
        logger.error(f"Error building system prompt: {e}")
        # Graceful fallback to minimal prompt
        return _get_fallback_prompt()


def _get_fallback_prompt() -> str:
    """
    Fallback prompt if loading fails.
    Ensures agent can still function.
    """

    return """You are a helpful AI agent.

You have access to tools that allow you to:
- Search the web for information
- Read and write files
- Execute code

Use these tools to help complete tasks."""


def load_custom_layers(domain: str) -> List[Dict]:
    """
    Load custom prompt layers for a specific domain.

    Useful for loading domain-specific behavior without modifying core layers.

    Args:
        domain: Domain name (e.g., 'research', 'coding', 'analysis')

    Returns:
        List of loaded PromptLayer objects (converted to dicts for compatibility)

    Example:
        layers = load_custom_layers('research')
        # Use layers to customize agent behavior for research tasks
    """

    try:
        domain_dir = Path.cwd() / "prompts" / "domain" / domain

        if not domain_dir.exists():
            logger.warning(f"Domain directory not found: {domain_dir}")
            return []

        # Load YAML files from domain-specific directory
        from agent.prompt_loader import PromptLayer
        import yaml

        layers = []

        for yaml_file in domain_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            if data and data.get("content"):
                layer = PromptLayer(
                    name=data.get("name"),
                    priority=data.get("priority", 50),
                    content=data.get("content"),
                    description=data.get("description", "")
                )
                layers.append(layer)

        logger.info(f"Loaded {len(layers)} custom layers for domain: {domain}")

        return layers

    except Exception as e:
        logger.error(f"Error loading custom layers for domain {domain}: {e}")
        return []
