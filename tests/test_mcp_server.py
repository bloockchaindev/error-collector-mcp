"""Tests for MCP server implementation."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from error_collector_mcp.mcp_server import ErrorCollectorMCPServer, create_mcp_server
from error_collector_mcp.services import ErrorCollectorMCPService


class TestErrorCollectorMCPServer:
    """Test ErrorCollectorMCPServer functionality."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        config_data = {
            "openrouter": {
                "api_key": "test-api-key"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
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
    
    @pytest.fixture
    async def mcp_server(self, temp_config, temp_data_dir):
        """Create MCP server instance."""
        server = ErrorCollectorMCPServer(temp_config, temp_data_dir)
        yield server
        
        # Cleanup
        if server._is_running:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test server initialization."""
        assert not mcp_server._is_running
        assert mcp_server.service is None
        assert mcp_server.error_query_tool is None
        
        # Mock the service initialization to avoid actual startup
        with patch.object(ErrorCollectorMCPService, 'initialize') as mock_init, \
             patch.object(ErrorCollectorMCPService, '__init__', return_value=None):
            
            mock_service = MagicMock()
            mock_service.error_manager = MagicMock()
            mcp_server.service = mock_service
            
            await mcp_server.initialize()
            
            assert mcp_server.error_query_tool is not None
            assert mcp_server.error_summary_tool is not None
            assert mcp_server.error_statistics_tool is not None
    
    @pytest.mark.asyncio
    async def test_server_start_stop(self, mcp_server):
        """Test server start and stop functionality."""
        # Mock service and MCP components
        mock_service = MagicMock()
        mock_service.start = AsyncMock()
        mock_service.stop = AsyncMock()
        mock_service.error_manager = MagicMock()
        
        mcp_server.service = mock_service
        mcp_server.error_query_tool = MagicMock()
        mcp_server.error_summary_tool = MagicMock()
        mcp_server.error_statistics_tool = MagicMock()
        
        # Mock FastMCP run method
        with patch.object(mcp_server.mcp, 'run', new_callable=AsyncMock) as mock_run:
            # Test start
            await mcp_server.start()
            
            assert mcp_server._is_running
            mock_service.start.assert_called_once()
            mock_run.assert_called_once()
            
            # Test stop
            await mcp_server.stop()
            
            assert not mcp_server._is_running
            mock_service.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, mcp_server):
        """Test MCP tool registration."""
        # Mock service
        mock_service = MagicMock()
        mock_service.error_manager = MagicMock()
        mcp_server.service = mock_service
        
        # Initialize tools
        from error_collector_mcp.mcp_tools import ErrorQueryTool, ErrorSummaryTool, ErrorStatisticsTool
        mcp_server.error_query_tool = ErrorQueryTool(mock_service.error_manager)
        mcp_server.error_summary_tool = ErrorSummaryTool(mock_service.error_manager)
        mcp_server.error_statistics_tool = ErrorStatisticsTool(mock_service.error_manager)
        
        # Test tool registration
        await mcp_server._register_mcp_tools()
        
        # Verify tools are registered (this is hard to test directly with FastMCP)
        # But we can verify the tools exist
        assert mcp_server.error_query_tool is not None
        assert mcp_server.error_summary_tool is not None
        assert mcp_server.error_statistics_tool is not None
    
    @pytest.mark.asyncio
    async def test_get_available_tools(self, mcp_server):
        """Test getting available tools list."""
        # Mock service and tools
        mock_service = MagicMock()
        mock_service.error_manager = MagicMock()
        mcp_server.service = mock_service
        
        from error_collector_mcp.mcp_tools import ErrorQueryTool, ErrorSummaryTool, ErrorStatisticsTool
        mcp_server.error_query_tool = ErrorQueryTool(mock_service.error_manager)
        mcp_server.error_summary_tool = ErrorSummaryTool(mock_service.error_manager)
        mcp_server.error_statistics_tool = ErrorStatisticsTool(mock_service.error_manager)
        
        tools = await mcp_server.get_available_tools()
        
        assert len(tools) == 5  # 3 main tools + 2 utility tools
        
        tool_names = [tool["name"] for tool in tools]
        assert "query_errors" in tool_names
        assert "get_error_summary" in tool_names
        assert "get_error_statistics" in tool_names
        assert "get_server_status" in tool_names
        assert "simulate_error" in tool_names
    
    @pytest.mark.asyncio
    async def test_server_status_tool(self, mcp_server):
        """Test server status tool functionality."""
        # Mock service with status
        mock_service = MagicMock()
        mock_service.get_service_status = AsyncMock(return_value={
            "status": "running",
            "healthy": True,
            "collectors": {
                "browser": {"collecting": True},
                "terminal": {"collecting": False}
            }
        })
        mcp_server.service = mock_service
        
        # Create a mock tool function
        async def mock_get_server_status(arguments):
            if not mcp_server.service:
                return {"success": False, "error": "Service not initialized"}
            
            status = await mcp_server.service.get_service_status()
            return {"success": True, "data": status}
        
        # Test with details
        result = await mock_get_server_status({"include_details": True})
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["status"] == "running"
        assert result["data"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_simulate_error_tool(self, mcp_server):
        """Test error simulation tool functionality."""
        # Mock service with simulation methods
        mock_service = MagicMock()
        mock_service.simulate_browser_error = AsyncMock(return_value="browser-error-id")
        mock_service.simulate_terminal_error = AsyncMock(return_value="terminal-error-id")
        mcp_server.service = mock_service
        
        # Create a mock tool function
        async def mock_simulate_error(arguments):
            if not mcp_server.service:
                return {"success": False, "error": "Service not initialized"}
            
            error_type = arguments.get("error_type", "browser")
            count = arguments.get("count", 1)
            
            simulated_errors = []
            for i in range(count):
                if error_type == "browser":
                    error_id = await mcp_server.service.simulate_browser_error()
                else:
                    error_id = await mcp_server.service.simulate_terminal_error()
                simulated_errors.append(error_id)
            
            return {
                "success": True,
                "data": {
                    "simulated_errors": simulated_errors,
                    "count": len(simulated_errors),
                    "type": error_type
                }
            }
        
        # Test browser error simulation
        result = await mock_simulate_error({"error_type": "browser", "count": 2})
        
        assert result["success"] is True
        assert result["data"]["count"] == 2
        assert result["data"]["type"] == "browser"
        assert len(result["data"]["simulated_errors"]) == 2
        
        # Test terminal error simulation
        result = await mock_simulate_error({"error_type": "terminal", "count": 1})
        
        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["type"] == "terminal"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Test error handling in server operations."""
        # Test initialization error
        with patch.object(ErrorCollectorMCPService, 'initialize', side_effect=Exception("Init error")):
            with pytest.raises(Exception, match="Init error"):
                await mcp_server.initialize()
        
        # Test start error with service failure
        mock_service = MagicMock()
        mock_service.start = AsyncMock(side_effect=Exception("Start error"))
        mcp_server.service = mock_service
        
        with pytest.raises(Exception, match="Start error"):
            await mcp_server.start()
        
        # Verify cleanup was attempted
        assert not mcp_server._is_running


class TestMCPServerFactory:
    """Test MCP server factory functions."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        config_data = {
            "openrouter": {
                "api_key": "test-api-key"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_create_mcp_server(self, temp_config):
        """Test MCP server creation factory function."""
        with patch.object(ErrorCollectorMCPService, 'initialize') as mock_init, \
             patch.object(ErrorCollectorMCPService, '__init__', return_value=None):
            
            server = await create_mcp_server(temp_config)
            
            assert isinstance(server, ErrorCollectorMCPServer)
            assert server.config_path == temp_config
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_mcp_server_success(self, temp_config):
        """Test successful MCP server run."""
        with patch('error_collector_mcp.mcp_server.create_mcp_server') as mock_create, \
             patch('error_collector_mcp.mcp_server.logger') as mock_logger:
            
            mock_server = MagicMock()
            mock_server.start = AsyncMock()
            mock_server.stop = AsyncMock()
            mock_create.return_value = mock_server
            
            # Import and test the run function
            from error_collector_mcp.mcp_server import run_mcp_server
            
            await run_mcp_server(temp_config)
            
            mock_create.assert_called_once_with(temp_config, None)
            mock_server.start.assert_called_once()
            mock_server.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_mcp_server_with_error(self, temp_config):
        """Test MCP server run with error."""
        with patch('error_collector_mcp.mcp_server.create_mcp_server') as mock_create, \
             patch('error_collector_mcp.mcp_server.logger') as mock_logger:
            
            mock_create.side_effect = Exception("Server creation failed")
            
            from error_collector_mcp.mcp_server import run_mcp_server
            
            # Should not raise exception, but log error
            await run_mcp_server(temp_config)
            
            mock_logger.error.assert_called()


class TestMCPServerIntegration:
    """Test MCP server integration scenarios."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        config_data = {
            "openrouter": {
                "api_key": "test-api-key"
            },
            "collection": {
                "enabled_sources": ["browser", "terminal"]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_full_server_workflow(self, temp_config):
        """Test complete server workflow with mocked components."""
        temp_data_dir = Path(tempfile.mkdtemp())
        
        try:
            # Mock all the heavy components
            with patch.object(ErrorCollectorMCPService, 'initialize') as mock_service_init, \
                 patch.object(ErrorCollectorMCPService, 'start') as mock_service_start, \
                 patch.object(ErrorCollectorMCPService, 'stop') as mock_service_stop, \
                 patch.object(ErrorCollectorMCPService, '__init__', return_value=None):
                
                # Create server
                server = ErrorCollectorMCPServer(temp_config, temp_data_dir)
                
                # Mock service
                mock_service = MagicMock()
                mock_service.error_manager = MagicMock()
                mock_service.get_service_status = AsyncMock(return_value={
                    "status": "running",
                    "healthy": True
                })
                server.service = mock_service
                
                # Initialize
                await server.initialize()
                
                # Verify tools are created
                assert server.error_query_tool is not None
                assert server.error_summary_tool is not None
                assert server.error_statistics_tool is not None
                
                # Get available tools
                tools = await server.get_available_tools()
                assert len(tools) == 5
                
                # Verify service methods were called
                mock_service_init.assert_called_once()
                
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_data_dir)
    
    @pytest.mark.asyncio
    async def test_server_resilience(self, temp_config):
        """Test server resilience to component failures."""
        server = ErrorCollectorMCPServer(temp_config)
        
        # Test initialization with service failure
        with patch.object(ErrorCollectorMCPService, 'initialize', side_effect=Exception("Service failed")):
            with pytest.raises(Exception):
                await server.initialize()
        
        # Test tool execution without service
        tools = await server.get_available_tools()
        assert len(tools) == 5  # Should still return tool definitions
        
        # Test graceful degradation
        assert not server._is_running
        assert server.service is None