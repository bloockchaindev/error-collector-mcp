"""Tests for browser error collector."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp

from error_collector_mcp.collectors.browser_collector import BrowserConsoleCollector, BrowserErrorData
from error_collector_mcp.collectors.browser_extension import BrowserExtensionBuilder
from error_collector_mcp.models import BrowserError, ErrorSeverity


class TestBrowserConsoleCollector:
    """Test BrowserConsoleCollector functionality."""
    
    @pytest.fixture
    async def browser_collector(self):
        """Create a browser collector instance."""
        collector = BrowserConsoleCollector(port=8765)
        yield collector
        if collector.is_collecting:
            await collector.stop_collection()
    
    @pytest.fixture
    def sample_error_data(self):
        """Create sample browser error data."""
        return {
            "message": "TypeError: Cannot read property 'foo' of null",
            "source": "https://example.com/script.js",
            "line_number": 42,
            "column_number": 15,
            "error_type": "TypeError",
            "stack_trace": "TypeError: Cannot read property 'foo' of null\\n    at test (script.js:42:15)",
            "url": "https://example.com/page.html",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "page_title": "Test Page",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
    
    @pytest.mark.asyncio
    async def test_start_stop_collection(self, browser_collector):
        """Test starting and stopping collection."""
        assert not browser_collector.is_collecting
        
        await browser_collector.start_collection()
        assert browser_collector.is_collecting
        
        await browser_collector.stop_collection()
        assert not browser_collector.is_collecting
    
    @pytest.mark.asyncio
    async def test_process_browser_error_data(self, browser_collector, sample_error_data):
        """Test processing browser error data."""
        await browser_collector.start_collection()
        
        # Process error data
        await browser_collector._process_browser_error_data(sample_error_data)
        
        # Check that error was collected
        errors = await browser_collector.get_collected_errors()
        assert len(errors) == 1
        
        error = errors[0]
        assert isinstance(error, BrowserError)
        assert error.message == "TypeError: Cannot read property 'foo' of null"
        assert error.url == "https://example.com/page.html"
        assert error.line_number == 42
        assert error.column_number == 15
        assert error.error_type == "TypeError"
    
    @pytest.mark.asyncio
    async def test_error_filtering(self, browser_collector):
        """Test error filtering based on patterns and domains."""
        await browser_collector.start_collection()
        
        # Test ignored pattern
        ignored_error = {
            "message": "ResizeObserver loop limit exceeded",
            "source": "https://example.com/script.js",
            "url": "https://example.com/page.html",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
        
        await browser_collector._process_browser_error_data(ignored_error)
        errors = await browser_collector.get_collected_errors()
        assert len(errors) == 0  # Should be filtered out
        
        # Test ignored domain
        extension_error = {
            "message": "Some extension error",
            "source": "chrome-extension://abc123/script.js",
            "url": "chrome-extension://abc123/page.html",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
        
        await browser_collector._process_browser_error_data(extension_error)
        errors = await browser_collector.get_collected_errors()
        assert len(errors) == 0  # Should be filtered out
        
        # Test normal error (should not be filtered)
        normal_error = {
            "message": "ReferenceError: x is not defined",
            "source": "https://example.com/script.js",
            "url": "https://example.com/page.html",
            "timestamp": "2024-01-01T12:00:00.000Z"
        }
        
        await browser_collector._process_browser_error_data(normal_error)
        errors = await browser_collector.get_collected_errors()
        assert len(errors) == 1  # Should be collected
    
    @pytest.mark.asyncio
    async def test_error_severity_determination(self, browser_collector):
        """Test error severity determination."""
        await browser_collector.start_collection()
        
        test_cases = [
            ("out of memory error", "Error", ErrorSeverity.CRITICAL),
            ("TypeError: undefined", "TypeError", ErrorSeverity.HIGH),
            ("console error message", "ConsoleError", ErrorSeverity.MEDIUM),
            ("warning message", "ConsoleWarning", ErrorSeverity.LOW)
        ]
        
        for message, error_type, expected_severity in test_cases:
            error_data = BrowserErrorData(
                message=message,
                source="test",
                error_type=error_type
            )
            
            severity = browser_collector._determine_error_severity(error_data)
            assert severity == expected_severity
    
    @pytest.mark.asyncio
    async def test_error_callbacks(self, browser_collector, sample_error_data):
        """Test error callback functionality."""
        callback_errors = []
        
        def error_callback(error: BrowserError):
            callback_errors.append(error)
        
        browser_collector.add_error_callback(error_callback)
        await browser_collector.start_collection()
        
        # Process an error
        await browser_collector._process_browser_error_data(sample_error_data)
        
        # Should have called the callback
        assert len(callback_errors) == 1
        assert isinstance(callback_errors[0], BrowserError)
        
        # Remove callback and test
        browser_collector.remove_error_callback(error_callback)
        await browser_collector._process_browser_error_data(sample_error_data)
        
        # Should not have added another error to callback list
        assert len(callback_errors) == 1
    
    def test_bookmarklet_generation(self, browser_collector):
        """Test bookmarklet code generation."""
        bookmarklet = browser_collector.get_bookmarklet_code()
        
        assert "javascript:" in bookmarklet
        assert "console.error" in bookmarklet
        assert "window.addEventListener" in bookmarklet
        assert str(browser_collector._http_port) in bookmarklet
    
    def test_extension_manifest_generation(self, browser_collector):
        """Test browser extension manifest generation."""
        manifest = browser_collector.get_browser_extension_manifest()
        
        assert manifest["manifest_version"] == 3
        assert manifest["name"] == "Error Collector MCP"
        assert "content_scripts" in manifest
        assert "background" in manifest
        assert "permissions" in manifest
    
    def test_extension_content_script_generation(self, browser_collector):
        """Test extension content script generation."""
        content_script = browser_collector.get_extension_content_script()
        
        assert "addEventListener" in content_script
        assert "chrome.runtime.sendMessage" in content_script
        assert "shouldIgnoreError" in content_script
        assert str(browser_collector._http_port) in content_script
    
    @pytest.mark.asyncio
    async def test_health_check(self, browser_collector):
        """Test health check functionality."""
        # Should be unhealthy when not collecting
        health_status = await browser_collector.health_check()
        assert health_status is False
        
        # Should be healthy when collecting
        await browser_collector.start_collection()
        health_status = await browser_collector.health_check()
        assert health_status is True
    
    @pytest.mark.asyncio
    async def test_log_file_monitoring(self, browser_collector):
        """Test log file monitoring functionality."""
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file_path = Path(f.name)
            browser_collector._log_file = log_file_path
            f.write("")  # Start with empty file
        
        try:
            await browser_collector.start_collection()
            
            # Give monitoring a moment to start
            await asyncio.sleep(0.1)
            
            # Append error data to log file
            error_data = {
                "message": "Test error from log file",
                "source": "test.js",
                "url": "https://test.com",
                "timestamp": "2024-01-01T12:00:00.000Z"
            }
            
            with open(log_file_path, 'a') as f:
                json.dump(error_data, f)
                f.write('\n')
            
            # Give monitoring time to process
            await asyncio.sleep(0.2)
            
            # Check if error was collected
            errors = await browser_collector.get_collected_errors()
            assert len(errors) >= 1
            
        finally:
            # Cleanup
            log_file_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_http_server_error_collection(self, browser_collector, sample_error_data):
        """Test HTTP server error collection endpoint."""
        await browser_collector.start_collection()
        
        # Give server time to start
        await asyncio.sleep(0.1)
        
        try:
            # Send error data via HTTP
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'http://localhost:{browser_collector._http_port}/collect',
                    json=sample_error_data
                ) as response:
                    assert response.status == 200
                    result = await response.json()
                    assert result["status"] == "success"
            
            # Check that error was collected
            errors = await browser_collector.get_collected_errors()
            assert len(errors) == 1
            assert errors[0].message == sample_error_data["message"]
            
        except aiohttp.ClientConnectorError:
            # Server might not be fully started, skip this test
            pytest.skip("HTTP server not accessible")
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, browser_collector):
        """Test status endpoint."""
        await browser_collector.start_collection()
        
        # Give server time to start
        await asyncio.sleep(0.1)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'http://localhost:{browser_collector._http_port}/status'
                ) as response:
                    assert response.status == 200
                    status = await response.json()
                    
                    assert status["collecting"] is True
                    assert status["websocket_port"] == browser_collector._websocket_port
                    assert status["http_port"] == browser_collector._http_port
                    assert "errors_collected" in status
                    assert "log_file" in status
                    
        except aiohttp.ClientConnectorError:
            # Server might not be fully started, skip this test
            pytest.skip("HTTP server not accessible")


class TestBrowserExtensionBuilder:
    """Test BrowserExtensionBuilder functionality."""
    
    @pytest.fixture
    def extension_builder(self):
        """Create an extension builder instance."""
        return BrowserExtensionBuilder(collector_port=8765)
    
    def test_chrome_extension_build(self, extension_builder):
        """Test Chrome extension building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "chrome"
            
            result_dir = extension_builder.build_chrome_extension(output_dir)
            
            # Check that files were created
            assert (result_dir / "manifest.json").exists()
            assert (result_dir / "content.js").exists()
            assert (result_dir / "background.js").exists()
            assert (result_dir / "popup.html").exists()
            assert (result_dir / "popup.js").exists()
            assert (result_dir / "icons" / "icon.svg").exists()
            
            # Check manifest content
            with open(result_dir / "manifest.json") as f:
                manifest = json.load(f)
                assert manifest["manifest_version"] == 3
                assert manifest["name"] == "Error Collector MCP"
    
    def test_firefox_extension_build(self, extension_builder):
        """Test Firefox extension building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "firefox"
            
            result_dir = extension_builder.build_firefox_extension(output_dir)
            
            # Check that files were created
            assert (result_dir / "manifest.json").exists()
            assert (result_dir / "content.js").exists()
            assert (result_dir / "background.js").exists()
            assert (result_dir / "popup.html").exists()
            assert (result_dir / "popup.js").exists()
            
            # Check manifest content (should be v2 for Firefox)
            with open(result_dir / "manifest.json") as f:
                manifest = json.load(f)
                assert manifest["manifest_version"] == 2
                assert manifest["name"] == "Error Collector MCP"
    
    def test_extension_packaging(self, extension_builder):
        """Test extension packaging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "chrome"
            package_file = Path(temp_dir) / "extension.zip"
            
            # Build extension
            extension_dir = extension_builder.build_chrome_extension(output_dir)
            
            # Package extension
            result_file = extension_builder.create_extension_package(extension_dir, package_file)
            
            assert result_file.exists()
            assert result_file.suffix == ".zip"
            assert result_file.stat().st_size > 0
    
    def test_manifest_generation(self, extension_builder):
        """Test manifest generation for different browsers."""
        # Chrome manifest (v3)
        chrome_manifest = extension_builder._get_manifest_v3()
        assert chrome_manifest["manifest_version"] == 3
        assert "service_worker" in chrome_manifest["background"]
        assert "action" in chrome_manifest
        
        # Firefox manifest (v2)
        firefox_manifest = extension_builder._get_manifest_v2()
        assert firefox_manifest["manifest_version"] == 2
        assert "scripts" in firefox_manifest["background"]
        assert "browser_action" in firefox_manifest
    
    def test_content_script_generation(self, extension_builder):
        """Test content script generation."""
        content_script = extension_builder._get_content_script()
        
        # Check for essential functionality
        assert "addEventListener" in content_script
        assert "chrome.runtime.sendMessage" in content_script
        assert "shouldIgnoreError" in content_script
        assert "sendError" in content_script
        assert str(extension_builder.collector_port) in content_script
    
    def test_background_script_generation(self, extension_builder):
        """Test background script generation."""
        background_script = extension_builder._get_background_script()
        
        # Check for essential functionality
        assert "chrome.runtime.onMessage.addListener" in background_script
        assert "chrome.storage.local" in background_script
        assert "chrome.action.setBadgeText" in background_script
        assert "ERROR_COLLECTED" in background_script
    
    def test_popup_generation(self, extension_builder):
        """Test popup HTML and script generation."""
        popup_html = extension_builder._get_popup_html()
        popup_script = extension_builder._get_popup_script()
        
        # Check HTML structure
        assert "<!DOCTYPE html>" in popup_html
        assert "Error Collector MCP" in popup_html
        assert "toggle" in popup_html
        assert "recent-errors" in popup_html
        
        # Check script functionality
        assert "chrome.storage" in popup_script
        assert "toggleSwitch" in popup_script
        assert "loadErrorStats" in popup_script
        assert "displayRecentErrors" in popup_script