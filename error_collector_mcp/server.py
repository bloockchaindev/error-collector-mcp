"""FastMCP server implementation for Error Collector MCP."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from fastmcp.server import Server

from .services import ErrorCollectorMCPService
from .mcp_tools import ErrorQueryTool, ErrorSummaryTool, ErrorStatisticsTool


logger = logging.getLogger(__name__)

# Global service instance
service: Optional[ErrorCollectorMCPService] = None

# Create FastMCP app
app = FastMCP("Error Collector MCP")


async def initialize_service(config_path: str, data_directory: Optional[Path] = None) -> None:
    """Initialize the error collector service."""
    global service
    
    try:
        service = ErrorCollectorMCPService(config_path, data_directory)
        await service.initialize()
        await service.start()
        
        logger.info("Error Collector MCP service initialized and started")
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise


async def shutdown_service() -> None:
    """Shutdown the error collector service."""
    global service
    
    if service:
        try:
            await service.stop()
            logger.info("Error Collector MCP service stopped")
        except Exception as e:
            logger.error(f"Error stopping service: {e}")


# Error Query Tool
@app.tool(
    name="query_errors",
    description="Query and filter collected errors with various criteria"
)
async def query_errors(
    time_range: str = "24h",
    sources: Optional[list] = None,
    categories: Optional[list] = None,
    severities: Optional[list] = None,
    limit: int = 20,
    offset: int = 0,
    include_context: bool = True,
    group_similar: bool = False
) -> Dict[str, Any]:
    """Query and filter collected errors."""
    if not service:
        return {"success": False, "error": "Service not initialized"}
    
    tool = ErrorQueryTool(service.error_manager)
    arguments = {
        "time_range": time_range,
        "sources": sources or [],
        "categories": categories or [],
        "severities": severities or [],
        "limit": limit,
        "offset": offset,
        "include_context": include_context,
        "group_similar": group_similar
    }
    
    return await tool.execute(arguments)


# Error Summary Tool
@app.tool(
    name="get_error_summary",
    description="Get AI-generated summaries and analysis of errors with root cause identification and solutions"
)
async def get_error_summary(
    action: str = "list_recent",
    error_ids: Optional[list] = None,
    summary_id: Optional[str] = None,
    time_range: str = "24h",
    min_confidence: Optional[float] = None,
    limit: int = 10,
    include_solutions: bool = True,
    enhance_solutions: bool = False
) -> Dict[str, Any]:
    """Get AI-generated error summaries and analysis."""
    if not service:
        return {"success": False, "error": "Service not initialized"}
    
    tool = ErrorSummaryTool(service.error_manager)
    arguments = {
        "action": action,
        "error_ids": error_ids or [],
        "summary_id": summary_id,
        "time_range": time_range,
        "min_confidence": min_confidence,
        "limit": limit,
        "include_solutions": include_solutions,
        "enhance_solutions": enhance_solutions
    }
    
    return await tool.execute(arguments)


# Error Statistics Tool
@app.tool(
    name="get_error_statistics",
    description="Get comprehensive error statistics, trends, and analytics for monitoring and analysis"
)
async def get_error_statistics(
    report_type: str = "overview",
    time_range: str = "24h",
    grouping: str = "hour",
    include_predictions: bool = False,
    include_recommendations: bool = True
) -> Dict[str, Any]:
    """Get comprehensive error statistics and analytics."""
    if not service:
        return {"success": False, "error": "Service not initialized"}
    
    tool = ErrorStatisticsTool(service.error_manager)
    arguments = {
        "report_type": report_type,
        "time_range": time_range,
        "grouping": grouping,
        "include_predictions": include_predictions,
        "include_recommendations": include_recommendations
    }
    
    return await tool.execute(arguments)


# Server Status Tool
@app.tool(
    name="get_server_status",
    description="Get comprehensive server status and health information"
)
async def get_server_status(include_details: bool = True) -> Dict[str, Any]:
    """Get server status and health information."""
    try:
        if not service:
            return {
                "success": False,
                "error": "Service not initialized"
            }
        
        status = await service.get_service_status()
        
        if not include_details:
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


# Error Simulation Tool
@app.tool(
    name="simulate_error",
    description="Simulate errors for testing and demonstration purposes"
)
async def simulate_error(error_type: str = "browser", count: int = 1) -> Dict[str, Any]:
    """Simulate errors for testing purposes."""
    try:
        if not service:
            return {
                "success": False,
                "error": "Service not initialized"
            }
        
        if error_type not in ["browser", "terminal"]:
            return {
                "success": False,
                "error": "Invalid error_type. Must be 'browser' or 'terminal'"
            }
        
        if not (1 <= count <= 10):
            return {
                "success": False,
                "error": "Count must be between 1 and 10"
            }
        
        simulated_errors = []
        
        for i in range(count):
            if error_type == "browser":
                error_id = await service.simulate_browser_error()
            else:  # terminal
                error_id = await service.simulate_terminal_error()
            
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


# Health Check Tool
@app.tool(
    name="health_check",
    description="Perform comprehensive health check on all system components"
)
async def health_check() -> Dict[str, Any]:
    """Perform comprehensive health check."""
    try:
        if not service:
            return {
                "success": False,
                "error": "Service not initialized"
            }
        
        health = await service.error_manager.health_check()
        
        return {
            "success": True,
            "data": {
                "overall_healthy": health["overall"],
                "components": health["components"],
                "timestamp": "2024-01-01T12:00:00Z",  # Would use actual timestamp
                "checks_performed": len(health["components"])
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": {
                "type": "health_check_error",
                "message": str(e)
            }
        }


# Cleanup Old Data Tool
@app.tool(
    name="cleanup_old_data",
    description="Clean up old errors and summaries based on retention policy"
)
async def cleanup_old_data(retention_days: Optional[int] = None) -> Dict[str, Any]:
    """Clean up old errors and summaries."""
    try:
        if not service:
            return {
                "success": False,
                "error": "Service not initialized"
            }
        
        result = await service.error_manager.cleanup_old_data(retention_days)
        
        return {
            "success": True,
            "data": {
                "errors_deleted": result["errors_deleted"],
                "summaries_deleted": result["summaries_deleted"],
                "retention_days": retention_days or service.config_service.get_config().storage.retention_days
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": {
                "type": "cleanup_error",
                "message": str(e)
            }
        }


# Server startup and shutdown handlers
@app.on_startup
async def startup():
    """Server startup handler."""
    logger.info("Error Collector MCP server starting up...")
    
    # Initialize service with default config
    config_path = "config.json"
    data_directory = None
    
    # Check for environment variables or command line args
    import os
    config_path = os.getenv("ERROR_COLLECTOR_CONFIG", config_path)
    data_dir_env = os.getenv("ERROR_COLLECTOR_DATA_DIR")
    if data_dir_env:
        data_directory = Path(data_dir_env)
    
    await initialize_service(config_path, data_directory)


@app.on_shutdown
async def shutdown():
    """Server shutdown handler."""
    logger.info("Error Collector MCP server shutting down...")
    await shutdown_service()


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the MCP server."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Set up signal handlers
    setup_signal_handlers()
    
    logger.info("Starting Error Collector MCP server...")
    
    # Run the FastMCP server
    app.run()


if __name__ == "__main__":
    main()