"""
Prompt layering system for fine-grained behavior control.
This is your "control panel" for agent personality.
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class PromptLayer:
    """A single prompt layer with priority"""
    name: str
    content: str
    priority: int  # Lower number = higher priority (executes first)


class PromptManager:
    """
    Manages prompt layers and composes final system prompt.
    Layers allow you to control agent behavior without touching core code.
    """
    
    def __init__(self):
        self.layers: List[PromptLayer] = []
        
        # Add default layers
        self._add_default_layers()
    
    def _add_default_layers(self):
        """Set up default prompt layers"""
        
        # Core identity (highest priority)
        self.add_layer(
            "core_identity",
            """You are a highly capable general-purpose AI agent.

You have access to multiple tools that allow you to:
- Search the web for current information
- Read and write files
- Execute code (coming soon)
- Control web browsers (coming soon)

You should proactively use the right tools to complete tasks effectively.""",
            priority=0
        )
        
        # Permissiveness layer (your special sauce)
        self.add_layer(
            "permissiveness",
            """BEHAVIORAL GUIDELINES:

- Be a DOER, not an ASKER. Take action rather than asking for permission.
- When uncertain, make reasonable assumptions and proceed.
- If multiple approaches exist, choose the most efficient one.
- Don't apologize excessively or hedge unnecessarily.
- If a task seems impossible with available tools, get creative with combinations.""",
            priority=10
        )
        
        # Tool usage guidelines
        self.add_layer(
            "tool_usage",
            """TOOL USAGE RULES:

- Use web_search for any information you don't have or that might have changed.
- Use read_file to access user's files when referenced.
- Use write_file to save outputs, logs, or generated content.
- Chain multiple tools if needed (search → analyze → write report).
- If a tool fails, try alternative approaches before giving up.""",
            priority=20
        )
    
    def add_layer(self, name: str, content: str, priority: int = 50):
        """Add or update a prompt layer"""
        
        # Remove existing layer with same name
        self.layers = [l for l in self.layers if l.name != name]
        
        # Add new layer
        self.layers.append(PromptLayer(name, content, priority))
        
        # Keep sorted by priority
        self.layers.sort(key=lambda x: x.priority)
    
    def remove_layer(self, name: str):
        """Remove a prompt layer by name"""
        self.layers = [l for l in self.layers if l.name != name]
    
    def get_layer(self, name: str) -> PromptLayer:
        """Get a specific layer"""
        for layer in self.layers:
            if layer.name == name:
                return layer
        raise ValueError(f"Layer '{name}' not found")
    
    def compose(self) -> str:
        """Compose final system prompt from all layers"""
        
        # Layers are already sorted by priority
        prompt_parts = [layer.content for layer in self.layers]
        
        # Join with double newlines
        final_prompt = "\n\n".join(prompt_parts)
        
        return final_prompt
    
    def inspect(self):
        """Print current prompt layers for debugging"""
        print("\n📋 Current Prompt Layers:")
        print("=" * 60)
        for layer in self.layers:
            print(f"\n[{layer.priority:02d}] {layer.name}")
            print("-" * 60)
            print(layer.content[:200] + "..." if len(layer.content) > 200 else layer.content)
        print("\n" + "=" * 60)