"""
Intelligent Provider Manager with Fallback Cascade.

Manages multiple LLM providers with automatic failover, rate limit tracking,
and cost optimization.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from agent.providers import LLMProvider, PROVIDERS
from agent.config import Config


@dataclass
class RateLimitState:
    """Rate limit tracking for a provider"""
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    last_reset_minute: datetime = None
    last_reset_hour: datetime = None

    def __post_init__(self):
        if self.last_reset_minute is None:
            self.last_reset_minute = datetime.now()
        if self.last_reset_hour is None:
            self.last_reset_hour = datetime.now()


@dataclass
class ProviderLimits:
    """Rate limits for each provider"""
    requests_per_minute: int
    requests_per_hour: int


class ProviderManager:
    """
    Manages provider selection with intelligent fallback cascade.

    Provider Priority Order:
    1. OpenRouter Free (nex-agi/deepseek-v3.1-nex-n1:free) - 20/min
    2. HuggingFace (meta-llama/Llama-3.3-70B-Instruct) - ~100/hour
    3. Google Gemini (gemini-2.0-flash-exp) - 60/min free
    4. Grok Premium (x-ai/grok-4-fast) - Paid fallback
    """

    # Provider cascade order with limits
    PROVIDER_CASCADE = {
        "openrouter": ProviderLimits(requests_per_minute=20, requests_per_hour=100),
        "huggingface": ProviderLimits(requests_per_minute=60, requests_per_hour=100),
        "gemini": ProviderLimits(requests_per_minute=60, requests_per_hour=1000),
        "grok": ProviderLimits(requests_per_minute=100, requests_per_hour=1000),  # Paid fallback
    }

    # Cost estimates per 1K tokens (approximate)
    COST_ESTIMATES = {
        "openrouter": 0.0,  # Free
        "huggingface": 0.0,  # Free tier
        "gemini": 0.0,       # Free tier
        "grok": 0.001,       # ~$1 per 1M tokens
    }

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.rate_limits: Dict[str, RateLimitState] = {}
        self.usage_tracker: Dict[str, int] = {}
        self.cost_tracker = {"total": 0.0, "saved": 0.0}
        self.state_file = Path("memory-bank/rate_limits.json")

        # Load available providers
        self._load_providers()

        # Load previous state
        self.load_state()

    def _load_providers(self) -> Dict[str, LLMProvider]:
        """Load all configured providers in cascade order"""
        loaded_providers = {}

        for provider_name in self.PROVIDER_CASCADE.keys():
            try:
                provider = self._create_provider(provider_name)
                if provider:
                    loaded_providers[provider_name] = provider
                    self.rate_limits[provider_name] = RateLimitState()
                    self.usage_tracker[provider_name] = 0
                    print(f"✓ Loaded provider: {provider_name}")
            except Exception as e:
                print(f"⚠️ Failed to load {provider_name}: {e}")

        if not loaded_providers:
            raise RuntimeError("No providers could be loaded!")

        self.providers = loaded_providers
        return loaded_providers

    def _create_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Create provider instance with API key validation"""
        if provider_name not in PROVIDERS:
            return None

        provider_class = PROVIDERS[provider_name]

        # Get API key based on provider
        api_key = self._get_api_key(provider_name)
        if not api_key:
            return None

        return provider_class(api_key)

    def _get_api_key(self, provider_name: str) -> Optional[str]:
        """Get API key for provider"""
        key_map = {
            "openrouter": Config.OPENROUTER_API_KEY,
            "huggingface": Config.HUGGINGFACE_API_KEY,
            "gemini": getattr(Config, 'GEMINI_API_KEY', None),
            "grok": getattr(Config, 'GROK_API_KEY', None),
        }
        return key_map.get(provider_name)

    def get_next_provider(self, task_complexity: str = "medium") -> LLMProvider:
        """
        Select optimal provider based on complexity and availability.

        Args:
            task_complexity: "simple", "medium", or "complex"

        Returns:
            Best available provider
        """
        # Reset expired rate limits
        self._reset_expired_limits()

        # Try providers in cascade order
        for provider_name in self.PROVIDER_CASCADE.keys():
            if provider_name not in self.providers:
                continue

            if not self.is_rate_limited(provider_name):
                provider = self.providers[provider_name]

                # Log selection
                print(f"🎯 Selected provider: {provider.provider_name} "
                      f"(complexity: {task_complexity})")

                return provider

        # All providers rate limited - use highest priority available
        # (will hit rate limit but at least tries)
        fallback_provider = list(self.providers.values())[0]
        print(f"⚠️ All providers rate limited, using fallback: {fallback_provider.provider_name}")
        return fallback_provider

    def handle_rate_limit(self, provider_name: str, error: Exception) -> LLMProvider:
        """
        Called when rate limit hit, returns next available provider.

        Args:
            provider_name: Provider that hit rate limit
            error: The rate limit exception

        Returns:
            Next available provider
        """
        print(f"🚫 Rate limit hit on {provider_name}: {error}")

        # Mark this provider as rate limited (force cooldown)
        if provider_name in self.rate_limits:
            state = self.rate_limits[provider_name]
            state.requests_this_minute = self.PROVIDER_CASCADE[provider_name].requests_per_minute
            state.requests_this_hour = self.PROVIDER_CASCADE[provider_name].requests_per_hour

        # Get next provider
        next_provider = self.get_next_provider()

        if next_provider.provider_name != provider_name:
            print(f"🔄 Falling back to: {next_provider.provider_name}")
        else:
            print("⚠️ No alternative providers available")

        return next_provider

    def is_rate_limited(self, provider_name: str) -> bool:
        """
        Check if provider is currently rate limited.

        Uses 90% threshold to prevent hitting limits.
        """
        if provider_name not in self.PROVIDER_CASCADE:
            return True

        limits = self.PROVIDER_CASCADE[provider_name]
        state = self.rate_limits.get(provider_name)

        if not state:
            return False

        # Check minute limit (90% threshold)
        minute_threshold = int(limits.requests_per_minute * 0.9)
        if state.requests_this_minute >= minute_threshold:
            return True

        # Check hour limit (90% threshold)
        hour_threshold = int(limits.requests_per_hour * 0.9)
        if state.requests_this_hour >= hour_threshold:
            return True

        return False

    def log_usage(self, provider_name: str, tokens: int = 0, cost: float = 0.0):
        """
        Track API usage and calculate savings.

        Args:
            provider_name: Provider used
            tokens: Token count (approximate)
            cost: Actual cost incurred
        """
        # Update request counts
        if provider_name in self.rate_limits:
            state = self.rate_limits[provider_name]
            state.requests_this_minute += 1
            state.requests_this_hour += 1

        # Update usage tracker
        self.usage_tracker[provider_name] = self.usage_tracker.get(provider_name, 0) + 1

        # Calculate estimated cost
        estimated_cost = (tokens / 1000) * self.COST_ESTIMATES.get(provider_name, 0.001)

        # Track actual cost if provided, otherwise use estimate
        actual_cost = cost if cost > 0 else estimated_cost
        self.cost_tracker["total"] += actual_cost

        # Calculate savings (vs always using paid Grok)
        grok_cost = (tokens / 1000) * self.COST_ESTIMATES["grok"]
        self.cost_tracker["saved"] += max(0, grok_cost - actual_cost)

    def get_status_report(self) -> str:
        """Generate human-readable status report"""
        lines = ["📊 Provider Status Report", "=" * 40]

        # Provider usage
        lines.append("Provider Usage:")
        for provider_name, requests in self.usage_tracker.items():
            limits = self.PROVIDER_CASCADE.get(provider_name)
            if limits:
                rate_limited = "🚫" if self.is_rate_limited(provider_name) else "✅"
                lines.append(f"  {rate_limited} {provider_name}: {requests} requests "
                           f"({self.rate_limits[provider_name].requests_this_minute}/{limits.requests_per_minute} min)")

        # Cost tracking
        lines.append("")
        lines.append("Cost Tracking:")
        lines.append(f"Total Cost: ${self.cost_tracker['total']:.4f}")
        lines.append(f"Total Saved: ${self.cost_tracker['saved']:.4f}")

        return "\n".join(lines)

    def _reset_expired_limits(self):
        """Reset rate limit counters for expired windows"""
        now = datetime.now()

        for provider_name, state in self.rate_limits.items():
            # Reset minute counter if needed
            if now - state.last_reset_minute >= timedelta(minutes=1):
                state.requests_this_minute = 0
                state.last_reset_minute = now

            # Reset hour counter if needed
            if now - state.last_reset_hour >= timedelta(hours=1):
                state.requests_this_hour = 0
                state.last_reset_hour = now

    def save_state(self):
        """Persist rate limit state to disk"""
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "providers": {},
            "usage_tracker": self.usage_tracker.copy(),
            "session_stats": {
                "total_requests": sum(self.usage_tracker.values()),
                "total_cost": self.cost_tracker["total"],
                "total_saved": self.cost_tracker["saved"]
            }
        }

        # Convert rate limit states to dict
        for provider_name, state in self.rate_limits.items():
            state_data["providers"][provider_name] = {
                "requests_this_minute": state.requests_this_minute,
                "requests_this_hour": state.requests_this_hour,
                "last_reset_minute": state.last_reset_minute.isoformat() if state.last_reset_minute else None,
                "last_reset_hour": state.last_reset_hour.isoformat() if state.last_reset_hour else None,
            }

        # Ensure directory exists
        self.state_file.parent.mkdir(exist_ok=True)

        # Save to file
        with open(self.state_file, 'w') as f:
            json.dump(state_data, f, indent=2)

    def load_state(self):
        """Load rate limit state from previous session"""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)

            # Load provider states
            for provider_name, state_dict in state_data.get("providers", {}).items():
                if provider_name in self.rate_limits:
                    state = self.rate_limits[provider_name]
                    state.requests_this_minute = state_dict.get("requests_this_minute", 0)
                    state.requests_this_hour = state_dict.get("requests_this_hour", 0)

                    # Parse timestamps
                    if state_dict.get("last_reset_minute"):
                        state.last_reset_minute = datetime.fromisoformat(state_dict["last_reset_minute"])
                    if state_dict.get("last_reset_hour"):
                        state.last_reset_hour = datetime.fromisoformat(state_dict["last_reset_hour"])

            # Load session stats
            session_stats = state_data.get("session_stats", {})
            self.cost_tracker["total"] = session_stats.get("total_cost", 0.0)
            self.cost_tracker["saved"] = session_stats.get("total_saved", 0.0)
            
            # Load usage tracker
            saved_usage = state_data.get("usage_tracker", {})
            for provider_name, usage in saved_usage.items():
                self.usage_tracker[provider_name] = usage

            print(f"✓ Loaded previous state from {self.state_file}")

        except Exception as e:
            print(f"⚠️ Failed to load state: {e}")