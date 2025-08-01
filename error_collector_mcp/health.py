"""Health check and status monitoring for Error Collector MCP."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .services import ErrorManager


logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: HealthStatus
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    uptime_seconds: float = 0
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check result."""
        self.checks.append(check)
        
        # Update overall status based on worst check
        if check.status == HealthStatus.CRITICAL:
            self.overall_status = HealthStatus.CRITICAL
        elif check.status == HealthStatus.WARNING and self.overall_status != HealthStatus.CRITICAL:
            self.overall_status = HealthStatus.WARNING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "duration_ms": check.duration_ms,
                    "details": check.details
                }
                for check in self.checks
            ],
            "summary": {
                "total_checks": len(self.checks),
                "healthy": len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
                "warnings": len([c for c in self.checks if c.status == HealthStatus.WARNING]),
                "critical": len([c for c in self.checks if c.status == HealthStatus.CRITICAL]),
                "unknown": len([c for c in self.checks if c.status == HealthStatus.UNKNOWN])
            }
        }


class HealthMonitor:
    """Health monitoring system for Error Collector MCP."""
    
    def __init__(self, error_manager: Optional[ErrorManager] = None):
        self.error_manager = error_manager
        self.start_time = time.time()
        self._monitoring_active = False
        self._health_history: List[SystemHealth] = []
        self._max_history = 100
    
    async def perform_health_check(self) -> SystemHealth:
        """Perform comprehensive health check."""
        health = SystemHealth(overall_status=HealthStatus.HEALTHY)
        health.uptime_seconds = time.time() - self.start_time
        
        # Check error manager
        if self.error_manager:
            await self._check_error_manager(health)
            await self._check_storage_systems(health)
            await self._check_collectors(health)
            await self._check_ai_summarizer(health)
        else:
            health.add_check(HealthCheck(
                name="error_manager",
                status=HealthStatus.CRITICAL,
                message="Error manager not initialized"
            ))
        
        # Check system resources
        await self._check_system_resources(health)
        
        # Store in history
        self._health_history.append(health)
        if len(self._health_history) > self._max_history:
            self._health_history.pop(0)
        
        return health
    
    async def _check_error_manager(self, health: SystemHealth) -> None:
        """Check error manager health."""
        start_time = time.time()
        
        try:
            if not self.error_manager._is_running:
                health.add_check(HealthCheck(
                    name="error_manager",
                    status=HealthStatus.CRITICAL,
                    message="Error manager is not running",
                    duration_ms=int((time.time() - start_time) * 1000)
                ))
                return
            
            # Check basic functionality
            stats = await self.error_manager.get_statistics()
            
            # Check error processing rate
            manager_stats = stats["manager"]
            processing_rate = manager_stats["total_errors_processed"]
            
            status = HealthStatus.HEALTHY
            message = f"Error manager operational, processed {processing_rate} errors"
            
            # Check for concerning patterns
            if manager_stats["collectors_active"] == 0:
                status = HealthStatus.WARNING
                message += " (no active collectors)"
            
            health.add_check(HealthCheck(
                name="error_manager",
                status=status,
                message=message,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    "errors_processed": processing_rate,
                    "summaries_generated": manager_stats["summaries_generated"],
                    "collectors_active": manager_stats["collectors_active"]
                }
            ))
            
        except Exception as e:
            health.add_check(HealthCheck(
                name="error_manager",
                status=HealthStatus.CRITICAL,
                message=f"Error manager check failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
    
    async def _check_storage_systems(self, health: SystemHealth) -> None:
        """Check storage system health."""
        start_time = time.time()
        
        try:
            # Check error store
            error_count = await self.error_manager.error_store.get_error_count()
            error_stats = await self.error_manager.error_store.get_statistics()
            
            status = HealthStatus.HEALTHY
            message = f"Error store operational with {error_count} errors"
            
            # Check for storage issues
            if error_count > self.error_manager.error_store.max_errors * 0.9:
                status = HealthStatus.WARNING
                message += " (approaching capacity)"
            
            health.add_check(HealthCheck(
                name="error_store",
                status=status,
                message=message,
                duration_ms=int((time.time() - start_time) * 1000),
                details=error_stats
            ))
            
            # Check summary store
            summary_count = await self.error_manager.summary_store.get_summary_count()
            summary_stats = await self.error_manager.summary_store.get_statistics()
            
            status = HealthStatus.HEALTHY
            message = f"Summary store operational with {summary_count} summaries"
            
            if summary_count > self.error_manager.summary_store.max_summaries * 0.9:
                status = HealthStatus.WARNING
                message += " (approaching capacity)"
            
            health.add_check(HealthCheck(
                name="summary_store",
                status=status,
                message=message,
                duration_ms=int((time.time() - start_time) * 1000),
                details=summary_stats
            ))
            
        except Exception as e:
            health.add_check(HealthCheck(
                name="storage_systems",
                status=HealthStatus.CRITICAL,
                message=f"Storage check failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
    
    async def _check_collectors(self, health: SystemHealth) -> None:
        """Check collector health."""
        start_time = time.time()
        
        try:
            healthy_collectors = 0
            total_collectors = len(self.error_manager.collectors)
            
            for name, collector in self.error_manager.collectors.items():
                collector_start = time.time()
                
                try:
                    collector_healthy = await collector.health_check()
                    
                    if collector_healthy:
                        healthy_collectors += 1
                        status = HealthStatus.HEALTHY
                        message = f"Collector {name} is healthy"
                    else:
                        status = HealthStatus.WARNING
                        message = f"Collector {name} health check failed"
                    
                    health.add_check(HealthCheck(
                        name=f"collector_{name}",
                        status=status,
                        message=message,
                        duration_ms=int((time.time() - collector_start) * 1000),
                        details={
                            "collecting": collector.is_collecting,
                            "healthy": collector_healthy
                        }
                    ))
                    
                except Exception as e:
                    health.add_check(HealthCheck(
                        name=f"collector_{name}",
                        status=HealthStatus.CRITICAL,
                        message=f"Collector {name} check failed: {str(e)}",
                        duration_ms=int((time.time() - collector_start) * 1000)
                    ))
            
            # Overall collector health
            if total_collectors == 0:
                overall_status = HealthStatus.WARNING
                overall_message = "No collectors registered"
            elif healthy_collectors == total_collectors:
                overall_status = HealthStatus.HEALTHY
                overall_message = f"All {total_collectors} collectors healthy"
            elif healthy_collectors > 0:
                overall_status = HealthStatus.WARNING
                overall_message = f"{healthy_collectors}/{total_collectors} collectors healthy"
            else:
                overall_status = HealthStatus.CRITICAL
                overall_message = "No collectors are healthy"
            
            health.add_check(HealthCheck(
                name="collectors_overall",
                status=overall_status,
                message=overall_message,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    "total_collectors": total_collectors,
                    "healthy_collectors": healthy_collectors
                }
            ))
            
        except Exception as e:
            health.add_check(HealthCheck(
                name="collectors",
                status=HealthStatus.CRITICAL,
                message=f"Collector check failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
    
    async def _check_ai_summarizer(self, health: SystemHealth) -> None:
        """Check AI summarizer health."""
        start_time = time.time()
        
        try:
            if not self.error_manager.ai_summarizer._is_running:
                health.add_check(HealthCheck(
                    name="ai_summarizer",
                    status=HealthStatus.CRITICAL,
                    message="AI summarizer is not running",
                    duration_ms=int((time.time() - start_time) * 1000)
                ))
                return
            
            # Check rate limiter status
            rate_limiter = self.error_manager.ai_summarizer.rate_limiter
            
            status = HealthStatus.HEALTHY
            message = "AI summarizer operational"
            details = {
                "running": True,
                "requests_in_queue": self.error_manager.ai_summarizer.request_queue.qsize(),
                "processing_requests": len(self.error_manager.ai_summarizer.processing_requests)
            }
            
            # Check for backoff status
            if rate_limiter.backoff_until and time.time() < rate_limiter.backoff_until:
                status = HealthStatus.WARNING
                message += " (in backoff period)"
                details["backoff_until"] = rate_limiter.backoff_until
            
            # Check queue size
            queue_size = self.error_manager.ai_summarizer.request_queue.qsize()
            if queue_size > 10:
                status = HealthStatus.WARNING
                message += f" ({queue_size} requests queued)"
            
            health.add_check(HealthCheck(
                name="ai_summarizer",
                status=status,
                message=message,
                duration_ms=int((time.time() - start_time) * 1000),
                details=details
            ))
            
        except Exception as e:
            health.add_check(HealthCheck(
                name="ai_summarizer",
                status=HealthStatus.CRITICAL,
                message=f"AI summarizer check failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
    
    async def _check_system_resources(self, health: SystemHealth) -> None:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Determine status based on resource usage
            status = HealthStatus.HEALTHY
            warnings = []
            
            if memory_percent > 90:
                status = HealthStatus.CRITICAL
                warnings.append(f"memory at {memory_percent:.1f}%")
            elif memory_percent > 80:
                status = HealthStatus.WARNING
                warnings.append(f"memory at {memory_percent:.1f}%")
            
            if disk_percent > 95:
                status = HealthStatus.CRITICAL
                warnings.append(f"disk at {disk_percent:.1f}%")
            elif disk_percent > 85:
                status = HealthStatus.WARNING
                warnings.append(f"disk at {disk_percent:.1f}%")
            
            if cpu_percent > 95:
                status = HealthStatus.WARNING
                warnings.append(f"CPU at {cpu_percent:.1f}%")
            
            message = "System resources normal"
            if warnings:
                message = f"Resource concerns: {', '.join(warnings)}"
            
            health.add_check(HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "cpu_percent": cpu_percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_free_gb": disk.free / (1024**3)
                }
            ))
            
        except ImportError:
            health.add_check(HealthCheck(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for resource monitoring",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
        except Exception as e:
            health.add_check(HealthCheck(
                name="system_resources",
                status=HealthStatus.WARNING,
                message=f"Resource check failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            ))
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history."""
        recent_history = self._health_history[-limit:] if self._health_history else []
        return [health.to_dict() for health in recent_history]
    
    def get_health_trends(self) -> Dict[str, Any]:
        """Get health trends analysis."""
        if len(self._health_history) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Analyze trends over recent history
        recent_checks = self._health_history[-10:]  # Last 10 checks
        
        # Count status changes
        status_counts = {
            HealthStatus.HEALTHY.value: 0,
            HealthStatus.WARNING.value: 0,
            HealthStatus.CRITICAL.value: 0,
            HealthStatus.UNKNOWN.value: 0
        }
        
        for health in recent_checks:
            status_counts[health.overall_status.value] += 1
        
        # Calculate stability
        latest_status = recent_checks[-1].overall_status
        status_changes = sum(
            1 for i in range(1, len(recent_checks))
            if recent_checks[i].overall_status != recent_checks[i-1].overall_status
        )
        
        stability = "stable" if status_changes <= 1 else "unstable"
        
        return {
            "current_status": latest_status.value,
            "stability": stability,
            "status_distribution": status_counts,
            "status_changes": status_changes,
            "checks_analyzed": len(recent_checks),
            "time_range": {
                "start": recent_checks[0].timestamp.isoformat(),
                "end": recent_checks[-1].timestamp.isoformat()
            }
        }