"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from error_collector_mcp.config import Config, OpenRouterConfig, CollectionPreferences


class TestOpenRouterConfig:
    """Test OpenRouter configuration."""
    
    def test_valid_config(self):
        """Test valid OpenRouter configuration."""
        config = OpenRouterConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.model == "meta-llama/llama-3.1-8b-instruct:free"
    
    def test_empty_api_key_raises_error(self):
        """Test that empty API key raises validation error."""
        with pytest.raises(ValidationError):
            OpenRouterConfig(api_key="")
    
    def test_whitespace_api_key_stripped(self):
        """Test that whitespace in API key is stripped."""
        config = OpenRouterConfig(api_key="  test-key  ")
        assert config.api_key == "test-key"


class TestCollectionPreferences:
    """Test collection preferences."""
    
    def test_default_preferences(self):
        """Test default collection preferences."""
        prefs = CollectionPreferences()
        assert "browser" in prefs.enabled_sources
        assert "terminal" in prefs.enabled_sources
        assert prefs.auto_summarize is True
        assert prefs.group_similar_errors is True


class TestConfig:
    """Test main configuration."""
    
    def test_valid_config(self):
        """Test valid complete configuration."""
        config = Config(
            openrouter=OpenRouterConfig(api_key="test-key")
        )
        assert config.openrouter.api_key == "test-key"
        assert config.collection.auto_summarize is True