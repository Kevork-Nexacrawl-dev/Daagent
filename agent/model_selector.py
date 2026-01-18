"""
Model Selector with Manual Override and Task-Type Routing.

Handles model selection with:
- Manual preference override from UI
- Automatic cascade for "auto" mode
- Future: Task-type detection for code tasks
"""

from typing import Dict, Any, Optional
from agent.config import Config


class ModelSelector:
    """
    Intelligent model selection with manual override capability.

    Supports:
    - Manual model preference from UI dropdown
    - Automatic cascade when "auto" selected
    - Future: Task-type routing (code → Grok 4 Fast)
    """

    def __init__(self, preference: str = "auto"):
        """Initialize with optional manual preference."""
        self.preference = preference

        # Model mappings for UI values to actual model IDs
        self.model_mappings = {
            "deepseek-v3-free": "nex-agi/deepseek-v3.1-nex-n1:free",
            "deepseek-v3-paid": "deepseek/deepseek-chat:paid",
            "grok-4-fast": "x-ai/grok-4-fast",
            "claude-sonnet": "anthropic/claude-3.5-sonnet"
        }

        # Display names and cost tiers for UI
        self.model_info = {
            "nex-agi/deepseek-v3.1-nex-n1:free": {
                "display_name": "DeepSeek V3 (Free)",
                "cost_tier": "free"
            },
            "deepseek/deepseek-chat": {
                "display_name": "DeepSeek V3 (Free)",
                "cost_tier": "free"
            },
            "deepseek/deepseek-chat:paid": {
                "display_name": "DeepSeek V3 (Paid)",
                "cost_tier": "paid"
            },
            "x-ai/grok-4-fast": {
                "display_name": "Grok 4 Fast",
                "cost_tier": "paid"
            },
            "anthropic/claude-3.5-sonnet": {
                "display_name": "Claude Sonnet",
                "cost_tier": "paid"
            }
        }

    def get_current_model_info(self) -> Dict[str, str]:
        """Return current model info for UI display."""
        # For now, return info based on preference
        # TODO: In future, this should return actual selected model from provider manager
        if self.preference == "auto":
            return {"display_name": "Auto (Smart)", "cost_tier": "auto"}

        model_id = self.model_mappings.get(self.preference)
        if model_id:
            return self.model_info.get(model_id, {"display_name": "Unknown", "cost_tier": "unknown"})

        return {"display_name": "Unknown", "cost_tier": "unknown"}

    def select_model(self, task_type: str = "general") -> str:
        """
        Select model based on preference and task type.

        Args:
            task_type: Type of task (general, code, reasoning)

        Returns:
            Model ID to use
        """
        # If manual preference (not auto), use it
        if self.preference != "auto":
            model_id = self.model_mappings.get(self.preference)
            if model_id:
                return model_id
            # Fallback to auto if invalid preference
            return self._get_auto_model()

        # TODO: Task-type routing (future enhancement)
        # if task_type == "code":
        #     return "x-ai/grok-2-1212"  # Always Grok for code

        # Auto mode: Use existing cascade logic
        return self._get_auto_model()

    def _get_auto_model(self) -> str:
        """Existing automatic cascade logic."""
        # This should integrate with ProviderManager's cascade logic
        # For now, return free tier as default
        return "deepseek/deepseek-chat"

    def get_model_info_by_id(self, model_id: str) -> Dict[str, str]:
        """Get model info by model ID for actual selected models."""
        return self.model_info.get(model_id, {"display_name": model_id, "cost_tier": "unknown"})