"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

from error_collector_mcp.config import Config, OpenRouterConfig


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file for testing."""
    config_data = {
        "openrouter": {
            "api_key": "test-api-key",
            "model": "meta-llama/llama-3.1-8b-instruct:free"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_config() -> Config:
    """Create a sample configuration for testing."""
    return Config(
        openrouter=OpenRouterConfig(api_key="test-api-key")
    )