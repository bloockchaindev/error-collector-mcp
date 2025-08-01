"""Configuration management for the error collector MCP."""

from .config_schema import Config, OpenRouterConfig, CollectionPreferences
from .config_validator import ConfigValidator

__all__ = [
    "Config",
    "OpenRouterConfig", 
    "CollectionPreferences",
    "ConfigValidator"
]