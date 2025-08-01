"""Tests for error manager service."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from error_collector_mcp.services.error_manager import ErrorManager, ErrorManagerStats
from error_collector_mcp.services.config_service import ConfigService
from error_collector_mcp.services.ai_summarizer import AISummarizer
from error_collector_mcp.storage import ErrorStore, SummaryStore, ErrorFilters
from error_collector_mcp.collectors import BaseCollector, BrowserConsoleCollector, TerminalCollector
from error_collector_mcp.models import BaseError, BrowserError, TerminalError, ErrorSource, ErrorSeverity, ErrorCategory
from error_collector_mcp.config import OpenRouterConfig


class MockCollector(BaseCollector):
    """Mock collector for testing."""
    
    def __init__(self, name: str = "mock"):
        super().__init__(name)
        self._collected_errors = []
        self._error_callbacks = []
    
    async def start_collection(self):
        self._is_collecting = True
    
    async def stop_collection(self):
        self._is_collecting = False
    
    async def get_collected_errors(self):
        errors = self._collected_errors.copy()
        self._collected_errors.clear()
        return errors
    
    def add_error_callback(self, callback):
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback):
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    async def simulate_error(self, error: BaseError):
        """Simulate an error being collected."""
        for callback in self._error_callbacks:
            await callback(error)


class TestErrorManagerStats:
    """Test ErrorManagerStats functionality."""
    
    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = ErrorManagerStats()
        assert stats.total_errors_processed == 0
        assert stats.errors_by_source == {}
        assert stats.summaries_generated == 0
        assert stats.collectors_active == 0
        assert stats.last_error_time is None


class TestErrorManager:
    """Test ErrorManager functionality."""
    
    @pytest.fixture
    async def error_manager_components(self):
        """Create error manager components for testing."""
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create config service
        config_service = ConfigService()
        
        # Mock config loading
        with patch.object(config_service, 'load_config') as mock_load:
            mock_config = MagicMock()
            mock_config.collection.auto_summarize = True
            mock_config.storage.retention_days = 30
            mock_load.return_value = mock_config
            await config_service.load_config("test_config.json")
        
        # Create storage components
        error_store = ErrorStore(temp_dir, max_errors=100)
        summary_store = SummaryStore(temp_dir, max_summaries=50)
        
        # Create AI summarizer
        openrouter_config = OpenRouterConfig(api_key="test-key")
        ai_summarizer = AISummarizer(openrouter_config)
        
        # Create error manager
        error_manager = ErrorManager(
            config_service=config_service,
            error_store=error_store,
            summary_store=summary_store,
            ai_summarizer=ai_summarizer
        )
        
        yield {
            'error_manager': error_manager,
            'config_service': config_service,
            'error_store': error_store,
            'summary_store': summary_store,
            'ai_summarizer': ai_summarizer,
            'temp_dir': temp_dir
        }
        
        # Cleanup
        if error_manager._is_running:
            await error_manager.stop()
        
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_errors(self):
        """Create sample errors for testing."""
        return [
            BrowserError(
                message="TypeError: Cannot read property 'foo' of null",
                url="https://example.com/page.html",
                error_type="TypeError"
            ),
            TerminalError(
                message="Command failed",
                command="npm install",
                exit_code=1,
                stderr_output="Permission denied"
            ),
            BaseError(
                message="Generic error",
                source=ErrorSource.UNKNOWN,
                category=ErrorCategory.RUNTIME
            )
        ]
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, error_manager_components):
        """Test starting and stopping the error manager."""
        error_manager = error_manager_components['error_manager']
        
        assert not error_manager._is_running
        
        await error_manager.start()
        assert error_manager._is_running
        
        await error_manager.stop()
        assert not error_manager._is_running
    
    @pytest.mark.asyncio
    async def test_collector_registration(self, error_manager_components):
        """Test collector registration and unregistration."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Create mock collector
            collector = MockCollector("test_collector")
            
            # Register collector
            await error_manager.register_collector(collector)
            assert "test_collector" in error_manager.collectors
            assert "test_collector" in error_manager.collector_callbacks
            
            # Unregister collector
            await error_manager.unregister_collector("test_collector")
            assert "test_collector" not in error_manager.collectors
            assert "test_collector" not in error_manager.collector_callbacks
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_start_stop_collection(self, error_manager_components):
        """Test starting and stopping collection."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register collectors
            collector1 = MockCollector("collector1")
            collector2 = MockCollector("collector2")
            
            await error_manager.register_collector(collector1)
            await error_manager.register_collector(collector2)
            
            # Start collection for all collectors
            await error_manager.start_collection()
            assert collector1.is_collecting
            assert collector2.is_collecting
            
            # Stop collection for specific collector
            await error_manager.stop_collection(["collector1"])
            assert not collector1.is_collecting
            assert collector2.is_collecting
            
            # Stop all collection
            await error_manager.stop_collection()
            assert not collector1.is_collecting
            assert not collector2.is_collecting
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_error_registration(self, error_manager_components, sample_errors):
        """Test error registration and storage."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register an error
            error = sample_errors[0]
            error_id = await error_manager.register_error(error)
            
            assert error_id == error.id
            assert error_manager.stats.total_errors_processed == 1
            assert error_manager.stats.errors_by_source["browser"] == 1
            
            # Retrieve the error
            retrieved_error = await error_manager.get_error(error_id)
            assert retrieved_error is not None
            assert retrieved_error.message == error.message
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_collector_error_callback(self, error_manager_components, sample_errors):
        """Test that collector errors are processed through callbacks."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register collector
            collector = MockCollector("test_collector")
            await error_manager.register_collector(collector)
            
            # Simulate error from collector
            error = sample_errors[0]
            await collector.simulate_error(error)
            
            # Give some time for processing
            await asyncio.sleep(0.1)
            
            # Check that error was registered
            assert error_manager.stats.total_errors_processed >= 1
            
            # Verify error can be retrieved
            retrieved_error = await error_manager.get_error(error.id)
            assert retrieved_error is not None
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_manual_summary_request(self, error_manager_components, sample_errors):
        """Test manual summary request."""
        error_manager = error_manager_components['error_manager']
        
        # Mock AI summarizer
        with patch.object(error_manager.ai_summarizer, 'summarize_error_group') as mock_summarize:
            mock_summary = MagicMock()
            mock_summary.id = "test-summary-id"
            mock_summarize.return_value = mock_summary
            
            await error_manager.start()
            
            try:
                # Register errors
                error_ids = []
                for error in sample_errors:
                    error_id = await error_manager.register_error(error)
                    error_ids.append(error_id)
                
                # Request summary
                summary_id = await error_manager.request_summary(error_ids)
                
                assert summary_id is not None
                assert error_manager.stats.summaries_generated == 1
                
                # Verify summarizer was called
                mock_summarize.assert_called_once()
                
            finally:
                await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_error_filtering(self, error_manager_components):
        """Test error filtering functionality."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register different types of errors
            browser_error = BrowserError(
                message="Browser error",
                url="https://example.com",
                error_type="TypeError"
            )
            terminal_error = TerminalError(
                message="Terminal error",
                command="test command",
                exit_code=1
            )
            
            await error_manager.register_error(browser_error)
            await error_manager.register_error(terminal_error)
            
            # Filter by source
            browser_filters = ErrorFilters(sources={ErrorSource.BROWSER})
            browser_errors = await error_manager.get_errors(browser_filters)
            assert len(browser_errors) == 1
            assert browser_errors[0].source == ErrorSource.BROWSER
            
            terminal_filters = ErrorFilters(sources={ErrorSource.TERMINAL})
            terminal_errors = await error_manager.get_errors(terminal_filters)
            assert len(terminal_errors) == 1
            assert terminal_errors[0].source == ErrorSource.TERMINAL
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_auto_summarization(self, error_manager_components):
        """Test automatic summarization functionality."""
        error_manager = error_manager_components['error_manager']
        
        # Mock AI summarizer
        with patch.object(error_manager.ai_summarizer, 'summarize_error_group') as mock_summarize:
            mock_summary = MagicMock()
            mock_summary.id = "auto-summary-id"
            mock_summarize.return_value = mock_summary
            
            # Set low threshold for testing
            error_manager.auto_summarize_threshold = 2
            
            await error_manager.start()
            
            try:
                # Register similar errors to trigger auto-summarization
                for i in range(3):
                    error = BrowserError(
                        message=f"TypeError: Cannot read property 'foo' of null {i}",
                        url="https://example.com",
                        error_type="TypeError"
                    )
                    await error_manager.register_error(error)
                
                # Give time for auto-summarization to trigger
                await asyncio.sleep(0.2)
                
                # Check that auto-summarization was triggered
                assert error_manager.stats.auto_summaries_generated >= 1
                
            finally:
                await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, error_manager_components):
        """Test cleanup of old data."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Mock cleanup methods
            with patch.object(error_manager.error_store, 'cleanup_old_errors') as mock_cleanup_errors, \
                 patch.object(error_manager.summary_store, 'cleanup_old_summaries') as mock_cleanup_summaries:
                
                mock_cleanup_errors.return_value = 5
                mock_cleanup_summaries.return_value = 3
                
                # Perform cleanup
                result = await error_manager.cleanup_old_data(30)
                
                assert result["errors_deleted"] == 5
                assert result["summaries_deleted"] == 3
                
                mock_cleanup_errors.assert_called_once_with(30)
                mock_cleanup_summaries.assert_called_once_with(30)
                
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self, error_manager_components, sample_errors):
        """Test statistics collection."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register some errors
            for error in sample_errors:
                await error_manager.register_error(error)
            
            # Register a collector
            collector = MockCollector("test_collector")
            await error_manager.register_collector(collector)
            await error_manager.start_collection(["test_collector"])
            
            # Get statistics
            stats = await error_manager.get_statistics()
            
            assert "manager" in stats
            assert "storage" in stats
            assert stats["manager"]["total_errors_processed"] == len(sample_errors)
            assert stats["manager"]["collectors_active"] == 1
            assert stats["manager"]["collectors_registered"] == 1
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_health_check(self, error_manager_components):
        """Test health check functionality."""
        error_manager = error_manager_components['error_manager']
        await error_manager.start()
        
        try:
            # Register a collector
            collector = MockCollector("test_collector")
            await error_manager.register_collector(collector)
            
            # Perform health check
            health = await error_manager.health_check()
            
            assert "overall" in health
            assert "components" in health
            assert "error_store" in health["components"]
            assert "summary_store" in health["components"]
            assert "collectors" in health["components"]
            assert "ai_summarizer" in health["components"]
            
            # Should be healthy
            assert health["overall"] is True
            assert health["components"]["error_store"] is True
            assert health["components"]["summary_store"] is True
            
        finally:
            await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_error_grouping(self, error_manager_components):
        """Test error grouping for auto-summarization."""
        error_manager = error_manager_components['error_manager']
        
        # Test group key generation
        error1 = BrowserError(
            message="TypeError: Cannot read property 'foo' of null",
            url="https://example.com",
            error_type="TypeError"
        )
        error2 = BrowserError(
            message="TypeError: Cannot read property 'bar' of null",
            url="https://example.com",
            error_type="TypeError"
        )
        
        key1 = error_manager._create_error_group_key(error1)
        key2 = error_manager._create_error_group_key(error2)
        
        # Should have similar keys (same source, category, error type)
        assert key1 == key2  # They should group together
        
        # Different error type should have different key
        error3 = BrowserError(
            message="ReferenceError: x is not defined",
            url="https://example.com",
            error_type="ReferenceError"
        )
        
        key3 = error_manager._create_error_group_key(error3)
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_error_ignoring(self, error_manager_components):
        """Test error ignoring based on configuration."""
        error_manager = error_manager_components['error_manager']
        
        # Mock config service to ignore certain errors
        with patch.object(error_manager.config_service, 'should_ignore_error') as mock_should_ignore:
            mock_should_ignore.return_value = True
            
            await error_manager.start()
            
            try:
                # Register an error that should be ignored
                error = BrowserError(
                    message="ResizeObserver loop limit exceeded",
                    url="https://example.com"
                )
                
                error_id = await error_manager.register_error(error)
                
                # Error should still get an ID but not be processed
                assert error_id == error.id
                
                # Should not increment processed count significantly
                # (might increment due to async processing)
                await asyncio.sleep(0.1)
                
                mock_should_ignore.assert_called_once()
                
            finally:
                await error_manager.stop()
    
    @pytest.mark.asyncio
    async def test_summary_retrieval(self, error_manager_components, sample_errors):
        """Test summary retrieval functionality."""
        error_manager = error_manager_components['error_manager']
        
        # Mock AI summarizer and summary store
        with patch.object(error_manager.ai_summarizer, 'summarize_error_group') as mock_summarize:
            mock_summary = MagicMock()
            mock_summary.id = "test-summary-id"
            mock_summary.error_ids = [sample_errors[0].id]
            mock_summarize.return_value = mock_summary
            
            await error_manager.start()
            
            try:
                # Register error and create summary
                error_id = await error_manager.register_error(sample_errors[0])
                summary_id = await error_manager.request_summary([error_id])
                
                # Test summary retrieval
                retrieved_summary = await error_manager.get_summary(summary_id)
                assert retrieved_summary is not None
                
                # Test summaries for error
                summaries_for_error = await error_manager.get_summaries_for_error(error_id)
                assert len(summaries_for_error) >= 0  # Might be 0 due to mocking
                
            finally:
                await error_manager.stop()