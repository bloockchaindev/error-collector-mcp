"""Error manager service for coordinating error collection and processing."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Callable, Any
from dataclasses import dataclass

from ..models import BaseError, BrowserError, TerminalError, ErrorSummary
from ..storage import ErrorStore, ErrorFilters, SummaryStore, SummaryFilters
from ..collectors import BaseCollector, BrowserConsoleCollector, TerminalCollector
from .ai_summarizer import AISummarizer
from .config_service import ConfigService


logger = logging.getLogger(__name__)


@dataclass
class ErrorManagerStats:
    """Statistics for error manager operations."""
    total_errors_processed: int = 0
    errors_by_source: Dict[str, int] = None
    summaries_generated: int = 0
    auto_summaries_generated: int = 0
    collectors_active: int = 0
    last_error_time: Optional[datetime] = None
    last_summary_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.errors_by_source is None:
            self.errors_by_source = {}


class ErrorManager:
    """Central coordinator for error collection, processing, and AI summarization."""
    
    def __init__(
        self,
        config_service: ConfigService,
        error_store: ErrorStore,
        summary_store: SummaryStore,
        ai_summarizer: AISummarizer
    ):
        self.config_service = config_service
        self.error_store = error_store
        self.summary_store = summary_store
        self.ai_summarizer = ai_summarizer
        
        # Collectors management
        self.collectors: Dict[str, BaseCollector] = {}
        self.collector_callbacks: Dict[str, Callable] = {}
        
        # Processing settings
        self.auto_summarize_enabled = True
        self.auto_summarize_threshold = 5  # Auto-summarize after N similar errors
        self.auto_summarize_interval = 300  # Auto-summarize every 5 minutes
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._is_running = False
        
        # Statistics
        self.stats = ErrorManagerStats()
        
        # Error processing queue
        self._error_queue: asyncio.Queue = asyncio.Queue()
        self._processing_errors: Dict[str, BaseError] = {}
        
        # Summarization tracking
        self._pending_summaries: Dict[str, List[str]] = {}  # group_key -> error_ids
        self._summary_timers: Dict[str, asyncio.Task] = {}
    
    async def start(self) -> None:
        """Start the error manager and all its components."""
        if self._is_running:
            logger.warning("Error manager is already running")
            return
        
        self._is_running = True
        
        # Start storage components
        await self.error_store.initialize()
        await self.summary_store.initialize()
        
        # Start AI summarizer
        await self.ai_summarizer.start()
        
        # Start background processing tasks
        self._start_background_tasks()
        
        # Load configuration settings
        await self._load_configuration()
        
        logger.info("Error manager started successfully")
    
    async def stop(self) -> None:
        """Stop the error manager and all its components."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Stop all collectors
        for collector in self.collectors.values():
            if collector.is_collecting:
                await collector.stop_collection()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Stop AI summarizer
        await self.ai_summarizer.stop()
        
        # Shutdown storage
        await self.error_store.shutdown()
        await self.summary_store.shutdown()
        
        logger.info("Error manager stopped successfully")
    
    async def register_collector(self, collector: BaseCollector) -> None:
        """Register an error collector."""
        collector_name = collector.name
        
        if collector_name in self.collectors:
            logger.warning(f"Collector {collector_name} is already registered")
            return
        
        # Register the collector
        self.collectors[collector_name] = collector
        
        # Set up error callback
        callback = self._create_collector_callback(collector_name)
        self.collector_callbacks[collector_name] = callback
        
        if hasattr(collector, 'add_error_callback'):
            collector.add_error_callback(callback)
        
        logger.info(f"Registered collector: {collector_name}")
    
    async def unregister_collector(self, collector_name: str) -> None:
        """Unregister an error collector."""
        if collector_name not in self.collectors:
            logger.warning(f"Collector {collector_name} is not registered")
            return
        
        collector = self.collectors[collector_name]
        
        # Stop collection if active
        if collector.is_collecting:
            await collector.stop_collection()
        
        # Remove callback
        if collector_name in self.collector_callbacks:
            callback = self.collector_callbacks[collector_name]
            if hasattr(collector, 'remove_error_callback'):
                collector.remove_error_callback(callback)
            del self.collector_callbacks[collector_name]
        
        # Remove collector
        del self.collectors[collector_name]
        
        logger.info(f"Unregistered collector: {collector_name}")
    
    async def start_collection(self, collector_names: Optional[List[str]] = None) -> None:
        """Start error collection for specified collectors or all collectors."""
        if collector_names is None:
            collector_names = list(self.collectors.keys())
        
        for name in collector_names:
            if name in self.collectors:
                collector = self.collectors[name]
                if not collector.is_collecting:
                    await collector.start_collection()
                    logger.info(f"Started collection for: {name}")
            else:
                logger.warning(f"Collector not found: {name}")
    
    async def stop_collection(self, collector_names: Optional[List[str]] = None) -> None:
        """Stop error collection for specified collectors or all collectors."""
        if collector_names is None:
            collector_names = list(self.collectors.keys())
        
        for name in collector_names:
            if name in self.collectors:
                collector = self.collectors[name]
                if collector.is_collecting:
                    await collector.stop_collection()
                    logger.info(f"Stopped collection for: {name}")
    
    async def register_error(self, error: BaseError) -> str:
        """Register a new error for processing."""
        # Check if error should be ignored
        if self._should_ignore_error(error):
            logger.debug(f"Ignoring error: {error.message[:50]}...")
            return error.id
        
        # Store the error
        error_id = await self.error_store.store_error(error)
        
        # Update statistics
        self.stats.total_errors_processed += 1
        self.stats.errors_by_source[error.source.value] = (
            self.stats.errors_by_source.get(error.source.value, 0) + 1
        )
        self.stats.last_error_time = datetime.utcnow()
        
        # Queue for processing
        await self._error_queue.put(error)
        
        logger.debug(f"Registered error: {error_id}")
        return error_id
    
    async def get_errors(self, filters: Optional[ErrorFilters] = None) -> List[BaseError]:
        """Get errors with optional filtering."""
        return await self.error_store.get_errors(filters or ErrorFilters())
    
    async def get_error(self, error_id: str) -> Optional[BaseError]:
        """Get a specific error by ID."""
        return await self.error_store.get_error(error_id)
    
    async def request_summary(self, error_ids: List[str]) -> Optional[str]:
        """Request AI summarization for specific errors."""
        if not error_ids:
            return None
        
        # Get errors from storage
        errors = []
        for error_id in error_ids:
            error = await self.error_store.get_error(error_id)
            if error:
                errors.append(error)
        
        if not errors:
            logger.warning(f"No errors found for IDs: {error_ids}")
            return None
        
        try:
            # Generate summary
            summary = await self.ai_summarizer.summarize_error_group(errors)
            
            # Store summary
            summary_id = await self.summary_store.store_summary(summary)
            
            # Update statistics
            self.stats.summaries_generated += 1
            self.stats.last_summary_time = datetime.utcnow()
            
            logger.info(f"Generated summary {summary_id} for {len(errors)} errors")
            return summary_id
            
        except Exception as e:
            logger.error(f"Failed to generate summary for errors {error_ids}: {e}")
            return None
    
    async def get_summaries(self, filters: Optional[SummaryFilters] = None) -> List[ErrorSummary]:
        """Get summaries with optional filtering."""
        return await self.summary_store.get_summaries(filters or SummaryFilters())
    
    async def get_summary(self, summary_id: str) -> Optional[ErrorSummary]:
        """Get a specific summary by ID."""
        return await self.summary_store.get_summary(summary_id)
    
    async def get_summaries_for_error(self, error_id: str) -> List[ErrorSummary]:
        """Get all summaries that include a specific error."""
        return await self.summary_store.get_summaries_for_error(error_id)
    
    async def cleanup_old_data(self, retention_days: Optional[int] = None) -> Dict[str, int]:
        """Clean up old errors and summaries."""
        if retention_days is None:
            retention_days = self.config_service.get_config().storage.retention_days
        
        # Clean up errors
        errors_deleted = await self.error_store.cleanup_old_errors(retention_days)
        
        # Clean up summaries
        summaries_deleted = await self.summary_store.cleanup_old_summaries(retention_days)
        
        logger.info(f"Cleaned up {errors_deleted} errors and {summaries_deleted} summaries")
        
        return {
            "errors_deleted": errors_deleted,
            "summaries_deleted": summaries_deleted
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        # Update collector statistics
        self.stats.collectors_active = sum(
            1 for collector in self.collectors.values() 
            if collector.is_collecting
        )
        
        # Get storage statistics
        error_stats = await self.error_store.get_statistics()
        summary_stats = await self.summary_store.get_statistics()
        
        return {
            "manager": {
                "total_errors_processed": self.stats.total_errors_processed,
                "errors_by_source": self.stats.errors_by_source,
                "summaries_generated": self.stats.summaries_generated,
                "auto_summaries_generated": self.stats.auto_summaries_generated,
                "collectors_active": self.stats.collectors_active,
                "collectors_registered": len(self.collectors),
                "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None,
                "last_summary_time": self.stats.last_summary_time.isoformat() if self.stats.last_summary_time else None,
                "pending_summaries": len(self._pending_summaries),
                "processing_errors": len(self._processing_errors)
            },
            "storage": {
                "errors": error_stats,
                "summaries": summary_stats
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health_status = {
            "overall": True,
            "components": {}
        }
        
        # Check error store
        try:
            await self.error_store.get_error_count()
            health_status["components"]["error_store"] = True
        except Exception as e:
            health_status["components"]["error_store"] = False
            health_status["overall"] = False
            logger.error(f"Error store health check failed: {e}")
        
        # Check summary store
        try:
            await self.summary_store.get_summary_count()
            health_status["components"]["summary_store"] = True
        except Exception as e:
            health_status["components"]["summary_store"] = False
            health_status["overall"] = False
            logger.error(f"Summary store health check failed: {e}")
        
        # Check collectors
        collector_health = {}
        for name, collector in self.collectors.items():
            try:
                collector_health[name] = await collector.health_check()
                if not collector_health[name]:
                    health_status["overall"] = False
            except Exception as e:
                collector_health[name] = False
                health_status["overall"] = False
                logger.error(f"Collector {name} health check failed: {e}")
        
        health_status["components"]["collectors"] = collector_health
        
        # Check AI summarizer (basic check)
        health_status["components"]["ai_summarizer"] = self.ai_summarizer._is_running
        if not self.ai_summarizer._is_running:
            health_status["overall"] = False
        
        return health_status
    
    def _create_collector_callback(self, collector_name: str) -> Callable:
        """Create a callback function for a collector."""
        async def callback(error: BaseError):
            try:
                await self.register_error(error)
            except Exception as e:
                logger.error(f"Failed to process error from {collector_name}: {e}")
        
        return callback
    
    def _should_ignore_error(self, error: BaseError) -> bool:
        """Check if an error should be ignored based on configuration."""
        # Check with config service
        domain = None
        if isinstance(error, BrowserError):
            domain = error.url
        
        return self.config_service.should_ignore_error(error.message, domain)
    
    async def _load_configuration(self) -> None:
        """Load configuration settings."""
        config = self.config_service.get_config()
        
        self.auto_summarize_enabled = config.collection.auto_summarize
        self.auto_summarize_threshold = 5  # Could be configurable
        
        logger.debug("Configuration loaded for error manager")
    
    def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        # Error processing task
        task = asyncio.create_task(self._process_error_queue())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Auto-summarization task
        task = asyncio.create_task(self._auto_summarization_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Cleanup task
        task = asyncio.create_task(self._periodic_cleanup())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        logger.debug("Background tasks started")
    
    async def _process_error_queue(self) -> None:
        """Background task to process the error queue."""
        while self._is_running:
            try:
                # Get error from queue
                try:
                    error = await asyncio.wait_for(
                        self._error_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the error
                await self._process_error(error)
                
            except Exception as e:
                logger.error(f"Error in error queue processing: {e}")
                await asyncio.sleep(1)
    
    async def _process_error(self, error: BaseError) -> None:
        """Process a single error."""
        try:
            self._processing_errors[error.id] = error
            
            # Check for auto-summarization
            if self.auto_summarize_enabled:
                await self._check_auto_summarization(error)
            
        except Exception as e:
            logger.error(f"Failed to process error {error.id}: {e}")
        finally:
            self._processing_errors.pop(error.id, None)
    
    async def _check_auto_summarization(self, error: BaseError) -> None:
        """Check if error should trigger auto-summarization."""
        # Create a grouping key for similar errors
        group_key = self._create_error_group_key(error)
        
        # Add to pending summaries
        if group_key not in self._pending_summaries:
            self._pending_summaries[group_key] = []
        
        self._pending_summaries[group_key].append(error.id)
        
        # Check if we should trigger summarization
        error_count = len(self._pending_summaries[group_key])
        
        if error_count >= self.auto_summarize_threshold:
            # Trigger immediate summarization
            await self._trigger_auto_summarization(group_key)
        elif error_count == 1:
            # Set timer for delayed summarization
            await self._set_summarization_timer(group_key)
    
    def _create_error_group_key(self, error: BaseError) -> str:
        """Create a grouping key for similar errors."""
        # Simple grouping based on source, category, and message similarity
        key_parts = [
            error.source.value,
            error.category.value,
            error.message[:50]  # First 50 chars of message
        ]
        
        if isinstance(error, BrowserError):
            key_parts.append(error.error_type)
        elif isinstance(error, TerminalError):
            key_parts.append(error.command.split()[0] if error.command else "")
        
        return "|".join(key_parts)
    
    async def _set_summarization_timer(self, group_key: str) -> None:
        """Set a timer for delayed auto-summarization."""
        # Cancel existing timer
        if group_key in self._summary_timers:
            self._summary_timers[group_key].cancel()
        
        # Create new timer
        async def timer_callback():
            await asyncio.sleep(self.auto_summarize_interval)
            await self._trigger_auto_summarization(group_key)
        
        task = asyncio.create_task(timer_callback())
        self._summary_timers[group_key] = task
    
    async def _trigger_auto_summarization(self, group_key: str) -> None:
        """Trigger auto-summarization for a group of errors."""
        if group_key not in self._pending_summaries:
            return
        
        error_ids = self._pending_summaries[group_key]
        if not error_ids:
            return
        
        try:
            # Generate summary
            summary_id = await self.request_summary(error_ids)
            
            if summary_id:
                self.stats.auto_summaries_generated += 1
                logger.info(f"Auto-generated summary {summary_id} for {len(error_ids)} errors")
            
        except Exception as e:
            logger.error(f"Failed to auto-generate summary for group {group_key}: {e}")
        
        finally:
            # Clean up
            self._pending_summaries.pop(group_key, None)
            if group_key in self._summary_timers:
                self._summary_timers[group_key].cancel()
                del self._summary_timers[group_key]
    
    async def _auto_summarization_loop(self) -> None:
        """Background loop for auto-summarization management."""
        while self._is_running:
            try:
                # Clean up completed timers
                completed_timers = [
                    key for key, task in self._summary_timers.items()
                    if task.done()
                ]
                
                for key in completed_timers:
                    del self._summary_timers[key]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in auto-summarization loop: {e}")
                await asyncio.sleep(60)
    
    async def _periodic_cleanup(self) -> None:
        """Background task for periodic cleanup."""
        while self._is_running:
            try:
                # Wait 24 hours between cleanups
                await asyncio.sleep(24 * 60 * 60)
                
                if self._is_running:
                    await self.cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60 * 60)  # Retry in 1 hour