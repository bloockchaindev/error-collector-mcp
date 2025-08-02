"""Integration example showing how all components work together."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .config_service import ConfigService
from .error_manager import ErrorManager
from .ai_summarizer import AISummarizer
from ..storage import ErrorStore, SummaryStore
from ..collectors import BrowserConsoleCollector, TerminalCollector
from ..models import BrowserError, TerminalError


logger = logging.getLogger(__name__)


class ErrorCollectorMCPService:
    """Complete Error Collector MCP service integration."""
    
    def __init__(self, config_path: str, data_directory: Optional[Path] = None):
        self.config_path = config_path
        self.data_directory = data_directory or Path.home() / ".error-collector-mcp"
        
        # Components
        self.config_service: Optional[ConfigService] = None
        self.error_store: Optional[ErrorStore] = None
        self.summary_store: Optional[SummaryStore] = None
        self.ai_summarizer: Optional[AISummarizer] = None
        self.error_manager: Optional[ErrorManager] = None
        
        # Collectors
        self.browser_collector: Optional[BrowserConsoleCollector] = None
        self.terminal_collector: Optional[TerminalCollector] = None
        
        self._is_running = False
    
    async def initialize(self) -> None:
        """Initialize all components."""
        if self._is_running:
            logger.warning("Service is already running")
            return
        
        try:
            # Initialize configuration service
            self.config_service = ConfigService()
            config = await self.config_service.load_config(self.config_path)
            
            # Create data directory
            self.data_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize storage components
            self.error_store = ErrorStore(
                self.data_directory,
                max_errors=config.storage.max_errors_stored
            )
            self.summary_store = SummaryStore(
                self.data_directory,
                max_summaries=config.storage.max_errors_stored // 2
            )
            
            # Initialize AI summarizer
            self.ai_summarizer = AISummarizer(config.openrouter)
            
            # Initialize summary store (CRITICAL: Load existing summaries)
            await self.summary_store.initialize()
            
            # Initialize error manager
            self.error_manager = ErrorManager(
                config_service=self.config_service,
                error_store=self.error_store,
                summary_store=self.summary_store,
                ai_summarizer=self.ai_summarizer
            )
            
            # Initialize collectors if enabled
            if self.config_service.is_source_enabled("browser"):
                self.browser_collector = BrowserConsoleCollector(
                    port=config.server.port + 100  # Offset from main server port
                )
                await self.error_manager.register_collector(self.browser_collector)
            
            if self.config_service.is_source_enabled("terminal"):
                self.terminal_collector = TerminalCollector()
                await self.error_manager.register_collector(self.terminal_collector)
            
            logger.info("Error Collector MCP service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def start(self) -> None:
        """Start the complete service."""
        if self._is_running:
            logger.warning("Service is already running")
            return
        
        try:
            # Start error manager (this starts all storage and AI components)
            await self.error_manager.start()
            
            # Start error collection
            await self.error_manager.start_collection()
            
            self._is_running = True
            logger.info("Error Collector MCP service started successfully")
            
            # Log service status
            await self._log_service_status()
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the complete service."""
        if not self._is_running:
            return
        
        try:
            # Stop error manager (this stops all components)
            if self.error_manager:
                await self.error_manager.stop()
            
            self._is_running = False
            logger.info("Error Collector MCP service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping service: {e}")
    
    async def get_service_status(self) -> dict:
        """Get comprehensive service status."""
        if not self._is_running or not self.error_manager:
            return {"status": "stopped"}
        
        try:
            # Get statistics from error manager
            stats = await self.error_manager.get_statistics()
            
            # Get health check
            health = await self.error_manager.health_check()
            
            # Get collector status
            collector_status = {}
            for name, collector in self.error_manager.collectors.items():
                collector_status[name] = {
                    "collecting": collector.is_collecting,
                    "healthy": await collector.health_check()
                }
            
            return {
                "status": "running",
                "healthy": health["overall"],
                "statistics": stats,
                "health": health,
                "collectors": collector_status,
                "data_directory": str(self.data_directory),
                "config_path": self.config_path
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def simulate_browser_error(self) -> str:
        """Simulate a browser error for testing."""
        if not self._is_running or not self.error_manager:
            raise RuntimeError("Service is not running")
        
        # Create a sample browser error
        error = BrowserError(
            message="TypeError: Cannot read property 'test' of null",
            url="https://example.com/test-page.html",
            user_agent="Mozilla/5.0 (Test Browser)",
            page_title="Test Page",
            line_number=42,
            column_number=15,
            error_type="TypeError",
            stack_trace="TypeError: Cannot read property 'test' of null\\n    at testFunction (test.js:42:15)"
        )
        
        # Register the error
        error_id = await self.error_manager.register_error(error)
        logger.info(f"Simulated browser error: {error_id}")
        
        return error_id
    
    async def simulate_terminal_error(self) -> str:
        """Simulate a terminal error for testing."""
        if not self._is_running or not self.error_manager:
            raise RuntimeError("Service is not running")
        
        # Create a sample terminal error
        error = TerminalError(
            message="npm ERR! code EACCES",
            command="npm install express",
            exit_code=1,
            working_directory="/home/user/project",
            stderr_output="npm ERR! code EACCES\\nnpm ERR! syscall access\\nnpm ERR! path /usr/local/lib/node_modules",
            stdout_output=""
        )
        
        # Register the error
        error_id = await self.error_manager.register_error(error)
        logger.info(f"Simulated terminal error: {error_id}")
        
        return error_id
    
    async def request_error_summary(self, error_ids: list) -> Optional[str]:
        """Request a summary for specific errors."""
        if not self._is_running or not self.error_manager:
            raise RuntimeError("Service is not running")
        
        return await self.error_manager.request_summary(error_ids)
    
    async def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors."""
        if not self._is_running or not self.error_manager:
            raise RuntimeError("Service is not running")
        
        from ..storage import ErrorFilters
        filters = ErrorFilters(limit=limit)
        return await self.error_manager.get_errors(filters)
    
    async def get_recent_summaries(self, limit: int = 5) -> list:
        """Get recent summaries."""
        if not self._is_running or not self.error_manager:
            raise RuntimeError("Service is not running")
        
        from ..storage import SummaryFilters
        filters = SummaryFilters(limit=limit)
        return await self.error_manager.get_summaries(filters)
    
    async def _log_service_status(self) -> None:
        """Log current service status."""
        try:
            status = await self.get_service_status()
            
            logger.info("=== Error Collector MCP Service Status ===")
            logger.info(f"Status: {status['status']}")
            logger.info(f"Healthy: {status.get('healthy', 'unknown')}")
            
            if 'statistics' in status:
                stats = status['statistics']['manager']
                logger.info(f"Errors processed: {stats['total_errors_processed']}")
                logger.info(f"Summaries generated: {stats['summaries_generated']}")
                logger.info(f"Active collectors: {stats['collectors_active']}")
            
            if 'collectors' in status:
                logger.info("Collectors:")
                for name, collector_status in status['collectors'].items():
                    logger.info(f"  {name}: collecting={collector_status['collecting']}, healthy={collector_status['healthy']}")
            
            logger.info("==========================================")
            
        except Exception as e:
            logger.error(f"Failed to log service status: {e}")


async def main():
    """Example usage of the complete service."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create service
    service = ErrorCollectorMCPService("config.json")
    
    try:
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        # Simulate some errors
        logger.info("Simulating errors...")
        
        browser_error_id = await service.simulate_browser_error()
        terminal_error_id = await service.simulate_terminal_error()
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Request a summary
        logger.info("Requesting error summary...")
        summary_id = await service.request_error_summary([browser_error_id, terminal_error_id])
        
        if summary_id:
            logger.info(f"Generated summary: {summary_id}")
        
        # Get recent data
        recent_errors = await service.get_recent_errors(5)
        recent_summaries = await service.get_recent_summaries(3)
        
        logger.info(f"Recent errors: {len(recent_errors)}")
        logger.info(f"Recent summaries: {len(recent_summaries)}")
        
        # Show final status
        status = await service.get_service_status()
        logger.info(f"Final status: {status['status']}")
        
        # Keep running for a bit to see auto-summarization
        logger.info("Running for 30 seconds to demonstrate auto-summarization...")
        
        # Simulate more similar errors
        for i in range(3):
            await service.simulate_browser_error()
            await asyncio.sleep(2)
        
        await asyncio.sleep(10)
        
        # Final statistics
        final_status = await service.get_service_status()
        final_stats = final_status['statistics']['manager']
        logger.info(f"Final statistics:")
        logger.info(f"  Total errors: {final_stats['total_errors_processed']}")
        logger.info(f"  Total summaries: {final_stats['summaries_generated']}")
        logger.info(f"  Auto summaries: {final_stats['auto_summaries_generated']}")
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        # Stop service
        await service.stop()
        logger.info("Service stopped")


if __name__ == "__main__":
    asyncio.run(main())