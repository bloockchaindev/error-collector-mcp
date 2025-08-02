"""Configuration service for loading and managing configuration."""

import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..config import Config, OpenRouterConfig, CollectionPreferences
from ..config.config_validator import ConfigValidator


logger = logging.getLogger(__name__)


class ConfigService:
    """Service for loading, validating, and managing configuration."""
    
    def __init__(self):
        self._config: Optional[Config] = None
        self._config_path: Optional[str] = None
    
    async def load_config(self, config_path: str) -> Config:
        """Load configuration from file with validation."""
        self._config_path = config_path
        
        try:
            config_data = await self._load_config_file(config_path)
            config = self._parse_config(config_data)
            await self._validate_and_prepare_config(config)
            
            self._config = config
            logger.info(f"Configuration loaded successfully from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
    
    async def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration data from JSON file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            logger.debug(f"Raw configuration loaded from {config_path}")
            return config_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read configuration file: {e}")
    
    def _parse_config(self, config_data: Dict[str, Any]) -> Config:
        """Parse configuration data into Config object."""
        try:
            # Apply environment variable overrides
            config_data = self._apply_env_overrides(config_data)
            
            # Create Config object with Pydantic validation
            config = Config(**config_data)
            
            logger.debug("Configuration parsed successfully")
            return config
            
        except Exception as e:
            raise ValueError(f"Configuration parsing failed: {e}")
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Load .env file if it exists
        self._load_env_file()
        
        # First, substitute ${VARIABLE} syntax in the config
        config_data = self._substitute_env_variables(config_data)
        
        # Then apply direct environment variable overrides
        config_data = self._apply_direct_env_overrides(config_data)
        
        return config_data
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_file = Path('.env')
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and not os.getenv(key):  # Don't override existing env vars
                                os.environ[key] = value
                logger.debug("Environment variables loaded from .env file")
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")
    
    def _substitute_env_variables(self, data: Any) -> Any:
        """Recursively substitute ${VARIABLE} patterns with environment variables."""
        if isinstance(data, dict):
            return {key: self._substitute_env_variables(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_variables(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VARIABLE} or ${VARIABLE:-default} patterns
            def replace_var(match):
                var_expr = match.group(1)
                if ':-' in var_expr:
                    var_name, default_value = var_expr.split(':-', 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    var_name = var_expr.strip()
                    env_value = os.getenv(var_name)
                    if env_value is None:
                        logger.warning(f"Environment variable {var_name} not found, keeping original value")
                        return match.group(0)  # Return original ${VAR} if not found
                    return env_value
            
            return re.sub(r'\$\{([^}]+)\}', replace_var, data)
        else:
            return data
    
    def _apply_direct_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply direct environment variable overrides using ERROR_COLLECTOR_ prefix."""
        # OpenRouter API key override
        api_key_env = os.getenv('ERROR_COLLECTOR_OPENROUTER__API_KEY') or os.getenv('OPENROUTER_API_KEY')
        if api_key_env:
            if 'openrouter' not in config_data:
                config_data['openrouter'] = {}
            config_data['openrouter']['api_key'] = api_key_env
            logger.debug("OpenRouter API key overridden from environment")
        
        # Log level override
        log_level_env = os.getenv('ERROR_COLLECTOR_SERVER__LOG_LEVEL')
        if log_level_env:
            if 'server' not in config_data:
                config_data['server'] = {}
            config_data['server']['log_level'] = log_level_env.upper()
            logger.debug(f"Log level overridden from environment: {log_level_env}")
        
        # Data directory override
        data_dir_env = os.getenv('ERROR_COLLECTOR_STORAGE__DATA_DIRECTORY') or os.getenv('ERROR_COLLECTOR_DATA_DIR')
        if data_dir_env:
            if 'storage' not in config_data:
                config_data['storage'] = {}
            config_data['storage']['data_directory'] = data_dir_env
            logger.debug(f"Data directory overridden from environment: {data_dir_env}")
        
        # Server host override
        host_env = os.getenv('ERROR_COLLECTOR_SERVER__HOST')
        if host_env:
            if 'server' not in config_data:
                config_data['server'] = {}
            config_data['server']['host'] = host_env
            logger.debug(f"Server host overridden from environment: {host_env}")
        
        # Server port override
        port_env = os.getenv('ERROR_COLLECTOR_SERVER__PORT')
        if port_env:
            if 'server' not in config_data:
                config_data['server'] = {}
            try:
                config_data['server']['port'] = int(port_env)
                logger.debug(f"Server port overridden from environment: {port_env}")
            except ValueError:
                logger.warning(f"Invalid port value in environment: {port_env}")
        
        return config_data
    
    async def _validate_and_prepare_config(self, config: Config) -> None:
        """Validate configuration and prepare directories."""
        # Validate configuration
        is_valid, issues = ConfigValidator.get_validation_summary(config)
        
        if not is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(issues)
            suggestions = ConfigValidator.suggest_fixes(issues)
            if suggestions:
                error_msg += "\n\nSuggested fixes:\n" + "\n".join(f"- {fix}" for fix in suggestions)
            raise ValueError(error_msg)
        
        # Prepare data directory
        await self._prepare_data_directory(config.storage.data_directory)
        
        logger.info("Configuration validation passed")
    
    async def _prepare_data_directory(self, data_dir: str) -> None:
        """Create and prepare the data directory."""
        data_path = Path(data_dir).expanduser().resolve()
        
        try:
            # Create directory if it doesn't exist
            data_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (data_path / "errors").mkdir(exist_ok=True)
            (data_path / "summaries").mkdir(exist_ok=True)
            (data_path / "backups").mkdir(exist_ok=True)
            
            # Test write permissions
            test_file = data_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            logger.debug(f"Data directory prepared: {data_path}")
            
        except Exception as e:
            raise IOError(f"Failed to prepare data directory {data_path}: {e}")
    
    def get_config(self) -> Config:
        """Get the current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config
    
    def get_openrouter_config(self) -> OpenRouterConfig:
        """Get OpenRouter configuration."""
        return self.get_config().openrouter
    
    def get_collection_preferences(self) -> CollectionPreferences:
        """Get collection preferences."""
        return self.get_config().collection
    
    async def reload_config(self) -> Config:
        """Reload configuration from the same file."""
        if self._config_path is None:
            raise RuntimeError("No configuration file path available for reload")
        
        logger.info("Reloading configuration...")
        return await self.load_config(self._config_path)
    
    def is_source_enabled(self, source: str) -> bool:
        """Check if an error source is enabled."""
        return source in self.get_collection_preferences().enabled_sources
    
    def should_ignore_error(self, error_message: str, domain: Optional[str] = None) -> bool:
        """Check if an error should be ignored based on preferences."""
        prefs = self.get_collection_preferences()
        
        # Check ignored domains (for browser errors)
        if domain and any(ignored in domain for ignored in prefs.ignored_domains):
            return True
        
        # Check ignored error patterns
        import re
        for pattern in prefs.ignored_error_patterns:
            try:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return True
            except re.error:
                logger.warning(f"Invalid regex pattern ignored: {pattern}")
                continue
        
        return False
    
    def get_data_directory(self) -> Path:
        """Get the configured data directory as a Path object."""
        return Path(self.get_config().storage.data_directory).expanduser().resolve()
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as dictionary (without sensitive data)."""
        if self._config is None:
            raise RuntimeError("No configuration loaded")
        
        config_dict = self._config.dict()
        
        # Mask sensitive information
        if 'openrouter' in config_dict and 'api_key' in config_dict['openrouter']:
            api_key = config_dict['openrouter']['api_key']
            if len(api_key) > 8:
                config_dict['openrouter']['api_key'] = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
            else:
                config_dict['openrouter']['api_key'] = "*" * len(api_key)
        
        return config_dict