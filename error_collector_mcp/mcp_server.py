"""MCP server implementation for Error Collector MCP."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastmcp import FastMCP

from .services import ErrorCollectorMCPService
from .mcp_tools import ErrorQueryTool, ErrorSummaryTool, ErrorStatisticsTool


logger = logging.getLogger(__name__)


class ErrorCollectorMCPServer:
    """MCP server for Error Collector functionality."""
    
    def __init__(self, config_path: str, data_directory: Optional[Path] = None):
        self.config_path = config_path
        self.data_directory = data_directory
        
        # Core service
        self.service: Optional[ErrorCollectorMCPService] = None
        
        # MCP server
        self.mcp = FastMCP("Error Collector MCP")
        
        # Tools
        self.error_query_tool: Optional[ErrorQueryTool] = None
        self.error_summary_tool: Optional[ErrorSummaryTool] = None
        self.error_statistics_tool: Optional[ErrorStatisticsTool] = None
        
        self._is_running = False
    
    async def initialize(self) -> None:
        """Initialize the MCP server and all components."""
        try:
            # Initialize core service
            self.service = ErrorCollectorMCPService(self.config_path, self.data_directory)
            await self.service.initialize()
            
            # Initialize MCP tools
            self.error_query_tool = ErrorQueryTool(self.service.error_manager)
            self.error_summary_tool = ErrorSummaryTool(self.service.error_manager)
            self.error_statistics_tool = ErrorStatisticsTool(self.service.error_manager)
            
            # Register MCP tools
            await self._register_mcp_tools()
            
            logger.info("Error Collector MCP server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self._is_running:
            logger.warning("MCP server is already running")
            return
        
        try:
            # Start core service
            await self.service.start()
            
            # Start MCP server
            await self.mcp.run()
            
            self._is_running = True
            logger.info("Error Collector MCP server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._is_running:
            return
        
        try:
            # Stop core service
            if self.service:
                await self.service.stop()
            
            self._is_running = False
            logger.info("Error Collector MCP server stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
    
    async def _register_mcp_tools(self) -> None:
        """Register all MCP tools with the server."""
        # Register error query tool
        @self.mcp.tool(
            name=self.error_query_tool.name,
            description=self.error_query_tool.description,
            input_schema=self.error_query_tool.input_schema
        )
        async def query_errors(arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Query and filter collected errors."""
            return await self.error_query_tool.execute(arguments)
        
        # Register error summary tool
        @self.mcp.tool(
            name=self.error_summary_tool.name,
            description=self.error_summary_tool.description,
            input_schema=self.error_summary_tool.input_schema
        )
        async def get_error_summary(arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Get AI-generated error summaries and analysis."""
            return await self.error_summary_tool.execute(arguments)
        
        # Register error statistics tool
        @self.mcp.tool(
            name=self.error_statistics_tool.name,
            description=self.error_statistics_tool.description,
            input_schema=self.error_statistics_tool.input_schema
        )
        async def get_error_statistics(arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Get comprehensive error statistics and analytics."""
            return await self.error_statistics_tool.execute(arguments)
        
        # Register additional utility tools
        @self.mcp.tool(
            name="get_server_status",
            description="Get comprehensive server status and health information",
            input_schema={
                "type": "object",
                "properties": {
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed component information",
                        "default": True
                    }
                }
            }
        )
        async def get_server_status(arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Get server status and health information."""
            try:
                if not self.service:
                    return {
                        "success": False,
                        "error": "Service not initialized"
                    }
                
                status = await self.service.get_service_status()
                
                if not arguments.get("include_details", True):
                    # Return simplified status
                    return {
                        "success": True,
                        "data": {
                            "status": status["status"],
                            "healthy": status.get("healthy", False),
                            "collectors_active": len([
                                c for c in status.get("collectors", {}).values()
                                if c.get("collecting", False)
                            ]) if "collectors" in status else 0
                        }
                    }
                
                return {
                    "success": True,
                    "data": status
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": {
                        "type": "status_error",
                        "message": str(e)
                    }
                }
        
        @self.mcp.tool(
            name="simulate_error",
            description="Simulate errors for testing and demonstration purposes",
            input_schema={
                "type": "object",
                "properties": {
                    "error_type": {
                        "type": "string",
                        "enum": ["browser", "terminal"],
                        "description": "Type of error to simulate",
                        "default": "browser"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of errors to simulate",
                        "default": 1
                    }
                }
            }
        )
        async def simulate_error(arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate errors for testing purposes."""
            try:
                if not self.service:
                    return {
                        "success": False,
                        "error": "Service not initialized"
                    }
                
                error_type = arguments.get("error_type", "browser")
                count = arguments.get("count", 1)
                
                simulated_errors = []
                
                for i in range(count):
                    if error_type == "browser":
                        error_id = await self.service.simulate_browser_error()
                    else:  # terminal
                        error_id = await self.service.simulate_terminal_error()
                    
                    simulated_errors.append(error_id)
                
                return {
                    "success": True,
                    "data": {
                        "simulated_errors": simulated_errors,
                        "count": len(simulated_errors),
                        "type": error_type
                    }
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": {
                        "type": "simulation_error",
                        "message": str(e)
                    }
                }
        
        logger.info("MCP tools registered successfully")
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        tools = []
        
        if self.error_query_tool:
            tools.append({
                "name": self.error_query_tool.name,
                "description": self.error_query_tool.description,
                "category": "query"
            })
        
        if self.error_summary_tool:
            tools.append({
                "name": self.error_summary_tool.name,
                "description": self.error_summary_tool.description,
                "category": "analysis"
            })
        
        if self.error_statistics_tool:
            tools.append({
                "name": self.error_statistics_tool.name,
                "description": self.error_statistics_tool.description,
                "category": "analytics"
            })
        
        # Add utility tools
        tools.extend([
            {
                "name": "get_server_status",
                "description": "Get comprehensive server status and health information",
                "category": "utility"
            },
            {
                "name": "simulate_error",
                "description": "Simulate errors for testing and demonstration purposes",
                "category": "utility"
            }
        ])
        
        return tools


async def create_mcp_server(config_path: str, data_directory: Optional[Path] = None) -> ErrorCollectorMCPServer:
    """Create and initialize an Error Collector MCP server."""
    server = ErrorCollectorMCPServer(config_path, data_directory)
    await server.initialize()
    return server


async def run_mcp_server(config_path: str, data_directory: Optional[Path] = None) -> None:
    """Run the Error Collector MCP server."""
    server = None
    try:
        server = await create_mcp_server(config_path, data_directory)
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
    finally:
        if server:
            await server.stop()


if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Get config path from command line
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    # Run server
    asyncio.run(run_mcp_server(config_path))