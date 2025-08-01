"""MCP tool for querying collected errors."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..services import ErrorManager
from ..storage import ErrorFilters
from ..models import ErrorSource, ErrorCategory, ErrorSeverity


class ErrorQueryTool:
    """MCP tool for querying and filtering collected errors."""
    
    def __init__(self, error_manager: ErrorManager):
        self.error_manager = error_manager
    
    @property
    def name(self) -> str:
        """Tool name for MCP registration."""
        return "query_errors"
    
    @property
    def description(self) -> str:
        """Tool description for MCP."""
        return "Query and filter collected errors with various criteria"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema for the MCP tool."""
        return {
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "enum": ["1h", "6h", "24h", "7d", "30d", "all"],
                    "description": "Time range for error query",
                    "default": "24h"
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["browser", "terminal", "unknown"]
                    },
                    "description": "Filter by error sources"
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["syntax", "runtime", "network", "permission", "resource", "logic", "unknown"]
                    },
                    "description": "Filter by error categories"
                },
                "severities": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "description": "Filter by error severities"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of errors to return",
                    "default": 20
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of errors to skip for pagination",
                    "default": 0
                },
                "include_context": {
                    "type": "boolean",
                    "description": "Include detailed error context in results",
                    "default": true
                },
                "group_similar": {
                    "type": "boolean",
                    "description": "Group similar errors together",
                    "default": false
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the error query tool."""
        try:
            # Parse arguments
            time_range = arguments.get("time_range", "24h")
            sources = arguments.get("sources", [])
            categories = arguments.get("categories", [])
            severities = arguments.get("severities", [])
            limit = arguments.get("limit", 20)
            offset = arguments.get("offset", 0)
            include_context = arguments.get("include_context", True)
            group_similar = arguments.get("group_similar", False)
            
            # Build filters
            filters = await self._build_filters(
                time_range, sources, categories, severities, limit, offset
            )
            
            # Query errors
            errors = await self.error_manager.get_errors(filters)
            
            # Process results
            if group_similar:
                grouped_errors = await self._group_similar_errors(errors)
                result_data = await self._format_grouped_errors(grouped_errors, include_context)
            else:
                result_data = await self._format_errors(errors, include_context)
            
            # Get total count for pagination
            total_count = await self.error_manager.error_store.get_error_count(
                ErrorFilters(
                    start_time=filters.start_time,
                    end_time=filters.end_time,
                    sources=filters.sources,
                    categories=filters.categories,
                    severities=filters.severities
                )
            )
            
            return {
                "success": True,
                "data": {
                    "errors": result_data,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + len(errors) < total_count
                    },
                    "filters_applied": {
                        "time_range": time_range,
                        "sources": sources,
                        "categories": categories,
                        "severities": severities
                    },
                    "query_time": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "type": "query_error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    async def _build_filters(
        self,
        time_range: str,
        sources: List[str],
        categories: List[str],
        severities: List[str],
        limit: int,
        offset: int
    ) -> ErrorFilters:
        """Build ErrorFilters object from arguments."""
        # Parse time range
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
        
        # Convert string enums to model enums
        source_enums = set()
        for source in sources:
            try:
                source_enums.add(ErrorSource(source))
            except ValueError:
                pass  # Skip invalid sources
        
        category_enums = set()
        for category in categories:
            try:
                category_enums.add(ErrorCategory(category))
            except ValueError:
                pass  # Skip invalid categories
        
        severity_enums = set()
        for severity in severities:
            try:
                severity_enums.add(ErrorSeverity(severity))
            except ValueError:
                pass  # Skip invalid severities
        
        return ErrorFilters(
            start_time=start_time,
            sources=source_enums if source_enums else None,
            categories=category_enums if category_enums else None,
            severities=severity_enums if severity_enums else None,
            limit=limit,
            offset=offset
        )
    
    async def _group_similar_errors(self, errors: List) -> Dict[str, List]:
        """Group similar errors together."""
        groups = {}
        
        for error in errors:
            # Create a simple grouping key
            group_key = f"{error.source.value}_{error.category.value}_{error.message[:50]}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(error)
        
        return groups
    
    async def _format_errors(self, errors: List, include_context: bool) -> List[Dict[str, Any]]:
        """Format errors for response."""
        formatted_errors = []
        
        for error in errors:
            error_data = {
                "id": error.id,
                "timestamp": error.timestamp.isoformat(),
                "source": error.source.value,
                "category": error.category.value,
                "severity": error.severity.value,
                "message": error.message
            }
            
            # Add type-specific fields
            if hasattr(error, 'error_type'):  # BrowserError
                error_data.update({
                    "error_type": error.error_type,
                    "url": error.url,
                    "line_number": error.line_number,
                    "column_number": error.column_number,
                    "page_title": error.page_title
                })
            elif hasattr(error, 'command'):  # TerminalError
                error_data.update({
                    "command": error.command,
                    "exit_code": error.exit_code,
                    "working_directory": error.working_directory
                })
            
            # Include context if requested
            if include_context:
                error_data["context"] = error.context
                if error.stack_trace:
                    error_data["stack_trace"] = error.stack_trace
            
            formatted_errors.append(error_data)
        
        return formatted_errors
    
    async def _format_grouped_errors(self, grouped_errors: Dict[str, List], include_context: bool) -> List[Dict[str, Any]]:
        """Format grouped errors for response."""
        formatted_groups = []
        
        for group_key, errors in grouped_errors.items():
            # Get representative error (first one)
            representative = errors[0]
            
            group_data = {
                "group_key": group_key,
                "count": len(errors),
                "representative_error": (await self._format_errors([representative], include_context))[0],
                "first_occurrence": min(error.timestamp for error in errors).isoformat(),
                "last_occurrence": max(error.timestamp for error in errors).isoformat(),
                "error_ids": [error.id for error in errors]
            }
            
            # Add severity distribution
            severity_counts = {}
            for error in errors:
                severity = error.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            group_data["severity_distribution"] = severity_counts
            
            formatted_groups.append(group_data)
        
        # Sort by count (most frequent first)
        formatted_groups.sort(key=lambda x: x["count"], reverse=True)
        
        return formatted_groups
    
    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for the tool description."""
        try:
            stats = await self.error_manager.get_statistics()
            return {
                "total_errors": stats["storage"]["errors"]["total_errors"],
                "by_source": stats["storage"]["errors"]["by_source"],
                "by_category": stats["storage"]["errors"]["by_category"],
                "by_severity": stats["storage"]["errors"]["by_severity"]
            }
        except Exception:
            return {"error": "Unable to retrieve statistics"}