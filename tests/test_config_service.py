"""Tests for configuration service."""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from error_collector_mcp.services.config_service import ConfigService
from error_collector_mcp.config import Config, OpenRouterConfig


class TestConfigService:
    """Test ConfigService functionality."""
    
    @pytest.fixture
    def config_service(self):
        """Create a ConfigService instance."""
        return ConfigService()
    
    @pytest.fixture
    def valid_config_data(self):
        """Valid configuration data."""
        return {
            "openrouter": {
                "api_key": "test-api-key-12345",
                "model": "meta-llama/llama-3.1-8b-instruct:free"
            },
            "collection": {
                "enabled_sources": ["browser", "terminal"],
                "max_errors_per_minute": 50
            },
            "storage": {
                "data_directory": tempfile.mkdtemp(),
                "max_errors_stored": 5000
            },
            "server": {
                "host": "localhost",
                "port": 8080
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, valid_config_data):
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_load_valid_config(self, config_service, temp_config_file):
        """Test loading a valid configuration file."""
        config = await config_service.load_config(temp_config_file)
        
        assert isinstance(config, Config)
        assert config.openrouter.api_key == "test-api-key-12345"
        assert config.collection.max_errors_per_minute == 50
        assert config.server.port == 8080
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, config_service):
        """Test loading a non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            await config_service.load_config("nonexistent.json")
    
    @pytest.mark.asyncio
    async def test_load_invalid_json(self, config_service):
        """Test loading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                await config_service.load_config(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_load_invalid_config_structure(self, config_service):
        """Test loading a config with invalid structure."""
        invalid_config = {
            "openrouter": {
                "api_key": "",  # Invalid: empty API key
                "model": "invalid-model-format"  # Invalid: no slash
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                await config_service.load_config(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_environment_variable_overrides(self, config_service, temp_config_file):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'ERROR_COLLECTOR_OPENROUTER__API_KEY': 'env-api-key',
            'ERROR_COLLECTOR_SERVER__LOG_LEVEL': 'DEBUG'
        }):
            config = await config_service.load_config(temp_config_file)
            
            assert config.openrouter.api_key == 'env-api-key'
            assert config.server.log_level.value == 'DEBUG'
    
    @pytest.mark.asyncio
    async def test_data_directory_creation(self, config_service, valid_config_data):
        """Test that data directory and subdirectories are created."""
        # Use a temporary directory that doesn't exist yet
        temp_dir = Path(tempfile.mkdtemp()) / "test_data"
        temp_dir.rmdir()  # Remove the directory so we can test creation
        
        valid_config_data["storage"]["data_directory"] = str(temp_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config_data, f)
            temp_path = f.name
        
        try:
            config = await config_service.load_config(temp_path)
            
            # Check that directories were created
            assert temp_dir.exists()
            assert (temp_dir / "errors").exists()
            assert (temp_dir / "summaries").exists()
            assert (temp_dir / "backups").exists()
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
            # Cleanup created directories
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_get_config_before_loading(self, config_service):
        """Test getting config before loading raises error."""
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            config_service.get_config()
    
    @pytest.mark.asyncio
    async def test_get_specific_configs(self, config_service, temp_config_file):
        """Test getting specific configuration sections."""
        await config_service.load_config(temp_config_file)
        
        openrouter_config = config_service.get_openrouter_config()
        assert isinstance(openrouter_config, OpenRouterConfig)
        assert openrouter_config.api_key == "test-api-key-12345"
        
        collection_prefs = config_service.get_collection_preferences()
        assert "browser" in collection_prefs.enabled_sources
        assert "terminal" in collection_prefs.enabled_sources
    
    @pytest.mark.asyncio
    async def test_is_source_enabled(self, config_service, temp_config_file):
        """Test checking if error sources are enabled."""
        await config_service.load_config(temp_config_file)
        
        assert config_service.is_source_enabled("browser")
        assert config_service.is_source_enabled("terminal")
        assert not config_service.is_source_enabled("nonexistent")
    
    @pytest.mark.asyncio
    async def test_should_ignore_error(self, config_service, valid_config_data):
        """Test error ignoring logic."""
        # Add some ignore patterns
        valid_config_data["collection"]["ignored_error_patterns"] = [
            r"ResizeObserver.*loop",
            r"Non-Error promise rejection"
        ]
        valid_config_data["collection"]["ignored_domains"] = [
            "chrome-extension://",
            "example.com"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_config_data, f)
            temp_path = f.name
        
        try:
            await config_service.load_config(temp_path)
            
            # Test pattern matching
            assert config_service.should_ignore_error("ResizeObserver loop limit exceeded")
            assert config_service.should_ignore_error("Non-Error promise rejection captured")
            assert not config_service.should_ignore_error("TypeError: Cannot read property")
            
            # Test domain matching
            assert config_service.should_ignore_error("Some error", "chrome-extension://abc123")
            assert config_service.should_ignore_error("Some error", "https://example.com/page")
            assert not config_service.should_ignore_error("Some error", "https://mysite.com")
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_reload_config(self, config_service, temp_config_file):
        """Test configuration reloading."""
        # Load initial config
        config1 = await config_service.load_config(temp_config_file)
        original_port = config1.server.port
        
        # Modify the config file
        with open(temp_config_file, 'r') as f:
            config_data = json.load(f)
        config_data["server"]["port"] = 9999
        with open(temp_config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Reload config
        config2 = await config_service.reload_config()
        
        assert config2.server.port == 9999
        assert config2.server.port != original_port
    
    @pytest.mark.asyncio
    async def test_export_config_masks_sensitive_data(self, config_service, temp_config_file):
        """Test that exported config masks sensitive information."""
        await config_service.load_config(temp_config_file)
        
        exported = config_service.export_config()
        
        # API key should be masked
        api_key = exported["openrouter"]["api_key"]
        assert "*" in api_key
        assert api_key != "test-api-key-12345"
        assert api_key.startswith("test")
        assert api_key.endswith("2345")
    
    @pytest.mark.asyncio
    async def test_get_data_directory(self, config_service, temp_config_file):
        """Test getting data directory as Path object."""
        await config_service.load_config(temp_config_file)
        
        data_dir = config_service.get_data_directory()
        assert isinstance(data_dir, Path)
        assert data_dir.exists()


class TestConfigValidator:
    """Test configuration validation."""
    
    def test_validate_openrouter_config(self):
        """Test OpenRouter configuration validation."""
        from error_collector_mcp.config.config_validator import ConfigValidator
        
        # Valid config
        valid_config = OpenRouterConfig(api_key="valid-api-key-12345")
        issues = ConfigValidator.validate_openrouter_config(valid_config)
        assert len(issues) == 0
        
        # Invalid config
        invalid_config = OpenRouterConfig(
            api_key="short",
            base_url="invalid-url",
            model="invalid-model",
            max_tokens=-1,
            temperature=3.0
        )
        issues = ConfigValidator.validate_openrouter_config(invalid_config)
        assert len(issues) > 0
        assert any("API key" in issue for issue in issues)
        assert any("base URL" in issue for issue in issues)
        assert any("model name" in issue for issue in issues)
        assert any("max_tokens" in issue for issue in issues)
        assert any("temperature" in issue for issue in issues)
    
    def test_suggest_fixes(self):
        """Test fix suggestions for common issues."""
        from error_collector_mcp.config.config_validator import ConfigValidator
        
        issues = [
            "OpenRouter API key appears to be invalid",
            "Invalid OpenRouter base URL",
            "Invalid model name format",
            "Invalid regex pattern"
        ]
        
        suggestions = ConfigValidator.suggest_fixes(issues)
        assert len(suggestions) > 0
        assert any("openrouter.ai" in suggestion for suggestion in suggestions)
        assert any("regex101.com" in suggestion for suggestion in suggestions)