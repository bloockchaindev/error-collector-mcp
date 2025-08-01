"""Summary storage for AI-generated error summaries."""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from ..models import ErrorSummary


logger = logging.getLogger(__name__)


class SummaryFilters:
    """Filters for summary retrieval."""
    
    def __init__(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        error_ids: Optional[Set[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.min_confidence = min_confidence
        self.error_ids = error_ids or set()
        self.limit = limit
        self.offset = offset


class SummaryStore:
    """Storage for error summaries with indexing and retrieval."""
    
    def __init__(self, data_directory: Path, max_summaries: int = 5000):
        self.data_directory = data_directory
        self.max_summaries = max_summaries
        self.summaries_dir = data_directory / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self._summaries: Dict[str, ErrorSummary] = {}
        self._summaries_by_error: Dict[str, Set[str]] = {}  # error_id -> summary_ids
        
        # Persistence settings
        self._dirty = False
        self._last_save = datetime.utcnow()
        self._save_interval = 60  # seconds
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the summary store and load existing data."""
        await self._load_from_disk()
        
        # Start background save task
        asyncio.create_task(self._periodic_save())
        
        logger.info(f"Summary store initialized with {len(self._summaries)} summaries")
    
    async def store_summary(self, summary: ErrorSummary) -> str:
        """Store an error summary."""
        async with self._lock:
            self._summaries[summary.id] = summary
            
            # Update error-to-summary mapping
            for error_id in summary.error_ids:
                if error_id not in self._summaries_by_error:
                    self._summaries_by_error[error_id] = set()
                self._summaries_by_error[error_id].add(summary.id)
            
            # Mark as dirty for persistence
            self._dirty = True
            
            # Enforce max summaries limit
            await self._enforce_max_summaries()
            
            logger.debug(f"Stored summary: {summary.id}")
            return summary.id
    
    async def get_summary(self, summary_id: str) -> Optional[ErrorSummary]:
        """Get a specific summary by ID."""
        return self._summaries.get(summary_id)
    
    async def get_summaries(self, filters: SummaryFilters) -> List[ErrorSummary]:
        """Get summaries matching the specified filters."""
        async with self._lock:
            matching_summaries = []
            
            for summary in self._summaries.values():
                # Apply time filters
                if filters.start_time and summary.generated_at < filters.start_time:
                    continue
                if filters.end_time and summary.generated_at > filters.end_time:
                    continue
                
                # Apply confidence filter
                if filters.min_confidence and summary.confidence_score < filters.min_confidence:
                    continue
                
                # Apply error ID filter
                if filters.error_ids:
                    if not any(error_id in summary.error_ids for error_id in filters.error_ids):
                        continue
                
                matching_summaries.append(summary)
            
            # Sort by priority score (highest first), then by generation time (newest first)
            matching_summaries.sort(
                key=lambda s: (s.get_priority_score(), s.generated_at),
                reverse=True
            )
            
            # Apply pagination
            start_idx = filters.offset
            end_idx = start_idx + filters.limit if filters.limit else None
            
            return matching_summaries[start_idx:end_idx]
    
    async def get_summaries_for_error(self, error_id: str) -> List[ErrorSummary]:
        """Get all summaries that include a specific error."""
        summary_ids = self._summaries_by_error.get(error_id, set())
        summaries = []
        
        for summary_id in summary_ids:
            summary = self._summaries.get(summary_id)
            if summary:
                summaries.append(summary)
        
        # Sort by confidence and recency
        summaries.sort(
            key=lambda s: (s.confidence_score, s.generated_at),
            reverse=True
        )
        
        return summaries
    
    async def get_summary_count(self, filters: Optional[SummaryFilters] = None) -> int:
        """Get count of summaries matching filters."""
        if filters is None:
            return len(self._summaries)
        
        summaries = await self.get_summaries(filters)
        return len(summaries)
    
    async def delete_summary(self, summary_id: str) -> bool:
        """Delete a specific summary."""
        async with self._lock:
            if summary_id not in self._summaries:
                return False
            
            summary = self._summaries[summary_id]
            
            # Remove from main storage
            del self._summaries[summary_id]
            
            # Remove from error-to-summary mapping
            for error_id in summary.error_ids:
                if error_id in self._summaries_by_error:
                    self._summaries_by_error[error_id].discard(summary_id)
                    if not self._summaries_by_error[error_id]:
                        del self._summaries_by_error[error_id]
            
            self._dirty = True
            logger.debug(f"Deleted summary: {summary_id}")
            return True
    
    async def cleanup_old_summaries(self, retention_days: int) -> int:
        """Remove summaries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        
        old_summary_ids = [
            summary_id for summary_id, summary in self._summaries.items()
            if summary.generated_at < cutoff_time
        ]
        
        deleted_count = 0
        for summary_id in old_summary_ids:
            if await self.delete_summary(summary_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old summaries")
        
        return deleted_count
    
    async def get_high_confidence_summaries(self, threshold: float = 0.8) -> List[ErrorSummary]:
        """Get summaries with high confidence scores."""
        filters = SummaryFilters(min_confidence=threshold)
        return await self.get_summaries(filters)
    
    async def get_recent_summaries(self, hours: int = 24) -> List[ErrorSummary]:
        """Get summaries generated in the last N hours."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        filters = SummaryFilters(start_time=start_time)
        return await self.get_summaries(filters)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get summary storage statistics."""
        async with self._lock:
            if not self._summaries:
                return {
                    "total_summaries": 0,
                    "average_confidence": 0.0,
                    "high_confidence_count": 0,
                    "errors_with_summaries": 0,
                    "oldest_summary": None,
                    "newest_summary": None
                }
            
            confidences = [s.confidence_score for s in self._summaries.values()]
            timestamps = [s.generated_at for s in self._summaries.values()]
            
            stats = {
                "total_summaries": len(self._summaries),
                "average_confidence": sum(confidences) / len(confidences),
                "high_confidence_count": len([c for c in confidences if c >= 0.8]),
                "errors_with_summaries": len(self._summaries_by_error),
                "oldest_summary": min(timestamps).isoformat(),
                "newest_summary": max(timestamps).isoformat(),
                "confidence_distribution": {
                    "0.0-0.2": len([c for c in confidences if 0.0 <= c < 0.2]),
                    "0.2-0.4": len([c for c in confidences if 0.2 <= c < 0.4]),
                    "0.4-0.6": len([c for c in confidences if 0.4 <= c < 0.6]),
                    "0.6-0.8": len([c for c in confidences if 0.6 <= c < 0.8]),
                    "0.8-1.0": len([c for c in confidences if 0.8 <= c <= 1.0])
                }
            }
            
            return stats
    
    async def _enforce_max_summaries(self) -> None:
        """Remove oldest summaries if we exceed the maximum."""
        if len(self._summaries) <= self.max_summaries:
            return
        
        # Sort summaries by generation time and remove oldest
        summaries_by_time = sorted(
            self._summaries.values(),
            key=lambda s: s.generated_at
        )
        
        summaries_to_remove = len(self._summaries) - self.max_summaries
        for summary in summaries_by_time[:summaries_to_remove]:
            await self.delete_summary(summary.id)
        
        logger.info(f"Removed {summaries_to_remove} oldest summaries to enforce limit")
    
    async def _load_from_disk(self) -> None:
        """Load summaries from disk storage."""
        try:
            summaries_file = self.summaries_dir / "summaries.json"
            if not summaries_file.exists():
                return
            
            with open(summaries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            loaded_count = 0
            for summary_data in data.get("summaries", []):
                try:
                    summary = ErrorSummary.from_dict(summary_data)
                    
                    # Store without limit check (loading existing data)
                    self._summaries[summary.id] = summary
                    
                    # Update error-to-summary mapping
                    for error_id in summary.error_ids:
                        if error_id not in self._summaries_by_error:
                            self._summaries_by_error[error_id] = set()
                        self._summaries_by_error[error_id].add(summary.id)
                    
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load summary from disk: {e}")
                    continue
            
            logger.info(f"Loaded {loaded_count} summaries from disk")
            
        except Exception as e:
            logger.error(f"Failed to load summaries from disk: {e}")
    
    async def _save_to_disk(self) -> None:
        """Save summaries to disk storage."""
        if not self._dirty:
            return
        
        try:
            summaries_file = self.summaries_dir / "summaries.json"
            backup_file = self.summaries_dir / "summaries.json.backup"
            
            # Create backup of existing file
            if summaries_file.exists():
                summaries_file.rename(backup_file)
            
            # Prepare data for serialization
            data = {
                "version": "1.0",
                "saved_at": datetime.utcnow().isoformat(),
                "total_summaries": len(self._summaries),
                "summaries": [summary.to_dict() for summary in self._summaries.values()]
            }
            
            # Write to temporary file first
            temp_file = summaries_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.rename(summaries_file)
            
            # Remove backup if save was successful
            if backup_file.exists():
                backup_file.unlink()
            
            self._dirty = False
            self._last_save = datetime.utcnow()
            
            logger.debug(f"Saved {len(self._summaries)} summaries to disk")
            
        except Exception as e:
            logger.error(f"Failed to save summaries to disk: {e}")
            # Restore backup if it exists
            backup_file = self.summaries_dir / "summaries.json.backup"
            if backup_file.exists():
                backup_file.rename(summaries_file)
    
    async def _periodic_save(self) -> None:
        """Periodically save dirty data to disk."""
        while True:
            try:
                await asyncio.sleep(self._save_interval)
                if self._dirty:
                    await self._save_to_disk()
            except Exception as e:
                logger.error(f"Error in periodic save: {e}")
    
    async def force_save(self) -> None:
        """Force immediate save to disk."""
        await self._save_to_disk()
    
    async def shutdown(self) -> None:
        """Shutdown the summary store and save data."""
        await self.force_save()
        logger.info("Summary store shutdown complete")