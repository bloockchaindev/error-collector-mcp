"""Tests for storage components."""

import pytest
import tempfile
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from error_collector_mcp.storage.error_store import ErrorStore, ErrorFilters
from error_collector_mcp.storage.summary_store import SummaryStore, SummaryFilters
from error_collector_mcp.models import (
    BaseError, BrowserError, TerminalError, ErrorSummary,
    ErrorSource, ErrorCategory, ErrorSeverity
)


class TestErrorStore:
    """Test ErrorStore functionality."""
    
    @pytest.fixture
    async def error_store(self):
        """Create a temporary error store."""
        temp_dir = Path(tempfile.mkdtemp())
        store = ErrorStore(temp_dir, max_errors=100)
        await store.initialize()
        yield store
        await store.shutdown()
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_errors(self):
        """Create sample errors for testing."""
        return [
            BaseError(
                message="Test error 1",
                source=ErrorSource.BROWSER,
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.HIGH
            ),
            BrowserError(
                message="TypeError: Cannot read property 'foo' of null",
                url="https://example.com/page.html",
                line_number=42,
                error_type="TypeError"
            ),
            TerminalError(
                message="Command failed",
                command="npm install",
                exit_code=1,
                stderr_output="Permission denied"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_error(self, error_store, sample_errors):
        """Test storing and retrieving errors."""
        error = sample_errors[0]
        
        # Store error
        error_id = await error_store.store_error(error)
        assert error_id == error.id
        
        # Retrieve error
        retrieved_error = await error_store.get_error(error_id)
        assert retrieved_error is not None
        assert retrieved_error.message == error.message
        assert retrieved_error.source == error.source
    
    @pytest.mark.asyncio
    async def test_error_deduplication(self, error_store):
        """Test that duplicate errors are not stored twice."""
        error1 = BaseError(message="Duplicate error", source=ErrorSource.BROWSER)
        error2 = BaseError(message="Duplicate error", source=ErrorSource.BROWSER)
        
        # Store first error
        id1 = await error_store.store_error(error1)
        
        # Store duplicate error
        id2 = await error_store.store_error(error2)
        
        # Should return the same ID
        assert id1 == id2
        
        # Should only have one error stored
        count = await error_store.get_error_count()
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_error_filtering(self, error_store, sample_errors):
        """Test error filtering functionality."""
        # Store all sample errors
        for error in sample_errors:
            await error_store.store_error(error)
        
        # Filter by source
        browser_filters = ErrorFilters(sources={ErrorSource.BROWSER})
        browser_errors = await error_store.get_errors(browser_filters)
        assert len(browser_errors) == 2  # BaseError and BrowserError both have BROWSER source
        
        # Filter by category
        runtime_filters = ErrorFilters(categories={ErrorCategory.RUNTIME})
        runtime_errors = await error_store.get_errors(runtime_filters)
        assert len(runtime_errors) >= 1
        
        # Filter by severity
        high_filters = ErrorFilters(severities={ErrorSeverity.HIGH})
        high_errors = await error_store.get_errors(high_filters)
        assert len(high_errors) >= 1
    
    @pytest.mark.asyncio
    async def test_time_filtering(self, error_store):
        """Test time-based filtering."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=2)
        recent_time = now - timedelta(minutes=30)
        
        # Create errors with different timestamps
        old_error = BaseError(message="Old error", timestamp=old_time)
        recent_error = BaseError(message="Recent error", timestamp=recent_time)
        
        await error_store.store_error(old_error)
        await error_store.store_error(recent_error)
        
        # Filter for recent errors only
        recent_filters = ErrorFilters(start_time=now - timedelta(hours=1))
        recent_errors = await error_store.get_errors(recent_filters)
        
        assert len(recent_errors) == 1
        assert recent_errors[0].message == "Recent error"
    
    @pytest.mark.asyncio
    async def test_pagination(self, error_store):
        """Test pagination functionality."""
        # Store multiple errors
        for i in range(10):
            error = BaseError(message=f"Error {i}")
            await error_store.store_error(error)
        
        # Test pagination
        page1_filters = ErrorFilters(limit=5, offset=0)
        page1_errors = await error_store.get_errors(page1_filters)
        assert len(page1_errors) == 5
        
        page2_filters = ErrorFilters(limit=5, offset=5)
        page2_errors = await error_store.get_errors(page2_filters)
        assert len(page2_errors) == 5
        
        # Ensure no overlap
        page1_ids = {e.id for e in page1_errors}
        page2_ids = {e.id for e in page2_errors}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_delete_error(self, error_store, sample_errors):
        """Test error deletion."""
        error = sample_errors[0]
        error_id = await error_store.store_error(error)
        
        # Verify error exists
        assert await error_store.get_error(error_id) is not None
        
        # Delete error
        deleted = await error_store.delete_error(error_id)
        assert deleted is True
        
        # Verify error is gone
        assert await error_store.get_error(error_id) is None
        
        # Try to delete non-existent error
        deleted_again = await error_store.delete_error(error_id)
        assert deleted_again is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_errors(self, error_store):
        """Test cleanup of old errors."""
        now = datetime.utcnow()
        old_time = now - timedelta(days=35)  # Older than 30 days
        recent_time = now - timedelta(days=5)
        
        # Create old and recent errors
        old_error = BaseError(message="Old error", timestamp=old_time)
        recent_error = BaseError(message="Recent error", timestamp=recent_time)
        
        await error_store.store_error(old_error)
        await error_store.store_error(recent_error)
        
        # Cleanup errors older than 30 days
        deleted_count = await error_store.cleanup_old_errors(30)
        assert deleted_count == 1
        
        # Verify only recent error remains
        remaining_errors = await error_store.get_errors(ErrorFilters())
        assert len(remaining_errors) == 1
        assert remaining_errors[0].message == "Recent error"
    
    @pytest.mark.asyncio
    async def test_max_errors_enforcement(self, error_store):
        """Test that max errors limit is enforced."""
        # Store more errors than the limit (100)
        for i in range(105):
            error = BaseError(message=f"Error {i}")
            await error_store.store_error(error)
        
        # Should not exceed max limit
        count = await error_store.get_error_count()
        assert count <= 100
    
    @pytest.mark.asyncio
    async def test_statistics(self, error_store, sample_errors):
        """Test statistics generation."""
        # Store sample errors
        for error in sample_errors:
            await error_store.store_error(error)
        
        stats = await error_store.get_statistics()
        
        assert stats["total_errors"] == len(sample_errors)
        assert "by_source" in stats
        assert "by_category" in stats
        assert "by_severity" in stats
        assert "oldest_error" in stats
        assert "newest_error" in stats
    
    @pytest.mark.asyncio
    async def test_persistence(self, error_store, sample_errors):
        """Test that errors are persisted to disk."""
        # Store errors
        for error in sample_errors:
            await error_store.store_error(error)
        
        # Force save
        await error_store.force_save()
        
        # Create new store with same directory
        temp_dir = error_store.data_directory
        new_store = ErrorStore(temp_dir, max_errors=100)
        await new_store.initialize()
        
        try:
            # Should load existing errors
            count = await new_store.get_error_count()
            assert count == len(sample_errors)
        finally:
            await new_store.shutdown()


class TestSummaryStore:
    """Test SummaryStore functionality."""
    
    @pytest.fixture
    async def summary_store(self):
        """Create a temporary summary store."""
        temp_dir = Path(tempfile.mkdtemp())
        store = SummaryStore(temp_dir, max_summaries=50)
        await store.initialize()
        yield store
        await store.shutdown()
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_summaries(self):
        """Create sample summaries for testing."""
        return [
            ErrorSummary(
                error_ids=["error1", "error2"],
                root_cause="Null pointer dereference",
                impact_assessment="Application crash",
                suggested_solutions=["Add null check", "Use optional chaining"],
                confidence_score=0.9
            ),
            ErrorSummary(
                error_ids=["error3"],
                root_cause="Network timeout",
                impact_assessment="Request failure",
                suggested_solutions=["Increase timeout", "Add retry logic"],
                confidence_score=0.7
            ),
            ErrorSummary(
                error_ids=["error4", "error5"],
                root_cause="Permission denied",
                impact_assessment="Feature unavailable",
                suggested_solutions=["Check permissions", "Request access"],
                confidence_score=0.6
            )
        ]
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_summary(self, summary_store, sample_summaries):
        """Test storing and retrieving summaries."""
        summary = sample_summaries[0]
        
        # Store summary
        summary_id = await summary_store.store_summary(summary)
        assert summary_id == summary.id
        
        # Retrieve summary
        retrieved_summary = await summary_store.get_summary(summary_id)
        assert retrieved_summary is not None
        assert retrieved_summary.root_cause == summary.root_cause
        assert retrieved_summary.confidence_score == summary.confidence_score
    
    @pytest.mark.asyncio
    async def test_get_summaries_for_error(self, summary_store, sample_summaries):
        """Test retrieving summaries for a specific error."""
        # Store summaries
        for summary in sample_summaries:
            await summary_store.store_summary(summary)
        
        # Get summaries for error1
        summaries = await summary_store.get_summaries_for_error("error1")
        assert len(summaries) == 1
        assert summaries[0].root_cause == "Null pointer dereference"
        
        # Get summaries for error that appears in multiple summaries
        summaries = await summary_store.get_summaries_for_error("error2")
        assert len(summaries) == 1
    
    @pytest.mark.asyncio
    async def test_confidence_filtering(self, summary_store, sample_summaries):
        """Test filtering by confidence score."""
        # Store summaries
        for summary in sample_summaries:
            await summary_store.store_summary(summary)
        
        # Filter for high confidence summaries
        high_conf_filters = SummaryFilters(min_confidence=0.8)
        high_conf_summaries = await summary_store.get_summaries(high_conf_filters)
        assert len(high_conf_summaries) == 1
        assert high_conf_summaries[0].confidence_score == 0.9
        
        # Get high confidence summaries using convenience method
        high_conf_summaries2 = await summary_store.get_high_confidence_summaries(0.8)
        assert len(high_conf_summaries2) == 1
    
    @pytest.mark.asyncio
    async def test_time_filtering(self, summary_store):
        """Test time-based filtering."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=2)
        recent_time = now - timedelta(minutes=30)
        
        # Create summaries with different timestamps
        old_summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Old issue",
            generated_at=old_time,
            confidence_score=0.8
        )
        recent_summary = ErrorSummary(
            error_ids=["error2"],
            root_cause="Recent issue",
            generated_at=recent_time,
            confidence_score=0.8
        )
        
        await summary_store.store_summary(old_summary)
        await summary_store.store_summary(recent_summary)
        
        # Filter for recent summaries
        recent_summaries = await summary_store.get_recent_summaries(1)  # Last 1 hour
        assert len(recent_summaries) == 1
        assert recent_summaries[0].root_cause == "Recent issue"
    
    @pytest.mark.asyncio
    async def test_delete_summary(self, summary_store, sample_summaries):
        """Test summary deletion."""
        summary = sample_summaries[0]
        summary_id = await summary_store.store_summary(summary)
        
        # Verify summary exists
        assert await summary_store.get_summary(summary_id) is not None
        
        # Delete summary
        deleted = await summary_store.delete_summary(summary_id)
        assert deleted is True
        
        # Verify summary is gone
        assert await summary_store.get_summary(summary_id) is None
        
        # Verify error-to-summary mapping is updated
        summaries_for_error = await summary_store.get_summaries_for_error("error1")
        assert len(summaries_for_error) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_old_summaries(self, summary_store):
        """Test cleanup of old summaries."""
        now = datetime.utcnow()
        old_time = now - timedelta(days=35)
        recent_time = now - timedelta(days=5)
        
        # Create old and recent summaries
        old_summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Old issue",
            generated_at=old_time,
            confidence_score=0.8
        )
        recent_summary = ErrorSummary(
            error_ids=["error2"],
            root_cause="Recent issue",
            generated_at=recent_time,
            confidence_score=0.8
        )
        
        await summary_store.store_summary(old_summary)
        await summary_store.store_summary(recent_summary)
        
        # Cleanup summaries older than 30 days
        deleted_count = await summary_store.cleanup_old_summaries(30)
        assert deleted_count == 1
        
        # Verify only recent summary remains
        remaining_summaries = await summary_store.get_summaries(SummaryFilters())
        assert len(remaining_summaries) == 1
        assert remaining_summaries[0].root_cause == "Recent issue"
    
    @pytest.mark.asyncio
    async def test_statistics(self, summary_store, sample_summaries):
        """Test statistics generation."""
        # Store sample summaries
        for summary in sample_summaries:
            await summary_store.store_summary(summary)
        
        stats = await summary_store.get_statistics()
        
        assert stats["total_summaries"] == len(sample_summaries)
        assert stats["average_confidence"] > 0
        assert stats["high_confidence_count"] >= 0
        assert stats["errors_with_summaries"] > 0
        assert "confidence_distribution" in stats
    
    @pytest.mark.asyncio
    async def test_persistence(self, summary_store, sample_summaries):
        """Test that summaries are persisted to disk."""
        # Store summaries
        for summary in sample_summaries:
            await summary_store.store_summary(summary)
        
        # Force save
        await summary_store.force_save()
        
        # Create new store with same directory
        temp_dir = summary_store.data_directory
        new_store = SummaryStore(temp_dir, max_summaries=50)
        await new_store.initialize()
        
        try:
            # Should load existing summaries
            count = await new_store.get_summary_count()
            assert count == len(sample_summaries)
        finally:
            await new_store.shutdown()