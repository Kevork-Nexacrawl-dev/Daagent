"""
LLM Provider abstraction layer for multi-provider support.
"""

from abc import ABC, abstractmethod
from typing import Any
from openai import OpenAI


class LLMProvider(ABC):
    """Abstract base for LLM providers"""

    @abstractmethod
    def get_client(self) -> Any:
        """Return configured API client"""
        pass

    @abstractmethod
    def get_model_name(self, task_type: str) -> str:
        """Return model for given task type"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name"""
        pass


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.models = {
            "conversational": "nex-agi/deepseek-v3.1-nex-n1:free",
            "code_editing": "nex-agi/deepseek-v3.1-nex-n1:free"
        }

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self, task_type: str) -> str:
        from agent.config import Config
        if Config.OVERRIDE_MODEL:
            return Config.OVERRIDE_MODEL
        return self.models.get(task_type, self.models["conversational"])

    @property
    def provider_name(self) -> str:
        return "OpenRouter"


class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api-inference.huggingface.co/v1"
        self.models = {
            "conversational": "meta-llama/Llama-3.3-70B-Instruct",
            "code_editing": "meta-llama/Llama-3.3-70B-Instruct"
        }

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self, task_type: str) -> str:
        from agent.config import Config
        if Config.OVERRIDE_MODEL:
            return Config.OVERRIDE_MODEL
        return self.models.get(task_type, self.models["conversational"])

    @property
    def provider_name(self) -> str:
        return "HuggingFace"


class TogetherProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.together.xyz/v1"
        self.models = {
            "conversational": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "code_editing": "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        }

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self, task_type: str) -> str:
        from agent.config import Config
        if Config.OVERRIDE_MODEL:
            return Config.OVERRIDE_MODEL
        return self.models.get(task_type, self.models["conversational"])

    @property
    def provider_name(self) -> str:
        return "Together.ai"


class GeminiProvider(LLMProvider):
    """Google Gemini provider with free tier access"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.models = {
            "conversational": "gemini-2.0-flash-exp",  # Free tier
            "code_editing": "gemini-2.0-flash-exp"
        }

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self, task_type: str) -> str:
        from agent.config import Config
        if Config.OVERRIDE_MODEL:
            return Config.OVERRIDE_MODEL
        return self.models.get(task_type, self.models["conversational"])

    @property
    def provider_name(self) -> str:
        return "Google Gemini"


class GrokProvider(LLMProvider):
    """Grok premium provider via OpenRouter"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.models = {
            "conversational": "x-ai/grok-4-fast",  # Paid fallback
            "code_editing": "x-ai/grok-4-fast"
        }

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self, task_type: str) -> str:
        from agent.config import Config
        if Config.OVERRIDE_MODEL:
            return Config.OVERRIDE_MODEL
        return self.models.get(task_type, self.models["conversational"])

    @property
    def provider_name(self) -> str:
        return "Grok Premium"


# Provider registry
PROVIDERS = {
    "openrouter": OpenRouterProvider,
    "huggingface": HuggingFaceProvider,
    "together": TogetherProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider
}