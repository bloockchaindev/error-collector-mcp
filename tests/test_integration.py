"""Integration tests for the complete Error Collector MCP system."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from error_collector_mcp.services import ErrorCollectorMCPService
from error_collector_mcp.models import BrowserError, TerminalError, ErrorSummary
from error_collector_mcp.health import HealthMonitor, HealthStatus


class TestCompleteIntegration:
    """Test complete system integration."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        config_data = {
            "openrouter": {
                "api_key": "test-api-key",
                "model": "meta-llama/llama-3.1-8b-instruct:free"
            },
            "collection": {
                "enabled_sources": ["browser", "terminal"],
                "auto_summarize": True
            },
            "storage": {
                "max_errors_stored": 1000,
                "retention_days": 30
            },
            "server": {
                "host": "localhost",
                "port": 8000
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_error_workflow(self, temp_config, temp_data_dir):
        """Test complete error collection and processing workflow."""
        # Mock heavy components to avoid actual API calls
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI') as mock_openai, \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "root_cause": "JavaScript error in browser",
                "impact_assessment": "User experience degraded",
                "suggested_solutions": ["Fix null reference", "Add error handling"],
                "confidence_score": 0.9
            })
            
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Create and initialize service
            service = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service.initialize()
            await service.start()
            
            try:
                # Test error simulation and collection
                browser_error_id = await service.simulate_browser_error()
                terminal_error_id = await service.simulate_terminal_error()
                
                # Verify errors were collected
                assert browser_error_id is not None
                assert terminal_error_id is not None
                
                # Wait for processing
                await asyncio.sleep(0.1)
                
                # Test error retrieval
                recent_errors = await service.get_recent_errors(10)
                assert len(recent_errors) >= 2
                
                # Test summary generation
                summary_id = await service.request_error_summary([browser_error_id, terminal_error_id])
                assert summary_id is not None
                
                # Test summary retrieval
                recent_summaries = await service.get_recent_summaries(5)
                assert len(recent_summaries) >= 1
                
                # Test service status
                status = await service.get_service_status()
                assert status["status"] == "running"
                assert "statistics" in status
                assert "collectors" in status
                
            finally:
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, temp_config, temp_data_dir):
        """Test health monitoring integration."""
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI'), \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            service = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service.initialize()
            await service.start()
            
            try:
                # Create health monitor
                health_monitor = HealthMonitor(service.error_manager)
                
                # Perform health check
                health = await health_monitor.perform_health_check()
                
                # Verify health check results
                assert health.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
                assert len(health.checks) > 0
                
                # Check specific components
                check_names = [check.name for check in health.checks]
                assert "error_manager" in check_names
                assert "error_store" in check_names
                assert "summary_store" in check_names
                
                # Test health history
                history = health_monitor.get_health_history(5)
                assert len(history) >= 1
                
                # Test health trends (need multiple checks)
                await health_monitor.perform_health_check()
                trends = health_monitor.get_health_trends()
                assert "current_status" in trends
                assert "stability" in trends
                
            finally:
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_error_processing_pipeline(self, temp_config, temp_data_dir):
        """Test the complete error processing pipeline."""
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI') as mock_openai, \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            # Mock AI response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "root_cause": "Null pointer dereference",
                "impact_assessment": "Application crash",
                "suggested_solutions": ["Add null check", "Use defensive programming"],
                "confidence_score": 0.85
            })
            
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            service = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service.initialize()
            await service.start()
            
            try:
                # Create test errors
                browser_error = BrowserError(
                    message="TypeError: Cannot read property 'foo' of null",
                    url="https://example.com/test.html",
                    error_type="TypeError",
                    line_number=42
                )
                
                terminal_error = TerminalError(
                    message="Command failed with exit code 1",
                    command="npm install",
                    exit_code=1,
                    stderr_output="Permission denied"
                )
                
                # Register errors through error manager
                browser_id = await service.error_manager.register_error(browser_error)
                terminal_id = await service.error_manager.register_error(terminal_error)
                
                # Wait for processing
                await asyncio.sleep(0.2)
                
                # Verify errors are stored
                stored_browser = await service.error_manager.get_error(browser_id)
                stored_terminal = await service.error_manager.get_error(terminal_id)
                
                assert stored_browser is not None
                assert stored_terminal is not None
                assert stored_browser.message == browser_error.message
                assert stored_terminal.command == terminal_error.command
                
                # Test manual summarization
                summary_id = await service.error_manager.request_summary([browser_id, terminal_id])
                assert summary_id is not None
                
                # Verify summary was created
                summary = await service.error_manager.get_summary(summary_id)
                assert summary is not None
                assert isinstance(summary, ErrorSummary)
                assert browser_id in summary.error_ids
                assert terminal_id in summary.error_ids
                assert summary.confidence_score == 0.85
                
                # Test statistics
                stats = await service.error_manager.get_statistics()
                assert stats["manager"]["total_errors_processed"] >= 2
                assert stats["manager"]["summaries_generated"] >= 1
                
            finally:
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self, temp_config, temp_data_dir):
        """Test MCP tools integration with the complete system."""
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI') as mock_openai, \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            # Mock AI response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "root_cause": "Test error analysis",
                "impact_assessment": "Test impact",
                "suggested_solutions": ["Test solution 1", "Test solution 2"],
                "confidence_score": 0.8
            })
            
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            service = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service.initialize()
            await service.start()
            
            try:
                # Import MCP tools
                from error_collector_mcp.mcp_tools import ErrorQueryTool, ErrorSummaryTool, ErrorStatisticsTool
                
                # Create tools
                query_tool = ErrorQueryTool(service.error_manager)
                summary_tool = ErrorSummaryTool(service.error_manager)
                stats_tool = ErrorStatisticsTool(service.error_manager)
                
                # Simulate some errors first
                await service.simulate_browser_error()
                await service.simulate_terminal_error()
                
                # Wait for processing
                await asyncio.sleep(0.1)
                
                # Test error query tool
                query_result = await query_tool.execute({
                    "time_range": "24h",
                    "limit": 10
                })
                
                assert query_result["success"] is True
                assert "errors" in query_result["data"]
                assert len(query_result["data"]["errors"]) >= 2
                
                # Test error summary tool
                error_ids = [error["id"] for error in query_result["data"]["errors"]]
                summary_result = await summary_tool.execute({
                    "action": "generate_new",
                    "error_ids": error_ids[:2]  # Take first 2 errors
                })
                
                assert summary_result["success"] is True
                assert "summary" in summary_result["data"]
                
                # Test statistics tool
                stats_result = await stats_tool.execute({
                    "report_type": "overview",
                    "time_range": "24h"
                })
                
                assert stats_result["success"] is True
                assert "summary" in stats_result["data"]
                assert stats_result["data"]["summary"]["errors_in_period"] >= 2
                
            finally:
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_error_persistence_and_recovery(self, temp_config, temp_data_dir):
        """Test error persistence and system recovery."""
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI'), \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            # First session: create and store errors
            service1 = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service1.initialize()
            await service1.start()
            
            try:
                # Create errors
                error_id1 = await service1.simulate_browser_error()
                error_id2 = await service1.simulate_terminal_error()
                
                # Force save to disk
                await service1.error_manager.error_store.force_save()
                
                # Verify errors exist
                error1 = await service1.error_manager.get_error(error_id1)
                error2 = await service1.error_manager.get_error(error_id2)
                assert error1 is not None
                assert error2 is not None
                
            finally:
                await service1.stop()
            
            # Second session: verify persistence
            service2 = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service2.initialize()
            await service2.start()
            
            try:
                # Verify errors were loaded from disk
                recovered_error1 = await service2.error_manager.get_error(error_id1)
                recovered_error2 = await service2.error_manager.get_error(error_id2)
                
                assert recovered_error1 is not None
                assert recovered_error2 is not None
                assert recovered_error1.message == error1.message
                assert recovered_error2.message == error2.message
                
                # Verify statistics reflect loaded data
                stats = await service2.error_manager.get_statistics()
                assert stats["storage"]["errors"]["total_errors"] >= 2
                
            finally:
                await service2.stop()
    
    @pytest.mark.asyncio
    async def test_system_resilience(self, temp_config, temp_data_dir):
        """Test system resilience to component failures."""
        with patch('error_collector_mcp.services.ai_summarizer.AsyncOpenAI') as mock_openai, \
             patch('error_collector_mcp.collectors.browser_collector.websockets'), \
             patch('error_collector_mcp.collectors.browser_collector.web'):
            
            # Mock AI failure
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            mock_openai.return_value = mock_client
            
            service = ErrorCollectorMCPService(temp_config, temp_data_dir)
            await service.initialize()
            await service.start()
            
            try:
                # System should still function even with AI failures
                error_id = await service.simulate_browser_error()
                assert error_id is not None
                
                # Error should be stored even if summarization fails
                error = await service.error_manager.get_error(error_id)
                assert error is not None
                
                # Summary request should fail gracefully
                summary_id = await service.error_manager.request_summary([error_id])
                assert summary_id is None  # Should fail but not crash
                
                # System status should reflect the issue
                status = await service.get_service_status()
                assert status["status"] == "running"  # Still running despite AI issues
                
            finally:
                await service.stop()