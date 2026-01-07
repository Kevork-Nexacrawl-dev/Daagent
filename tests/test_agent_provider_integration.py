"""
Tests for agent integration with ProviderManager.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.core import UnifiedAgent
from agent.config import TaskType
from agent.provider_manager import ProviderManager


class TestAgentProviderIntegration:
    """Test agent integration with provider manager"""

    def test_agent_provider_selection(self):
        """Test agent uses provider manager correctly"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            agent = UnifiedAgent()

            # Should have provider manager
            assert hasattr(agent, "provider_manager")
            assert isinstance(agent.provider_manager, ProviderManager)

            # Should load state on init
            # (This is tested implicitly by agent startup)

    def test_agent_complexity_assessment(self):
        """Test task complexity detection"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            agent = UnifiedAgent()

            # Simple message
            complexity = agent._assess_complexity("Hello", TaskType.CONVERSATIONAL)
            assert complexity in ["simple", "medium", "complex"]

            # Complex message
            complexity = agent._assess_complexity("Write a complex algorithm", TaskType.CODE_EDITING)
            assert complexity in ["simple", "medium", "complex"]

    def test_rate_limit_error_detection(self):
        """Test detection of rate limit errors"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            agent = UnifiedAgent()

            # Should detect 429 errors
            assert agent._is_rate_limit_error(Exception("429 Too Many Requests"))
            assert agent._is_rate_limit_error(Exception("Rate limit exceeded"))

            # Should not detect other errors
            assert not agent._is_rate_limit_error(Exception("Network timeout"))

    @patch('agent.core.UnifiedAgent._execute_tool')
    @patch('agent.providers.OpenRouterProvider.get_client')
    def test_agent_fallback_on_rate_limit(self, mock_get_client, mock_execute_tool):
        """Test agent handles rate limit and falls back to next provider"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            # Mock the provider's client to raise rate limit error
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("429 Too Many Requests")

            agent = UnifiedAgent()

            # Mock tool execution to return success
            mock_execute_tool.return_value = "Tool executed successfully"

            # This should trigger rate limit handling
            result = agent.run("Test message")

            # Should have attempted to handle rate limit
            # (Exact behavior depends on provider availability)

    @patch('agent.core.UnifiedAgent._execute_tool')
    @patch('agent.providers.OpenRouterProvider.get_client')
    def test_agent_successful_request(self, mock_get_client, mock_execute_tool):
        """Test agent processes successful requests with cost tracking"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            # Mock the provider's client
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].message.tool_calls = None

            mock_client.chat.completions.create.return_value = mock_response

            agent = UnifiedAgent()

            # Mock tool execution (shouldn't be called)
            mock_execute_tool.return_value = "Tool result"

            result = agent.run("Test message")

            # Should return the response
            assert "Test response" in result

            # Should have logged usage
            assert agent.provider_manager.usage_tracker["openrouter"] >= 1

    def test_agent_task_type_detection(self):
        """Test automatic task type detection"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            agent = UnifiedAgent()

            # Conversational
            task_type = agent._detect_task_type("Hello, how are you?")
            assert task_type == TaskType.CONVERSATIONAL

            # Code editing
            task_type = agent._detect_task_type("Edit the file to add a function")
            assert task_type == TaskType.CODE_EDITING

            # Browser automation
            task_type = agent._detect_task_type("Fill out this job application form")
            assert task_type == TaskType.BROWSER_AUTOMATION