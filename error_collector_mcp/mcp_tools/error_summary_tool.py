"""MCP tool for AI-generated error summaries."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..services import ErrorManager
from ..storage import SummaryFilters


class ErrorSummaryTool:
    """MCP tool for getting and generating AI-powered error summaries."""
    
    def __init__(self, error_manager: ErrorManager):
        self.error_manager = error_manager
    
    @property
    def name(self) -> str:
        """Tool name for MCP registration."""
        return "get_error_summary"
    
    @property
    def description(self) -> str:
        """Tool description for MCP."""
        return "Get AI-generated summaries and analysis of errors with root cause identification and solutions"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Input schema for the MCP tool."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_existing", "generate_new", "get_for_error", "list_recent"],
                    "description": "Action to perform",
                    "default": "list_recent"
                },
                "error_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of error IDs to summarize (for generate_new or get_for_error)"
                },
                "summary_id": {
                    "type": "string",
                    "description": "Specific summary ID to retrieve (for get_existing)"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["1h", "6h", "24h", "7d", "30d", "all"],
                    "description": "Time range for recent summaries",
                    "default": "24h"
                },
                "min_confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum confidence score for summaries"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of summaries to return",
                    "default": 10
                },
                "include_solutions": {
                    "type": "boolean",
                    "description": "Include detailed solution suggestions",
                    "default": true
                },
                "enhance_solutions": {
                    "type": "boolean",
                    "description": "Generate additional solution suggestions",
                    "default": false
                }
            },
            "required": []
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the error summary tool."""
        try:
            action = arguments.get("action", "list_recent")
            
            if action == "get_existing":
                return await self._get_existing_summary(arguments)
            elif action == "generate_new":
                return await self._generate_new_summary(arguments)
            elif action == "get_for_error":
                return await self._get_summaries_for_error(arguments)
            elif action == "list_recent":
                return await self._list_recent_summaries(arguments)
            else:
                return {
                    "success": False,
                    "error": {
                        "type": "invalid_action",
                        "message": f"Unknown action: {action}",
                        "timestamp": datetime.utcnow().isoformat()
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
    
    async def _get_existing_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get an existing summary by ID."""
        summary_id = arguments.get("summary_id")
        if not summary_id:
            return {
                "success": False,
                "error": {
                    "type": "missing_parameter",
                    "message": "summary_id is required for get_existing action"
                }
            }
        
        summary = await self.error_manager.get_summary(summary_id)
        if not summary:
            return {
                "success": False,
                "error": {
                    "type": "not_found",
                    "message": f"Summary not found: {summary_id}"
                }
            }
        
        # Enhance solutions if requested
        enhanced_solutions = []
        if arguments.get("enhance_solutions", False):
            try:
                enhanced_solutions = await self.error_manager.ai_summarizer.get_solution_suggestions(summary)
            except Exception as e:
                # Don't fail the whole request if enhancement fails
                enhanced_solutions = [f"Enhancement failed: {str(e)}"]
        
        return {
            "success": True,
            "data": {
                "summary": await self._format_summary(summary, arguments.get("include_solutions", True)),
                "enhanced_solutions": enhanced_solutions,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _generate_new_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new summary for specified errors."""
        error_ids = arguments.get("error_ids", [])
        if not error_ids:
            return {
                "success": False,
                "error": {
                    "type": "missing_parameter",
                    "message": "error_ids is required for generate_new action"
                }
            }
        
        # Validate error IDs exist
        valid_errors = []
        for error_id in error_ids:
            error = await self.error_manager.get_error(error_id)
            if error:
                valid_errors.append(error)
        
        if not valid_errors:
            return {
                "success": False,
                "error": {
                    "type": "no_valid_errors",
                    "message": "No valid errors found for the provided IDs"
                }
            }
        
        # Generate summary
        try:
            summary_id = await self.error_manager.request_summary(error_ids)
            if not summary_id:
                return {
                    "success": False,
                    "error": {
                        "type": "generation_failed",
                        "message": "Failed to generate summary"
                    }
                }
            
            # Retrieve the generated summary
            summary = await self.error_manager.get_summary(summary_id)
            
            # Enhance solutions if requested
            enhanced_solutions = []
            if arguments.get("enhance_solutions", False) and summary:
                try:
                    enhanced_solutions = await self.error_manager.ai_summarizer.get_solution_suggestions(summary)
                except Exception:
                    enhanced_solutions = []
            
            return {
                "success": True,
                "data": {
                    "summary": await self._format_summary(summary, arguments.get("include_solutions", True)) if summary else None,
                    "enhanced_solutions": enhanced_solutions,
                    "errors_analyzed": len(valid_errors),
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "type": "generation_error",
                    "message": f"Summary generation failed: {str(e)}"
                }
            }
    
    async def _get_summaries_for_error(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all summaries that include a specific error."""
        error_ids = arguments.get("error_ids", [])
        if not error_ids:
            return {
                "success": False,
                "error": {
                    "type": "missing_parameter",
                    "message": "error_ids is required for get_for_error action"
                }
            }
        
        all_summaries = []
        for error_id in error_ids:
            summaries = await self.error_manager.get_summaries_for_error(error_id)
            for summary in summaries:
                if summary not in all_summaries:  # Avoid duplicates
                    all_summaries.append(summary)
        
        # Sort by confidence and recency
        all_summaries.sort(
            key=lambda s: (s.confidence_score, s.generated_at),
            reverse=True
        )
        
        # Apply limit
        limit = arguments.get("limit", 10)
        all_summaries = all_summaries[:limit]
        
        formatted_summaries = []
        for summary in all_summaries:
            formatted_summaries.append(
                await self._format_summary(summary, arguments.get("include_solutions", True))
            )
        
        return {
            "success": True,
            "data": {
                "summaries": formatted_summaries,
                "total_found": len(formatted_summaries),
                "error_ids_queried": error_ids,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _list_recent_summaries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List recent summaries with optional filtering."""
        # Build filters
        filters = await self._build_summary_filters(arguments)
        
        # Get summaries
        summaries = await self.error_manager.get_summaries(filters)
        
        # Format summaries
        formatted_summaries = []
        for summary in summaries:
            formatted_summaries.append(
                await self._format_summary(summary, arguments.get("include_solutions", True))
            )
        
        # Get total count
        total_count = await self.error_manager.summary_store.get_summary_count(filters)
        
        return {
            "success": True,
            "data": {
                "summaries": formatted_summaries,
                "pagination": {
                    "total": total_count,
                    "limit": arguments.get("limit", 10),
                    "returned": len(formatted_summaries)
                },
                "filters_applied": {
                    "time_range": arguments.get("time_range", "24h"),
                    "min_confidence": arguments.get("min_confidence")
                },
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _build_summary_filters(self, arguments: Dict[str, Any]) -> SummaryFilters:
        """Build SummaryFilters from arguments."""
        # Parse time range
        time_range = arguments.get("time_range", "24h")
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
        
        return SummaryFilters(
            start_time=start_time,
            min_confidence=arguments.get("min_confidence"),
            limit=arguments.get("limit", 10),
            offset=0
        )
    
    async def _format_summary(self, summary, include_solutions: bool = True) -> Dict[str, Any]:
        """Format a summary for response."""
        formatted = {
            "id": summary.id,
            "error_ids": summary.error_ids,
            "error_count": len(summary.error_ids),
            "root_cause": summary.root_cause,
            "impact_assessment": summary.impact_assessment,
            "confidence_score": summary.confidence_score,
            "priority_score": summary.get_priority_score(),
            "is_high_confidence": summary.is_high_confidence(),
            "generated_at": summary.generated_at.isoformat(),
            "model_used": summary.model_used,
            "processing_time_ms": summary.processing_time_ms
        }
        
        if include_solutions:
            formatted["suggested_solutions"] = summary.suggested_solutions
            formatted["solution_count"] = len(summary.suggested_solutions)
        
        if summary.related_errors:
            formatted["related_errors"] = summary.related_errors
            formatted["related_error_count"] = len(summary.related_errors)
        
        return formatted
    
    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for tool description."""
        try:
            stats = await self.error_manager.get_statistics()
            return {
                "total_summaries": stats["storage"]["summaries"]["total_summaries"],
                "average_confidence": stats["storage"]["summaries"]["average_confidence"],
                "high_confidence_count": stats["storage"]["summaries"]["high_confidence_count"],
                "confidence_distribution": stats["storage"]["summaries"]["confidence_distribution"]
            }
        except Exception:
            return {"error": "Unable to retrieve statistics"}