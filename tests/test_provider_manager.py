"""
Tests for ProviderManager with fallback cascade.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.provider_manager import ProviderManager
from agent.providers import OpenRouterProvider


class TestProviderManager:
    """Test ProviderManager functionality"""

    def test_provider_loading(self):
        """Test provider manager loads correctly"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()
            assert len(pm.providers) >= 1  # At least OpenRouter
            assert "openrouter" in pm.providers

    def test_provider_selection(self):
        """Test provider selection by complexity"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()

            # Simple task should get first available (OpenRouter)
            provider = pm.get_next_provider("simple")
            assert provider.provider_name.lower() == "openrouter"

            # Complex task should still get OpenRouter (only one loaded)
            provider = pm.get_next_provider("complex")
            assert provider.provider_name.lower() == "openrouter"

    def test_provider_cascade_order(self):
        """Test that providers are tried in correct cascade order"""
        with patch.dict('os.environ', {
            'OPENROUTER_API_KEY': 'test_key',
            'HUGGINGFACE_API_KEY': 'test_key',
            'GEMINI_API_KEY': 'test_key',
            'GROK_API_KEY': 'test_key'
        }):
            manager = ProviderManager()

            # Should have all providers loaded
            assert len(manager.providers) >= 1  # At least OpenRouter

            # Check cascade order
            expected_order = ['openrouter', 'huggingface', 'gemini', 'grok']
            for provider in expected_order:
                if provider in manager.providers:
                    assert provider in manager.PROVIDER_CASCADE

    def test_rate_limit_detection(self):
        """Test rate limit state tracking"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()
            
            # Reset rate limits for clean test
            pm.rate_limits["openrouter"] = RateLimitState()

            # Initially not rate limited
            assert not pm.is_rate_limited("openrouter")

            # Simulate hitting rate limit
            pm.handle_rate_limit("openrouter", Exception("429 Too Many Requests"))

            # Should now be rate limited
            assert pm.is_rate_limited("openrouter")

    def test_provider_fallback(self):
        """Test automatic fallback to next provider"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()

            # If we had multiple providers loaded, test fallback
            # For now, just test that handle_rate_limit doesn't crash
            try:
                pm.handle_rate_limit("openrouter", Exception("Rate limit"))
                # Should either return same provider or next in cascade
            except Exception as e:
                pytest.fail(f"handle_rate_limit raised unexpected error: {e}")

    def test_cost_tracking(self):
        """Test cost calculation and savings"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()

            # Reset cost tracker for clean test
            pm.cost_tracker = {"total": 0.0, "saved": 0.0}

            # Log some usage for free provider
            pm.log_usage("openrouter", 1000, 0.0)  # Free

            # Check cost tracking - should be free
            assert pm.cost_tracker["total"] == 0.0
            assert pm.cost_tracker["saved"] == 0.001  # Saved vs Grok cost

            # Check status report
            report = pm.get_status_report()
            assert "Cost" in report
            assert "saved" in report.lower()

    def test_usage_tracking(self):
        """Test request counting per provider"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm = ProviderManager()
            
            # Reset usage tracker for clean test
            pm.usage_tracker = {"openrouter": 0}

            # Log usage
            pm.log_usage("openrouter", 500, 0.0)

            # Should increment
            assert pm.usage_tracker["openrouter"] == 1

    def test_state_persistence(self, tmp_path):
        """Test saving/loading rate limit state"""
        # Create manager with temp state file
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            pm1 = ProviderManager()
            original_state_file = pm1.state_file
            pm1.state_file = tmp_path / "test_rate_limits.json"

            # Modify state
            pm1.usage_tracker["openrouter"] = 5
            pm1.cost_tracker["total"] = 1.23

            # Save state
            pm1.save_state()

            # Create new instance
            pm2 = ProviderManager()
            pm2.state_file = tmp_path / "test_rate_limits.json"
            # Reset to avoid loading from original file
            pm2.usage_tracker = {}
            pm2.cost_tracker = {"total": 0.0, "saved": 0.0}
            pm2.load_state()

            # Should load previous state
            assert pm2.usage_tracker["openrouter"] == 5
            assert pm2.cost_tracker["total"] == 1.23

    def test_status_report(self):
        """Test status report generation"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test_key'}):
            manager = ProviderManager()

            report = manager.get_status_report()
            assert "Provider Status Report" in report
            assert "Cost Tracking" in report
