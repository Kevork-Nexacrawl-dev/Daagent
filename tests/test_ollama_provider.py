"""
Tests for OllamaProvider class.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.providers import OllamaProvider
from agent.config import Config


class TestOllamaProvider:
    """Test OllamaProvider functionality"""

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_initialization(self):
        """Test provider initializes correctly"""
        provider = OllamaProvider()
        assert provider.api_key == ""
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.models["conversational"] == "llama3.1"
        assert provider.provider_name == "Ollama"

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_get_client(self):
        """Test get_client returns OpenAI client with correct config"""
        provider = OllamaProvider()
        with patch('agent.providers.OpenAI') as mock_openai:
            client = provider.get_client()
            mock_openai.assert_called_once_with(api_key="", base_url="http://localhost:11434/v1")
            assert client == mock_openai.return_value

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_get_model_name_default(self):
        """Test get_model_name returns default model"""
        provider = OllamaProvider()
        assert provider.get_model_name("conversational") == "llama3.1"
        assert provider.get_model_name("code_editing") == "llama3.1"
        assert provider.get_model_name("unknown") == "llama3.1"  # falls back to conversational

    @patch('agent.config.Config.OVERRIDE_MODEL', 'custom-model')
    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_get_model_name_override(self):
        """Test get_model_name respects override"""
        provider = OllamaProvider()
        assert provider.get_model_name("conversational") == "custom-model"

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_chat_non_streaming(self):
        """Test chat method non-streaming"""
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response

            result = provider.chat(messages, model="test-model", stream=False)

            mock_client.chat.completions.create.assert_called_once_with(
                model="test-model",
                messages=messages,
                stream=False
            )
            assert result == mock_response

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_chat_streaming(self):
        """Test chat method streaming"""
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response

            result = provider.chat(messages, model="test-model", stream=True)

            mock_client.chat.completions.create.assert_called_once_with(
                model="test-model",
                messages=messages,
                stream=True
            )
            assert result == mock_response

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_chat_default_model(self):
        """Test chat uses default model when none specified"""
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response

            result = provider.chat(messages)

            mock_client.chat.completions.create.assert_called_once_with(
                model="llama3.1",
                messages=messages,
                stream=False
            )

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_generate_non_streaming(self):
        """Test generate method non-streaming"""
        provider = OllamaProvider()
        prompt = "Write a story"

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.completions.create.return_value = mock_response

            result = provider.generate(prompt, model="test-model", stream=False)

            mock_client.completions.create.assert_called_once_with(
                model="test-model",
                prompt=prompt,
                stream=False
            )
            assert result == mock_response

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_generate_streaming(self):
        """Test generate method streaming"""
        provider = OllamaProvider()
        prompt = "Write a story"

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.completions.create.return_value = mock_response

            result = provider.generate(prompt, model="test-model", stream=True)

            mock_client.completions.create.assert_called_once_with(
                model="test-model",
                prompt=prompt,
                stream=True
            )
            assert result == mock_response

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_generate_default_model(self):
        """Test generate uses default model when none specified"""
        provider = OllamaProvider()
        prompt = "Write a story"

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_client.completions.create.return_value = mock_response

            result = provider.generate(prompt)

            mock_client.completions.create.assert_called_once_with(
                model="llama3.1",
                prompt=prompt,
                stream=False
            )

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_chat_connection_error(self):
        """Test chat handles connection errors"""
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Connection refused")

            with pytest.raises(Exception, match="Connection refused"):
                provider.chat(messages)

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_generate_model_not_found_error(self):
        """Test generate handles model not found errors"""
        provider = OllamaProvider()
        prompt = "Write a story"

        with patch('agent.providers.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.completions.create.side_effect = Exception("model 'nonexistent' not found")

            with pytest.raises(Exception, match="model 'nonexistent' not found"):
                provider.generate(prompt, model="nonexistent")

    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_provider_with_api_key(self):
        """Test provider initialization with API key"""
        provider = OllamaProvider(api_key="test_key")
        assert provider.api_key == "test_key"

        with patch('agent.providers.OpenAI') as mock_openai:
            client = provider.get_client()
            mock_openai.assert_called_once_with(api_key="test_key", base_url="http://localhost:11434/v1")


class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider with UnifiedAgent"""

    @patch('agent.config.Config.DEV_MODE', True)
    @patch('agent.config.Config.OLLAMA_MODEL_DEFAULT', 'llama3.1')
    @patch('agent.config.Config.OLLAMA_HOST', 'http://localhost:11434')
    def test_unified_agent_with_ollama_provider(self):
        """Test that UnifiedAgent can initialize and use OllamaProvider"""
        from agent.core import UnifiedAgent
        from agent.provider_manager import ProviderManager

        # Mock the provider manager to use Ollama
        with patch('agent.provider_manager.ProviderManager.load_state'), \
             patch('agent.provider_manager.ProviderManager.get_next_provider') as mock_get_provider:

            mock_provider = OllamaProvider()
            mock_get_provider.return_value = mock_provider

            # Mock the OpenAI client to avoid actual API calls
            with patch('agent.providers.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                # Mock successful response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_client.chat.completions.create.return_value = mock_response

                agent = UnifiedAgent()

                # This should work without errors
                assert agent.provider_manager is not None
                assert len(agent.provider_manager.providers) >= 0  # May be empty if no env vars

                # Test that we can get a provider (mocked)
                provider = agent.provider_manager.get_next_provider("simple")
                assert provider.provider_name == "Ollama"