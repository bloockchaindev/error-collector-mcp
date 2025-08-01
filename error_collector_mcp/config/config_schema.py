"""Configuration schema definitions using Pydantic."""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field, validator
from enum import Enum


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OpenRouterConfig(BaseModel):
    """OpenRouter API configuration."""
    api_key: str = Field(..., description="OpenRouter API key")
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    model: str = Field(
        default="meta-llama/llama-3.1-8b-instruct:free",
        description="Model to use for summarization"
    )
    max_tokens: int = Field(default=1000, description="Maximum tokens for responses")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or not v.strip():
            raise ValueError("OpenRouter API key cannot be empty")
        return v.strip()


class CollectionPreferences(BaseModel):
    """Error collection preferences and filtering."""
    enabled_sources: Set[str] = Field(
        default={"browser", "terminal"},
        description="Enabled error sources"
    )
    ignored_error_patterns: List[str] = Field(
        default=[],
        description="Regex patterns for errors to ignore"
    )
    ignored_domains: List[str] = Field(
        default=[],
        description="Browser domains to ignore"
    )
    max_errors_per_minute: int = Field(
        default=100,
        description="Maximum errors to collect per minute"
    )
    auto_summarize: bool = Field(
        default=True,
        description="Automatically summarize new errors"
    )
    group_similar_errors: bool = Field(
        default=True,
        description="Group similar errors together"
    )
    similarity_threshold: float = Field(
        default=0.8,
        description="Threshold for grouping similar errors"
    )


class StorageConfig(BaseModel):
    """Storage configuration."""
    data_directory: str = Field(
        default="~/.error-collector-mcp",
        description="Directory for storing error data"
    )
    max_errors_stored: int = Field(
        default=10000,
        description="Maximum number of errors to store"
    )
    retention_days: int = Field(
        default=30,
        description="Days to retain error data"
    )
    backup_enabled: bool = Field(
        default=True,
        description="Enable automatic backups"
    )


class ServerConfig(BaseModel):
    """MCP server configuration."""
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    max_concurrent_requests: int = Field(
        default=10,
        description="Maximum concurrent requests"
    )


class Config(BaseModel):
    """Main configuration model."""
    openrouter: OpenRouterConfig
    collection: CollectionPreferences = Field(default_factory=CollectionPreferences)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    
    class Config:
        env_prefix = "ERROR_COLLECTOR_"
        env_nested_delimiter = "__"