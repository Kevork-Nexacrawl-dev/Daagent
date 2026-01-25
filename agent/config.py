import os
import sys
from dotenv import load_dotenv
from enum import Enum

load_dotenv(encoding='utf-8-sig')

class TaskType(Enum):
    """Task categories for model selection"""
    CONVERSATIONAL = "conversational"  # Research, Q&A, general reasoning
    CODE_EDITING = "code_editing"      # Multi-file edits, refactoring
    BROWSER_AUTOMATION = "browser"     # Job applications, web scraping

class Config:
    """Agent configuration with dynamic model selection"""
    
    # Development mode (uses free models)
    DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
    
    # Web mode detection
    WEB_MODE = os.getenv('DAAGENT_WEB_MODE') == '1'
    
    # Model override (CLI flag)
    OVERRIDE_MODEL = None
    
    # Provider selection (NEW)
    PROVIDER = os.getenv("PROVIDER", "openrouter").lower()
    
    # Provider API keys (NEW)
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GROK_API_KEY = os.getenv("GROK_API_KEY", "")
    
    # Provider override from CLI (NEW)
    OVERRIDE_PROVIDER = None
    
    # OpenRouter settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Model assignments
    MODELS = {
        # Development (free)
        "dev": {
            TaskType.CONVERSATIONAL: "tngtech/deepseek-r1t2-chimera:free",
            TaskType.CODE_EDITING: "x-ai/grok-4-fast",  # Always use Grok for code editing
        },
        # Production (paid but optimized)
        "prod": {
            TaskType.CONVERSATIONAL: "deepseek-ai/DeepSeek-V3.2",
            TaskType.CODE_EDITING: "x-ai/grok-4-fast",  # Always use Grok for code editing
        }
    }
    
    # Anthropic (for browser automation only)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    
    # Ollama settings
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL_DEFAULT = os.getenv("OLLAMA_MODEL_DEFAULT", "llama3.2:latest")
    
    # Agent behavior
    # MAX_ITERATIONS: Controls ReAct loop depth
    # - 10: Simple QA and basic tasks
    # - 25: Complex research, multi-step analysis (default)
    # - 50+: Job applications, deep automation
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 25))  # Raised for complex tasks
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
    
    # MCP Warehouse integration
    MCP_WAREHOUSE_PATH = os.getenv(
        "MCP_WAREHOUSE_PATH",
        r"C:\Users\k\Documents\Projects\mcp-module-manager"
    )
    
    # Enable/disable MCP warehouse
    ENABLE_MCP = os.getenv("ENABLE_MCP", "true").lower() == "true"
    
    # Latency optimization settings
    ENABLE_QUERY_CLASSIFICATION = os.getenv("ENABLE_QUERY_CLASSIFICATION", "true").lower() == "true"
    ENABLE_RESPONSE_CACHE = os.getenv("ENABLE_RESPONSE_CACHE", "true").lower() == "true"
    ENABLE_LAZY_TOOLS = os.getenv("ENABLE_LAZY_TOOLS", "true").lower() == "true"
    CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", 24))
    
    # Streaming configuration
    ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    
    @classmethod
    def get_model_for_task(cls, task_type: TaskType) -> str:
        """Select appropriate model based on task type and mode"""
        if cls.OVERRIDE_MODEL:
            return cls.OVERRIDE_MODEL
        mode = "dev" if cls.DEV_MODE else "prod"
        return cls.MODELS[mode][task_type]
    
    @classmethod
    def get_openrouter_client(cls):
        """Get OpenAI-compatible OpenRouter client"""
        from openai import OpenAI
        return OpenAI(
            api_key=cls.OPENROUTER_API_KEY,
            base_url=cls.OPENROUTER_BASE_URL
        )
    
    @classmethod
    def get_anthropic_client(cls):
        """Get Anthropic client for Computer Use"""
        from anthropic import Anthropic
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY required for browser automation")
        return Anthropic(api_key=cls.ANTHROPIC_API_KEY)
    
    @classmethod
    def get_provider(cls, task_type: TaskType = None):
        """Get configured provider instance
        
        For code editing tasks, always use OpenRouter with Grok
        """
        from agent.providers import PROVIDERS
        
        provider_name = cls.OVERRIDE_PROVIDER or cls.PROVIDER
        
        # Force OpenRouter for code editing tasks
        if task_type == TaskType.CODE_EDITING:
            provider_name = "openrouter"
        
        if provider_name not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = PROVIDERS[provider_name]
        
        # Get appropriate API key
        if provider_name == "openrouter":
            api_key = cls.OPENROUTER_API_KEY
        elif provider_name == "huggingface":
            api_key = cls.HUGGINGFACE_API_KEY
        elif provider_name == "together":
            api_key = cls.TOGETHER_API_KEY
        elif provider_name == "gemini":
            api_key = cls.GEMINI_API_KEY
        elif provider_name == "grok":
            api_key = cls.GROK_API_KEY
        elif provider_name == "ollama":
            api_key = ""  # No API key needed for local Ollama
        else:
            raise ValueError(f"No API key configured for {provider_name}")
        
        if not api_key and provider_name != "ollama":
            raise ValueError(f"{provider_name.upper()}_API_KEY not found in .env")
        
        return provider_class(api_key)
    
    @classmethod
    def validate(cls):
        """Enhanced validation with provider check"""
        provider = cls.OVERRIDE_PROVIDER or cls.PROVIDER
        
        if provider not in ["openrouter", "huggingface", "together", "gemini", "grok", "ollama"]:
            raise ValueError(f"Invalid PROVIDER: {provider}")
        
        # Check that provider's API key exists
        if provider == "openrouter" and not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in .env")
        elif provider == "huggingface" and not cls.HUGGINGFACE_API_KEY:
            raise ValueError("HUGGINGFACE_API_KEY not found in .env")
        elif provider == "together" and not cls.TOGETHER_API_KEY:
            raise ValueError("TOGETHER_API_KEY not found in .env")
        elif provider == "gemini" and not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env")
        elif provider == "grok" and not cls.GROK_API_KEY:
            raise ValueError("GROK_API_KEY not found in .env")
        # Ollama doesn't require API key
        
        # Print validation info
        provider_obj = cls.get_provider()
        mode = "DEV" if cls.DEV_MODE else "PROD"
        if not cls.WEB_MODE:
            sys.stderr.write(f"✓ Config validated: {mode} mode, Provider: {provider_obj.provider_name}\n")
            sys.stderr.write(f"  - Conversational: {provider_obj.get_model_name('conversational')}\n")
            sys.stderr.write(f"  - Code Editing: {provider_obj.get_model_name('code_editing')}\n")
            sys.stderr.flush()
