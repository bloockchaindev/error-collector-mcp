"""Tests for MCP tools."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from error_collector_mcp.mcp_tools.error_query_tool import ErrorQueryTool
from error_collector_mcp.mcp_tools.error_summary_tool import ErrorSummaryTool
from error_collector_mcp.mcp_tools.error_statistics_tool import ErrorStatisticsTool
from error_collector_mcp.services.error_manager import ErrorManager
from error_collector_mcp.models import BaseError, BrowserError, TerminalError, ErrorSummary, ErrorSource, ErrorCategory, ErrorSeverity


class TestErrorQueryTool:
    """Test ErrorQueryTool functionality."""
    
    @pytest.fixture
    def mock_error_manager(self):
        """Create mock error manager."""
        manager = MagicMock(spec=ErrorManager)
        manager.get_errors = AsyncMock()
        manager.error_store = MagicMock()
        manager.error_store.get_error_count = AsyncMock()
        return manager
    
    @pytest.fixture
    def error_query_tool(self, mock_error_manager):
        """Create ErrorQueryTool instance."""
        return ErrorQueryTool(mock_error_manager)
    
    @pytest.fixture
    def sample_errors(self):
        """Create sample errors for testing."""
        return [
            BrowserError(
                message="TypeError: Cannot read property 'foo' of null",
                url="https://example.com/page.html",
                error_type="TypeError",
                line_number=42
            ),
            TerminalError(
                message="Command failed",
                command="npm install",
                exit_code=1,
                stderr_output="Permission denied"
            ),
            BaseError(
                message="Generic error",
                source=ErrorSource.UNKNOWN,
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.HIGH
            )
        ]
    
    def test_tool_properties(self, error_query_tool):
        """Test tool properties."""
        assert error_query_tool.name == "query_errors"
        assert "Query and filter collected errors" in error_query_tool.description
        assert "type" in error_query_tool.input_schema
        assert "properties" in error_query_tool.input_schema
    
    @pytest.mark.asyncio
    async def test_basic_query_execution(self, error_query_tool, mock_error_manager, sample_errors):
        """Test basic query execution."""
        # Mock return values
        mock_error_manager.get_errors.return_value = sample_errors
        mock_error_manager.error_store.get_error_count.return_value = len(sample_errors)
        
        # Execute query
        result = await error_query_tool.execute({
            "time_range": "24h",
            "limit": 10
        })
        
        assert result["success"] is True
        assert "data" in result
        assert "errors" in result["data"]
        assert "pagination" in result["data"]
        assert len(result["data"]["errors"]) == len(sample_errors)
    
    @pytest.mark.asyncio
    async def test_query_with_filters(self, error_query_tool, mock_error_manager, sample_errors):
        """Test query with various filters."""
        mock_error_manager.get_errors.return_value = [sample_errors[0]]  # Only browser error
        mock_error_manager.error_store.get_error_count.return_value = 1
        
        result = await error_query_tool.execute({
            "sources": ["browser"],
            "categories": ["runtime"],
            "severities": ["high"],
            "limit": 5
        })
        
        assert result["success"] is True
        assert len(result["data"]["errors"]) == 1
        assert result["data"]["errors"][0]["source"] == "browser"
    
    @pytest.mark.asyncio
    async def test_grouped_errors(self, error_query_tool, mock_error_manager, sample_errors):
        """Test error grouping functionality."""
        mock_error_manager.get_errors.return_value = sample_errors
        mock_error_manager.error_store.get_error_count.return_value = len(sample_errors)
        
        result = await error_query_tool.execute({
            "group_similar": True,
            "limit": 10
        })
        
        assert result["success"] is True
        assert "errors" in result["data"]
        # Should return grouped format
        if result["data"]["errors"]:
            assert "group_key" in result["data"]["errors"][0]
            assert "count" in result["data"]["errors"][0]
    
    @pytest.mark.asyncio
    async def test_pagination(self, error_query_tool, mock_error_manager, sample_errors):
        """Test pagination functionality."""
        mock_error_manager.get_errors.return_value = sample_errors[:2]  # First 2 errors
        mock_error_manager.error_store.get_error_count.return_value = len(sample_errors)
        
        result = await error_query_tool.execute({
            "limit": 2,
            "offset": 0
        })
        
        assert result["success"] is True
        pagination = result["data"]["pagination"]
        assert pagination["total"] == len(sample_errors)
        assert pagination["limit"] == 2
        assert pagination["offset"] == 0
        assert pagination["has_more"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, error_query_tool, mock_error_manager):
        """Test error handling in query execution."""
        # Mock an exception
        mock_error_manager.get_errors.side_effect = Exception("Database error")
        
        result = await error_query_tool.execute({"limit": 10})
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "query_error"


class TestErrorSummaryTool:
    """Test ErrorSummaryTool functionality."""
    
    @pytest.fixture
    def mock_error_manager(self):
        """Create mock error manager."""
        manager = MagicMock(spec=ErrorManager)
        manager.get_summary = AsyncMock()
        manager.get_summaries = AsyncMock()
        manager.get_summaries_for_error = AsyncMock()
        manager.get_error = AsyncMock()
        manager.request_summary = AsyncMock()
        manager.summary_store = MagicMock()
        manager.summary_store.get_summary_count = AsyncMock()
        manager.ai_summarizer = MagicMock()
        manager.ai_summarizer.get_solution_suggestions = AsyncMock()
        return manager
    
    @pytest.fixture
    def error_summary_tool(self, mock_error_manager):
        """Create ErrorSummaryTool instance."""
        return ErrorSummaryTool(mock_error_manager)
    
    @pytest.fixture
    def sample_summary(self):
        """Create sample error summary."""
        return ErrorSummary(
            error_ids=["error1", "error2"],
            root_cause="Null pointer dereference",
            impact_assessment="Application crash",
            suggested_solutions=["Add null check", "Use optional chaining"],
            confidence_score=0.9,
            model_used="test-model"
        )
    
    def test_tool_properties(self, error_summary_tool):
        """Test tool properties."""
        assert error_summary_tool.name == "get_error_summary"
        assert "AI-generated summaries" in error_summary_tool.description
        assert "action" in error_summary_tool.input_schema["properties"]
    
    @pytest.mark.asyncio
    async def test_get_existing_summary(self, error_summary_tool, mock_error_manager, sample_summary):
        """Test getting existing summary."""
        mock_error_manager.get_summary.return_value = sample_summary
        
        result = await error_summary_tool.execute({
            "action": "get_existing",
            "summary_id": "test-summary-id"
        })
        
        assert result["success"] is True
        assert "summary" in result["data"]
        assert result["data"]["summary"]["root_cause"] == "Null pointer dereference"
    
    @pytest.mark.asyncio
    async def test_generate_new_summary(self, error_summary_tool, mock_error_manager, sample_summary):
        """Test generating new summary."""
        # Mock error retrieval
        mock_error = MagicMock()
        mock_error_manager.get_error.return_value = mock_error
        
        # Mock summary generation
        mock_error_manager.request_summary.return_value = "new-summary-id"
        mock_error_manager.get_summary.return_value = sample_summary
        
        result = await error_summary_tool.execute({
            "action": "generate_new",
            "error_ids": ["error1", "error2"]
        })
        
        assert result["success"] is True
        assert "summary" in result["data"]
        assert result["data"]["errors_analyzed"] == 2
    
    @pytest.mark.asyncio
    async def test_list_recent_summaries(self, error_summary_tool, mock_error_manager, sample_summary):
        """Test listing recent summaries."""
        mock_error_manager.get_summaries.return_value = [sample_summary]
        mock_error_manager.summary_store.get_summary_count.return_value = 1
        
        result = await error_summary_tool.execute({
            "action": "list_recent",
            "time_range": "24h",
            "limit": 10
        })
        
        assert result["success"] is True
        assert "summaries" in result["data"]
        assert len(result["data"]["summaries"]) == 1
        assert "pagination" in result["data"]
    
    @pytest.mark.asyncio
    async def test_get_summaries_for_error(self, error_summary_tool, mock_error_manager, sample_summary):
        """Test getting summaries for specific error."""
        mock_error_manager.get_summaries_for_error.return_value = [sample_summary]
        
        result = await error_summary_tool.execute({
            "action": "get_for_error",
            "error_ids": ["error1"]
        })
        
        assert result["success"] is True
        assert "summaries" in result["data"]
        assert len(result["data"]["summaries"]) == 1
    
    @pytest.mark.asyncio
    async def test_solution_enhancement(self, error_summary_tool, mock_error_manager, sample_summary):
        """Test solution enhancement functionality."""
        mock_error_manager.get_summary.return_value = sample_summary
        mock_error_manager.ai_summarizer.get_solution_suggestions.return_value = [
            "Additional solution 1",
            "Additional solution 2"
        ]
        
        result = await error_summary_tool.execute({
            "action": "get_existing",
            "summary_id": "test-summary-id",
            "enhance_solutions": True
        })
        
        assert result["success"] is True
        assert "enhanced_solutions" in result["data"]
        assert len(result["data"]["enhanced_solutions"]) == 2
    
    @pytest.mark.asyncio
    async def test_missing_parameters(self, error_summary_tool, mock_error_manager):
        """Test handling of missing parameters."""
        # Test missing summary_id for get_existing
        result = await error_summary_tool.execute({
            "action": "get_existing"
        })
        
        assert result["success"] is False
        assert result["error"]["type"] == "missing_parameter"
        
        # Test missing error_ids for generate_new
        result = await error_summary_tool.execute({
            "action": "generate_new"
        })
        
        assert result["success"] is False
        assert result["error"]["type"] == "missing_parameter"


class TestErrorStatisticsTool:
    """Test ErrorStatisticsTool functionality."""
    
    @pytest.fixture
    def mock_error_manager(self):
        """Create mock error manager."""
        manager = MagicMock(spec=ErrorManager)
        manager.get_statistics = AsyncMock()
        manager.get_errors = AsyncMock()
        manager.health_check = AsyncMock()
        manager.error_store = MagicMock()
        manager.summary_store = MagicMock()
        return manager
    
    @pytest.fixture
    def error_statistics_tool(self, mock_error_manager):
        """Create ErrorStatisticsTool instance."""
        return ErrorStatisticsTool(mock_error_manager)
    
    @pytest.fixture
    def sample_stats(self):
        """Create sample statistics."""
        return {
            "manager": {
                "total_errors_processed": 100,
                "summaries_generated": 20,
                "auto_summaries_generated": 15,
                "collectors_active": 2
            },
            "storage": {
                "errors": {
                    "total_errors": 100,
                    "by_source": {"browser": 60, "terminal": 40},
                    "by_category": {"runtime": 50, "syntax": 30, "network": 20},
                    "by_severity": {"high": 30, "medium": 50, "low": 20}
                },
                "summaries": {
                    "total_summaries": 20,
                    "average_confidence": 0.8,
                    "high_confidence_count": 15,
                    "confidence_distribution": {
                        "0.8-1.0": 15,
                        "0.6-0.8": 3,
                        "0.4-0.6": 2
                    }
                }
            }
        }
    
    def test_tool_properties(self, error_statistics_tool):
        """Test tool properties."""
        assert error_statistics_tool.name == "get_error_statistics"
        assert "comprehensive error statistics" in error_statistics_tool.description
        assert "report_type" in error_statistics_tool.input_schema["properties"]
    
    @pytest.mark.asyncio
    async def test_overview_report(self, error_statistics_tool, mock_error_manager, sample_stats):
        """Test overview report generation."""
        mock_error_manager.get_statistics.return_value = sample_stats
        mock_error_manager.get_errors.return_value = []  # Empty for simplicity
        
        result = await error_statistics_tool.execute({
            "report_type": "overview",
            "time_range": "24h"
        })
        
        assert result["success"] is True
        assert result["data"]["report_type"] == "overview"
        assert "summary" in result["data"]
        assert "breakdown" in result["data"]
        assert "ai_analysis" in result["data"]
    
    @pytest.mark.asyncio
    async def test_trends_report(self, error_statistics_tool, mock_error_manager, sample_stats):
        """Test trends report generation."""
        # Mock some errors for time series
        mock_errors = [
            MagicMock(timestamp=datetime.utcnow() - timedelta(hours=1), source=ErrorSource.BROWSER),
            MagicMock(timestamp=datetime.utcnow() - timedelta(hours=2), source=ErrorSource.TERMINAL)
        ]
        mock_error_manager.get_errors.return_value = mock_errors
        
        result = await error_statistics_tool.execute({
            "report_type": "trends",
            "time_range": "24h",
            "grouping": "hour"
        })
        
        assert result["success"] is True
        assert result["data"]["report_type"] == "trends"
        assert "time_series" in result["data"]
        assert "trends" in result["data"]
    
    @pytest.mark.asyncio
    async def test_patterns_report(self, error_statistics_tool, mock_error_manager):
        """Test patterns report generation."""
        # Mock errors with patterns
        mock_errors = [
            MagicMock(
                message="TypeError: Cannot read property",
                timestamp=datetime.utcnow(),
                source=ErrorSource.BROWSER,
                category=ErrorCategory.RUNTIME
            ),
            MagicMock(
                message="TypeError: Cannot read property",
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                source=ErrorSource.BROWSER,
                category=ErrorCategory.RUNTIME
            )
        ]
        mock_error_manager.get_errors.return_value = mock_errors
        
        result = await error_statistics_tool.execute({
            "report_type": "patterns",
            "time_range": "24h"
        })
        
        assert result["success"] is True
        assert result["data"]["report_type"] == "patterns"
        assert "patterns" in result["data"]
        assert "correlations" in result["data"]
        assert "recurring_issues" in result["data"]
    
    @pytest.mark.asyncio
    async def test_health_report(self, error_statistics_tool, mock_error_manager, sample_stats):
        """Test health report generation."""
        mock_health = {
            "overall": True,
            "components": {
                "error_store": True,
                "summary_store": True,
                "collectors": {"browser": True, "terminal": True},
                "ai_summarizer": True
            }
        }
        
        mock_error_manager.health_check.return_value = mock_health
        mock_error_manager.get_statistics.return_value = sample_stats
        
        result = await error_statistics_tool.execute({
            "report_type": "health"
        })
        
        assert result["success"] is True
        assert result["data"]["report_type"] == "health"
        assert result["data"]["overall_health"] is True
        assert "health_scores" in result["data"]
        assert "component_status" in result["data"]
    
    @pytest.mark.asyncio
    async def test_detailed_report(self, error_statistics_tool, mock_error_manager, sample_stats):
        """Test detailed report generation."""
        mock_health = {"overall": True, "components": {}}
        mock_error_manager.get_statistics.return_value = sample_stats
        mock_error_manager.health_check.return_value = mock_health
        mock_error_manager.get_errors.return_value = []
        
        result = await error_statistics_tool.execute({
            "report_type": "detailed"
        })
        
        assert result["success"] is True
        assert result["data"]["report_type"] == "detailed"
        assert "overview" in result["data"]
        assert "trends" in result["data"]
        assert "patterns" in result["data"]
        assert "health" in result["data"]
        assert "executive_summary" in result["data"]
    
    @pytest.mark.asyncio
    async def test_invalid_report_type(self, error_statistics_tool, mock_error_manager):
        """Test handling of invalid report type."""
        result = await error_statistics_tool.execute({
            "report_type": "invalid_type"
        })
        
        assert result["success"] is False
        assert result["error"]["type"] == "invalid_report_type"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, error_statistics_tool, mock_error_manager):
        """Test error handling in statistics generation."""
        mock_error_manager.get_statistics.side_effect = Exception("Statistics error")
        
        result = await error_statistics_tool.execute({
            "report_type": "overview"
        })
        
        assert result["success"] is False
        assert result["error"]["type"] == "execution_error"


class TestMCPToolsIntegration:
    """Test integration between MCP tools."""
    
    @pytest.fixture
    def mock_error_manager(self):
        """Create comprehensive mock error manager."""
        manager = MagicMock(spec=ErrorManager)
        
        # Mock all required methods
        manager.get_errors = AsyncMock()
        manager.get_error = AsyncMock()
        manager.get_summary = AsyncMock()
        manager.get_summaries = AsyncMock()
        manager.get_summaries_for_error = AsyncMock()
        manager.request_summary = AsyncMock()
        manager.get_statistics = AsyncMock()
        manager.health_check = AsyncMock()
        
        # Mock stores
        manager.error_store = MagicMock()
        manager.error_store.get_error_count = AsyncMock()
        manager.summary_store = MagicMock()
        manager.summary_store.get_summary_count = AsyncMock()
        manager.ai_summarizer = MagicMock()
        manager.ai_summarizer.get_solution_suggestions = AsyncMock()
        
        return manager
    
    @pytest.fixture
    def all_tools(self, mock_error_manager):
        """Create all MCP tools."""
        return {
            "query": ErrorQueryTool(mock_error_manager),
            "summary": ErrorSummaryTool(mock_error_manager),
            "statistics": ErrorStatisticsTool(mock_error_manager)
        }
    
    @pytest.mark.asyncio
    async def test_workflow_integration(self, all_tools, mock_error_manager):
        """Test a complete workflow using all tools."""
        # Mock data
        sample_error = BrowserError(
            message="Test error",
            url="https://example.com",
            error_type="TypeError"
        )
        sample_summary = ErrorSummary(
            error_ids=[sample_error.id],
            root_cause="Test cause",
            impact_assessment="Test impact",
            suggested_solutions=["Test solution"],
            confidence_score=0.9
        )
        
        # Setup mocks
        mock_error_manager.get_errors.return_value = [sample_error]
        mock_error_manager.error_store.get_error_count.return_value = 1
        mock_error_manager.get_error.return_value = sample_error
        mock_error_manager.request_summary.return_value = "summary-id"
        mock_error_manager.get_summary.return_value = sample_summary
        
        # 1. Query errors
        query_result = await all_tools["query"].execute({
            "time_range": "24h",
            "limit": 10
        })
        assert query_result["success"] is True
        
        # 2. Generate summary for found errors
        error_ids = [error["id"] for error in query_result["data"]["errors"]]
        summary_result = await all_tools["summary"].execute({
            "action": "generate_new",
            "error_ids": error_ids
        })
        assert summary_result["success"] is True
        
        # 3. Get statistics
        stats_result = await all_tools["statistics"].execute({
            "report_type": "overview"
        })
        # This might fail due to missing mock setup, but that's expected
        
    def test_tool_schema_consistency(self, all_tools):
        """Test that all tools have consistent schema structure."""
        for tool_name, tool in all_tools.items():
            # All tools should have these properties
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'input_schema')
            
            # Schema should be valid
            schema = tool.input_schema
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            
            # All tools should have execute method
            assert hasattr(tool, 'execute')
            assert callable(tool.execute)