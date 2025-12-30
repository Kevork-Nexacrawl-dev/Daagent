"""
Basic tests to verify agent core functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import UnifiedAgent
from agent.config import Config, TaskType
from agent.prompts import PromptManager


def test_config():
    """Test configuration is valid"""
    print("\n🧪 Testing configuration...")
    Config.validate()
    print("✅ Config valid\n")


def test_prompt_manager():
    """Test prompt composition"""
    print("\n🧪 Testing prompt manager...")
    
    pm = PromptManager()
    
    # Add custom layer
    pm.add_layer("test_layer", "This is a test layer.", priority=99)
    
    # Inspect layers
    pm.inspect()
    
    # Compose prompt
    composed = pm.compose()
    assert "test_layer" in composed or "test layer" in composed.lower()
    
    print("✅ Prompt manager working\n")


def test_agent_initialization():
    """Test agent can be initialized"""
    print("\n🧪 Testing agent initialization...")
    
    agent = UnifiedAgent()
    
    # Check task detection
    assert agent._detect_task_type("Search for AI news") == TaskType.CONVERSATIONAL
    assert agent._detect_task_type("Refactor my code") == TaskType.CODE_EDITING
    assert agent._detect_task_type("Fill out this form") == TaskType.BROWSER_AUTOMATION
    
    print("✅ Agent initialized successfully\n")


if __name__ == "__main__":
    test_config()
    test_prompt_manager()
    test_agent_initialization()
    
    print("\n🎉 All basic tests passed!")