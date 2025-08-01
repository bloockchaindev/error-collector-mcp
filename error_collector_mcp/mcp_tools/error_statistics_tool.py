"""MCP tool for error statistics and analytics."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..services import ErrorManager
from ..storage import ErrorFilters, SummaryFilters
from ..models import ErrorSource, ErrorCategory, ErrorSeverity


class ErrorStatisticsTool:
    """MCP tool for error trends, patterns, and analytics."""
    
    def __init__(self, error_manager: ErrorManager):
        self.error_manager = error_manager
    
    @property
    def name(self) -> str:
        """Tool name for MCP registration."""
        return "get_error_statistics"
    
    @property
    def description(self) -> str:
        """Tool description for MCP."""
        return "Get comprehensive error statistics, trends, and analytics for monitoring and analysis"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema for the MCP tool."""
        return {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["overview", "trends", "patterns", "health", "detailed"],
                    "description": "Type of statistics report to generate",
                    "default": "overview"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["1h", "6h", "24h", "7d", "30d", "all"],
                    "description": "Time range for statistics",
                    "default": "24h"
                },
                "grouping": {
                    "type": "string",
                    "enum": ["hour", "day", "week", "month"],
                    "description": "Time grouping for trend analysis",
                    "default": "hour"
                },
                "include_predictions": {
                    "type": "boolean",
                    "description": "Include trend predictions and forecasts",
                    "default": false
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include actionable recommendations",
                    "default": true
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the error statistics tool."""
        try:
            report_type = arguments.get("report_type", "overview")
            
            if report_type == "overview":
                return await self._generate_overview_report(arguments)
            elif report_type == "trends":
                return await self._generate_trends_report(arguments)
            elif report_type == "patterns":
                return await self._generate_patterns_report(arguments)
            elif report_type == "health":
                return await self._generate_health_report(arguments)
            elif report_type == "detailed":
                return await self._generate_detailed_report(arguments)
            else:
                return {
                    "success": False,
                    "error": {
                        "type": "invalid_report_type",
                        "message": f"Unknown report type: {report_type}"
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "type": "execution_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    async def _generate_overview_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overview statistics report."""
        time_range = arguments.get("time_range", "24h")
        
        # Get comprehensive statistics
        stats = await self.error_manager.get_statistics()
        
        # Get time-filtered error count
        filters = self._build_time_filter(time_range)
        recent_errors = await self.error_manager.get_errors(filters)
        recent_count = len(recent_errors)
        
        # Calculate error rate
        error_rate = await self._calculate_error_rate(time_range, recent_count)
        
        # Get top error categories and sources
        top_categories = await self._get_top_categories(recent_errors)
        top_sources = await self._get_top_sources(recent_errors)
        
        # Get summary statistics
        summary_stats = stats["storage"]["summaries"]
        
        # Generate recommendations if requested
        recommendations = []
        if arguments.get("include_recommendations", True):
            recommendations = await self._generate_overview_recommendations(
                recent_errors, stats
            )
        
        return {
            "success": True,
            "data": {
                "report_type": "overview",
                "time_range": time_range,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_errors_all_time": stats["storage"]["errors"]["total_errors"],
                    "errors_in_period": recent_count,
                    "error_rate": error_rate,
                    "total_summaries": summary_stats["total_summaries"],
                    "average_confidence": summary_stats.get("average_confidence", 0),
                    "active_collectors": stats["manager"]["collectors_active"]
                },
                "breakdown": {
                    "by_source": top_sources,
                    "by_category": top_categories,
                    "by_severity": await self._get_severity_distribution(recent_errors)
                },
                "ai_analysis": {
                    "summaries_generated": stats["manager"]["summaries_generated"],
                    "auto_summaries": stats["manager"]["auto_summaries_generated"],
                    "confidence_distribution": summary_stats.get("confidence_distribution", {})
                },
                "recommendations": recommendations
            }
        }
    
    async def _generate_trends_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trends and time-series analysis report."""
        time_range = arguments.get("time_range", "24h")
        grouping = arguments.get("grouping", "hour")
        
        # Get time-series data
        time_series = await self._generate_time_series(time_range, grouping)
        
        # Calculate trends
        trends = await self._calculate_trends(time_series)
        
        # Generate predictions if requested
        predictions = []
        if arguments.get("include_predictions", False):
            predictions = await self._generate_predictions(time_series, grouping)
        
        return {
            "success": True,
            "data": {
                "report_type": "trends",
                "time_range": time_range,
                "grouping": grouping,
                "generated_at": datetime.utcnow().isoformat(),
                "time_series": time_series,
                "trends": trends,
                "predictions": predictions,
                "analysis": {
                    "peak_error_periods": await self._identify_peak_periods(time_series),
                    "error_velocity": trends.get("velocity", 0),
                    "trend_direction": trends.get("direction", "stable")
                }
            }
        }
    
    async def _generate_patterns_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate error patterns and correlation analysis."""
        time_range = arguments.get("time_range", "24h")
        
        # Get recent errors for pattern analysis
        filters = self._build_time_filter(time_range)
        errors = await self.error_manager.get_errors(filters)
        
        # Analyze patterns
        patterns = await self._analyze_error_patterns(errors)
        correlations = await self._find_error_correlations(errors)
        recurring_issues = await self._identify_recurring_issues(errors)
        
        return {
            "success": True,
            "data": {
                "report_type": "patterns",
                "time_range": time_range,
                "generated_at": datetime.utcnow().isoformat(),
                "patterns": patterns,
                "correlations": correlations,
                "recurring_issues": recurring_issues,
                "insights": await self._generate_pattern_insights(patterns, correlations)
            }
        }
    
    async def _generate_health_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate system health and performance report."""
        # Get health check results
        health = await self.error_manager.health_check()
        
        # Get performance metrics
        stats = await self.error_manager.get_statistics()
        
        # Calculate health scores
        health_scores = await self._calculate_health_scores(health, stats)
        
        # Generate alerts and warnings
        alerts = await self._generate_health_alerts(health, stats)
        
        return {
            "success": True,
            "data": {
                "report_type": "health",
                "generated_at": datetime.utcnow().isoformat(),
                "overall_health": health["overall"],
                "health_scores": health_scores,
                "component_status": health["components"],
                "performance_metrics": {
                    "error_processing_rate": stats["manager"]["total_errors_processed"],
                    "summary_generation_rate": stats["manager"]["summaries_generated"],
                    "storage_utilization": await self._calculate_storage_utilization(stats)
                },
                "alerts": alerts,
                "recommendations": await self._generate_health_recommendations(health, stats)
            }
        }
    
    async def _generate_detailed_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive detailed report."""
        # Combine all report types
        overview = await self._generate_overview_report(arguments)
        trends = await self._generate_trends_report(arguments)
        patterns = await self._generate_patterns_report(arguments)
        health = await self._generate_health_report(arguments)
        
        return {
            "success": True,
            "data": {
                "report_type": "detailed",
                "generated_at": datetime.utcnow().isoformat(),
                "overview": overview["data"],
                "trends": trends["data"],
                "patterns": patterns["data"],
                "health": health["data"],
                "executive_summary": await self._generate_executive_summary(
                    overview["data"], trends["data"], patterns["data"], health["data"]
                )
            }
        }
    
    def _build_time_filter(self, time_range: str) -> ErrorFilters:
        """Build time-based error filter."""
        start_time = None
        if time_range != "all":
            time_deltas = {
                "1h": timedelta(hours=1),
                "6h": timedelta(hours=6),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30)
            }
            if time_range in time_deltas:
                start_time = datetime.utcnow() - time_deltas[time_range]
        
        return ErrorFilters(start_time=start_time, limit=1000)  # High limit for analysis
    
    async def _calculate_error_rate(self, time_range: str, error_count: int) -> Dict[str, Any]:
        """Calculate error rate metrics."""
        time_deltas = {
            "1h": 1,
            "6h": 6,
            "24h": 24,
            "7d": 24 * 7,
            "30d": 24 * 30
        }
        
        hours = time_deltas.get(time_range, 24)
        rate_per_hour = error_count / hours if hours > 0 else 0
        
        return {
            "errors_per_hour": round(rate_per_hour, 2),
            "errors_per_day": round(rate_per_hour * 24, 2),
            "total_in_period": error_count,
            "period_hours": hours
        }
    
    async def _get_top_categories(self, errors: List) -> Dict[str, int]:
        """Get top error categories."""
        category_counts = {}
        for error in errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by count
        return dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
    
    async def _get_top_sources(self, errors: List) -> Dict[str, int]:
        """Get top error sources."""
        source_counts = {}
        for error in errors:
            source = error.source.value
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
    
    async def _get_severity_distribution(self, errors: List) -> Dict[str, int]:
        """Get error severity distribution."""
        severity_counts = {}
        for error in errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return severity_counts
    
    async def _generate_time_series(self, time_range: str, grouping: str) -> List[Dict[str, Any]]:
        """Generate time series data for trends."""
        # This is a simplified implementation
        # In a real system, you'd query the database with time grouping
        
        filters = self._build_time_filter(time_range)
        errors = await self.error_manager.get_errors(filters)
        
        # Group errors by time periods
        time_groups = {}
        
        for error in errors:
            # Determine time bucket based on grouping
            if grouping == "hour":
                bucket = error.timestamp.replace(minute=0, second=0, microsecond=0)
            elif grouping == "day":
                bucket = error.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif grouping == "week":
                days_since_monday = error.timestamp.weekday()
                bucket = error.timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
            else:  # month
                bucket = error.timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            bucket_str = bucket.isoformat()
            if bucket_str not in time_groups:
                time_groups[bucket_str] = []
            time_groups[bucket_str].append(error)
        
        # Convert to time series format
        time_series = []
        for timestamp, bucket_errors in sorted(time_groups.items()):
            time_series.append({
                "timestamp": timestamp,
                "error_count": len(bucket_errors),
                "by_severity": await self._get_severity_distribution(bucket_errors),
                "by_source": await self._get_top_sources(bucket_errors)
            })
        
        return time_series
    
    async def _calculate_trends(self, time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend metrics from time series."""
        if len(time_series) < 2:
            return {"direction": "insufficient_data", "velocity": 0}
        
        # Simple trend calculation
        counts = [point["error_count"] for point in time_series]
        
        # Calculate velocity (change rate)
        if len(counts) >= 2:
            recent_avg = sum(counts[-3:]) / min(3, len(counts))
            earlier_avg = sum(counts[:3]) / min(3, len(counts))
            velocity = recent_avg - earlier_avg
        else:
            velocity = 0
        
        # Determine direction
        if velocity > 1:
            direction = "increasing"
        elif velocity < -1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return {
            "direction": direction,
            "velocity": round(velocity, 2),
            "peak_count": max(counts) if counts else 0,
            "average_count": round(sum(counts) / len(counts), 2) if counts else 0
        }
    
    async def _generate_predictions(self, time_series: List[Dict[str, Any]], grouping: str) -> List[Dict[str, Any]]:
        """Generate simple trend predictions."""
        if len(time_series) < 3:
            return []
        
        # Simple linear prediction based on recent trend
        recent_counts = [point["error_count"] for point in time_series[-3:]]
        trend = (recent_counts[-1] - recent_counts[0]) / len(recent_counts)
        
        # Generate next few predictions
        predictions = []
        last_timestamp = datetime.fromisoformat(time_series[-1]["timestamp"])
        
        for i in range(1, 4):  # Predict next 3 periods
            if grouping == "hour":
                next_time = last_timestamp + timedelta(hours=i)
            elif grouping == "day":
                next_time = last_timestamp + timedelta(days=i)
            elif grouping == "week":
                next_time = last_timestamp + timedelta(weeks=i)
            else:  # month
                next_time = last_timestamp + timedelta(days=30 * i)
            
            predicted_count = max(0, recent_counts[-1] + (trend * i))
            
            predictions.append({
                "timestamp": next_time.isoformat(),
                "predicted_count": round(predicted_count, 1),
                "confidence": max(0.1, 1.0 - (i * 0.2))  # Decreasing confidence
            })
        
        return predictions
    
    async def _identify_peak_periods(self, time_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify peak error periods."""
        if not time_series:
            return []
        
        counts = [point["error_count"] for point in time_series]
        avg_count = sum(counts) / len(counts)
        threshold = avg_count * 1.5  # 50% above average
        
        peaks = []
        for point in time_series:
            if point["error_count"] > threshold:
                peaks.append({
                    "timestamp": point["timestamp"],
                    "error_count": point["error_count"],
                    "above_average": round(point["error_count"] - avg_count, 1)
                })
        
        return peaks
    
    async def _analyze_error_patterns(self, errors: List) -> Dict[str, Any]:
        """Analyze error patterns."""
        patterns = {
            "common_messages": {},
            "error_sequences": [],
            "time_patterns": {}
        }
        
        # Common message patterns
        for error in errors:
            # Extract first 50 chars as pattern
            pattern = error.message[:50]
            patterns["common_messages"][pattern] = patterns["common_messages"].get(pattern, 0) + 1
        
        # Sort by frequency
        patterns["common_messages"] = dict(
            sorted(patterns["common_messages"].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        # Time patterns (hour of day)
        hour_counts = {}
        for error in errors:
            hour = error.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        patterns["time_patterns"] = hour_counts
        
        return patterns
    
    async def _find_error_correlations(self, errors: List) -> List[Dict[str, Any]]:
        """Find correlations between different error types."""
        # Simplified correlation analysis
        correlations = []
        
        # Group errors by time windows
        time_windows = {}
        for error in errors:
            # 5-minute windows
            window = error.timestamp.replace(minute=(error.timestamp.minute // 5) * 5, second=0, microsecond=0)
            window_str = window.isoformat()
            
            if window_str not in time_windows:
                time_windows[window_str] = []
            time_windows[window_str].append(error)
        
        # Look for windows with multiple error types
        for window_time, window_errors in time_windows.items():
            if len(window_errors) > 1:
                sources = set(error.source.value for error in window_errors)
                categories = set(error.category.value for error in window_errors)
                
                if len(sources) > 1 or len(categories) > 1:
                    correlations.append({
                        "time_window": window_time,
                        "error_count": len(window_errors),
                        "sources": list(sources),
                        "categories": list(categories),
                        "correlation_strength": min(1.0, len(window_errors) / 10.0)
                    })
        
        return correlations[:10]  # Top 10 correlations
    
    async def _identify_recurring_issues(self, errors: List) -> List[Dict[str, Any]]:
        """Identify recurring error issues."""
        # Group similar errors
        error_groups = {}
        
        for error in errors:
            # Create a grouping key
            key = f"{error.source.value}_{error.category.value}_{error.message[:30]}"
            
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(error)
        
        # Find groups with multiple occurrences
        recurring = []
        for group_key, group_errors in error_groups.items():
            if len(group_errors) >= 3:  # At least 3 occurrences
                first_time = min(error.timestamp for error in group_errors)
                last_time = max(error.timestamp for error in group_errors)
                duration = (last_time - first_time).total_seconds() / 3600  # hours
                
                recurring.append({
                    "pattern": group_key,
                    "occurrences": len(group_errors),
                    "first_seen": first_time.isoformat(),
                    "last_seen": last_time.isoformat(),
                    "duration_hours": round(duration, 2),
                    "frequency": round(len(group_errors) / max(duration, 1), 2),
                    "representative_message": group_errors[0].message
                })
        
        # Sort by frequency
        recurring.sort(key=lambda x: x["frequency"], reverse=True)
        
        return recurring[:10]
    
    async def _generate_pattern_insights(self, patterns: Dict, correlations: List) -> List[str]:
        """Generate insights from pattern analysis."""
        insights = []
        
        # Most common error pattern
        if patterns["common_messages"]:
            top_pattern = list(patterns["common_messages"].items())[0]
            insights.append(f"Most common error pattern: '{top_pattern[0]}...' ({top_pattern[1]} occurrences)")
        
        # Peak error times
        if patterns["time_patterns"]:
            peak_hour = max(patterns["time_patterns"].items(), key=lambda x: x[1])
            insights.append(f"Peak error time: {peak_hour[0]}:00 with {peak_hour[1]} errors")
        
        # Correlation insights
        if correlations:
            high_correlation = max(correlations, key=lambda x: x["correlation_strength"])
            insights.append(f"Strong correlation found: {len(high_correlation['sources'])} sources, {len(high_correlation['categories'])} categories in same time window")
        
        return insights
    
    async def _calculate_health_scores(self, health: Dict, stats: Dict) -> Dict[str, float]:
        """Calculate health scores for different components."""
        scores = {}
        
        # Overall system health
        scores["overall"] = 1.0 if health["overall"] else 0.0
        
        # Component health scores
        for component, status in health["components"].items():
            if isinstance(status, dict):
                # For collectors, calculate average health
                healthy_count = sum(1 for s in status.values() if s)
                total_count = len(status)
                scores[component] = healthy_count / total_count if total_count > 0 else 0.0
            else:
                scores[component] = 1.0 if status else 0.0
        
        return scores
    
    async def _generate_health_alerts(self, health: Dict, stats: Dict) -> List[Dict[str, Any]]:
        """Generate health alerts and warnings."""
        alerts = []
        
        # System health alerts
        if not health["overall"]:
            alerts.append({
                "level": "critical",
                "message": "System health check failed",
                "component": "system",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Component alerts
        for component, status in health["components"].items():
            if isinstance(status, dict):
                for sub_component, sub_status in status.items():
                    if not sub_status:
                        alerts.append({
                            "level": "warning",
                            "message": f"{component}.{sub_component} is unhealthy",
                            "component": f"{component}.{sub_component}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
            elif not status:
                alerts.append({
                    "level": "warning",
                    "message": f"{component} is unhealthy",
                    "component": component,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    async def _calculate_storage_utilization(self, stats: Dict) -> Dict[str, Any]:
        """Calculate storage utilization metrics."""
        error_stats = stats["storage"]["errors"]
        summary_stats = stats["storage"]["summaries"]
        
        return {
            "error_storage": {
                "total_errors": error_stats["total_errors"],
                "utilization_percentage": 0  # Would need max capacity info
            },
            "summary_storage": {
                "total_summaries": summary_stats["total_summaries"],
                "utilization_percentage": 0  # Would need max capacity info
            }
        }
    
    async def _generate_overview_recommendations(self, errors: List, stats: Dict) -> List[str]:
        """Generate recommendations based on overview data."""
        recommendations = []
        
        if len(errors) > 100:
            recommendations.append("High error volume detected. Consider implementing error rate limiting or investigating root causes.")
        
        # Check for dominant error sources
        sources = await self._get_top_sources(errors)
        if sources:
            top_source = list(sources.items())[0]
            if top_source[1] > len(errors) * 0.7:
                recommendations.append(f"Majority of errors ({top_source[1]}) come from {top_source[0]}. Focus debugging efforts here.")
        
        # Check summary generation rate
        if stats["manager"]["summaries_generated"] < len(errors) / 10:
            recommendations.append("Low AI summary generation rate. Consider enabling auto-summarization or reviewing API limits.")
        
        return recommendations
    
    async def _generate_health_recommendations(self, health: Dict, stats: Dict) -> List[str]:
        """Generate health-based recommendations."""
        recommendations = []
        
        if not health["overall"]:
            recommendations.append("System health is compromised. Check component status and logs.")
        
        # Check collector health
        collectors = health["components"].get("collectors", {})
        unhealthy_collectors = [name for name, status in collectors.items() if not status]
        
        if unhealthy_collectors:
            recommendations.append(f"Unhealthy collectors detected: {', '.join(unhealthy_collectors)}. Restart or reconfigure these collectors.")
        
        return recommendations
    
    async def _generate_executive_summary(self, overview: Dict, trends: Dict, patterns: Dict, health: Dict) -> Dict[str, Any]:
        """Generate executive summary of all reports."""
        return {
            "key_metrics": {
                "total_errors": overview["summary"]["total_errors_all_time"],
                "recent_error_rate": overview["summary"]["error_rate"]["errors_per_hour"],
                "system_health": "healthy" if health["overall_health"] else "unhealthy",
                "trend_direction": trends["trends"]["direction"]
            },
            "top_concerns": [
                concern for concern in [
                    "High error rate" if overview["summary"]["error_rate"]["errors_per_hour"] > 10 else None,
                    "System unhealthy" if not health["overall_health"] else None,
                    "Increasing error trend" if trends["trends"]["direction"] == "increasing" else None
                ] if concern
            ],
            "recommendations": overview.get("recommendations", [])[:3]  # Top 3 recommendations
        }