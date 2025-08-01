"""Configuration validation utilities."""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from .config_schema import Config, OpenRouterConfig, CollectionPreferences


class ConfigValidator:
    """Validates configuration values and provides helpful error messages."""
    
    @staticmethod
    def validate_openrouter_config(config: OpenRouterConfig) -> List[str]:
        """Validate OpenRouter configuration and return list of issues."""
        issues = []
        
        # Validate API key format
        if not config.api_key or len(config.api_key.strip()) < 10:
            issues.append("OpenRouter API key appears to be invalid (too short)")
        
        # Validate base URL
        try:
            parsed_url = urlparse(config.base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                issues.append(f"Invalid OpenRouter base URL: {config.base_url}")
        except Exception:
            issues.append(f"Malformed OpenRouter base URL: {config.base_url}")
        
        # Validate model name format
        if not config.model or "/" not in config.model:
            issues.append(f"Invalid model name format: {config.model}")
        
        # Validate numeric ranges
        if config.max_tokens <= 0 or config.max_tokens > 32000:
            issues.append(f"max_tokens should be between 1 and 32000, got {config.max_tokens}")
        
        if not (0.0 <= config.temperature <= 2.0):
            issues.append(f"temperature should be between 0.0 and 2.0, got {config.temperature}")
        
        if config.timeout <= 0 or config.timeout > 300:
            issues.append(f"timeout should be between 1 and 300 seconds, got {config.timeout}")
        
        if config.max_retries < 0 or config.max_retries > 10:
            issues.append(f"max_retries should be between 0 and 10, got {config.max_retries}")
        
        return issues
    
    @staticmethod
    def validate_collection_preferences(prefs: CollectionPreferences) -> List[str]:
        """Validate collection preferences and return list of issues."""
        issues = []
        
        # Validate enabled sources
        valid_sources = {"browser", "terminal"}
        invalid_sources = prefs.enabled_sources - valid_sources
        if invalid_sources:
            issues.append(f"Invalid error sources: {invalid_sources}. Valid sources: {valid_sources}")
        
        # Validate regex patterns
        for pattern in prefs.ignored_error_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                issues.append(f"Invalid regex pattern '{pattern}': {e}")
        
        # Validate numeric ranges
        if prefs.max_errors_per_minute <= 0 or prefs.max_errors_per_minute > 10000:
            issues.append(f"max_errors_per_minute should be between 1 and 10000, got {prefs.max_errors_per_minute}")
        
        if not (0.0 <= prefs.similarity_threshold <= 1.0):
            issues.append(f"similarity_threshold should be between 0.0 and 1.0, got {prefs.similarity_threshold}")
        
        return issues
    
    @staticmethod
    def validate_storage_config(storage_config) -> List[str]:
        """Validate storage configuration and return list of issues."""
        issues = []
        
        # Validate data directory
        data_dir = Path(storage_config.data_directory).expanduser()
        try:
            # Check if parent directory exists and is writable
            parent_dir = data_dir.parent
            if not parent_dir.exists():
                issues.append(f"Parent directory does not exist: {parent_dir}")
            elif not os.access(parent_dir, os.W_OK):
                issues.append(f"No write permission for directory: {parent_dir}")
        except Exception as e:
            issues.append(f"Invalid data directory path: {e}")
        
        # Validate numeric ranges
        if storage_config.max_errors_stored <= 0 or storage_config.max_errors_stored > 1000000:
            issues.append(f"max_errors_stored should be between 1 and 1000000, got {storage_config.max_errors_stored}")
        
        if storage_config.retention_days <= 0 or storage_config.retention_days > 3650:
            issues.append(f"retention_days should be between 1 and 3650, got {storage_config.retention_days}")
        
        return issues
    
    @staticmethod
    def validate_server_config(server_config) -> List[str]:
        """Validate server configuration and return list of issues."""
        issues = []
        
        # Validate host
        if not server_config.host:
            issues.append("Server host cannot be empty")
        
        # Validate port
        if not (1 <= server_config.port <= 65535):
            issues.append(f"Server port should be between 1 and 65535, got {server_config.port}")
        
        # Check if port is available (basic check)
        if server_config.port < 1024 and os.getuid() != 0:
            issues.append(f"Port {server_config.port} requires root privileges")
        
        # Validate concurrent requests
        if server_config.max_concurrent_requests <= 0 or server_config.max_concurrent_requests > 1000:
            issues.append(f"max_concurrent_requests should be between 1 and 1000, got {server_config.max_concurrent_requests}")
        
        return issues
    
    @classmethod
    def validate_config(cls, config: Config) -> Dict[str, List[str]]:
        """Validate entire configuration and return categorized issues."""
        validation_results = {
            "openrouter": cls.validate_openrouter_config(config.openrouter),
            "collection": cls.validate_collection_preferences(config.collection),
            "storage": cls.validate_storage_config(config.storage),
            "server": cls.validate_server_config(config.server)
        }
        
        return validation_results
    
    @classmethod
    def get_validation_summary(cls, config: Config) -> tuple[bool, List[str]]:
        """Get validation summary with overall status and all issues."""
        validation_results = cls.validate_config(config)
        
        all_issues = []
        for category, issues in validation_results.items():
            for issue in issues:
                all_issues.append(f"[{category}] {issue}")
        
        is_valid = len(all_issues) == 0
        return is_valid, all_issues
    
    @staticmethod
    def suggest_fixes(issues: List[str]) -> List[str]:
        """Suggest fixes for common configuration issues."""
        suggestions = []
        
        for issue in issues:
            if "API key" in issue and "invalid" in issue:
                suggestions.append("Get a valid API key from https://openrouter.ai/")
            elif "base URL" in issue:
                suggestions.append("Use the default OpenRouter URL: https://openrouter.ai/api/v1")
            elif "model name" in issue:
                suggestions.append("Use format: provider/model-name, e.g., 'meta-llama/llama-3.1-8b-instruct:free'")
            elif "regex pattern" in issue:
                suggestions.append("Check regex syntax at https://regex101.com/")
            elif "directory" in issue and "permission" in issue:
                suggestions.append("Create directory with: mkdir -p ~/.error-collector-mcp")
            elif "port" in issue and "privileges" in issue:
                suggestions.append("Use a port above 1024 or run with sudo")
        
        return list(set(suggestions))  # Remove duplicates