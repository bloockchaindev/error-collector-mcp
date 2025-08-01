"""Error storage with in-memory cache and file persistence."""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict
import hashlib

from ..models import BaseError, BrowserError, TerminalError, ErrorSource, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class ErrorFilters:
    """Filters for error retrieval."""
    
    def __init__(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sources: Optional[Set[ErrorSource]] = None,
        categories: Optional[Set[ErrorCategory]] = None,
        severities: Optional[Set[ErrorSeverity]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.sources = sources or set()
        self.categories = categories or set()
        self.severities = severities or set()
        self.limit = limit
        self.offset = offset


class ErrorStore:
    """In-memory error store with file persistence and deduplication."""
    
    def __init__(self, data_directory: Path, max_errors: int = 10000):
        self.data_directory = data_directory
        self.max_errors = max_errors
        self.errors_dir = data_directory / "errors"
        self.errors_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self._errors: Dict[str, BaseError] = {}
        self._error_hashes: Dict[str, str] = {}  # hash -> error_id mapping
        self._errors_by_source: Dict[ErrorSource, Set[str]] = defaultdict(set)
        self._errors_by_category: Dict[ErrorCategory, Set[str]] = defaultdict(set)
        self._errors_by_severity: Dict[ErrorSeverity, Set[str]] = defaultdict(set)
        
        # Persistence settings
        self._dirty = False
        self._last_save = datetime.utcnow()
        self._save_interval = 60  # seconds
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the error store and load existing data."""
        await self._load_from_disk()
        
        # Start background save task
        asyncio.create_task(self._periodic_save())
        
        logger.info(f"Error store initialized with {len(self._errors)} errors")
    
    async def store_error(self, error: BaseError) -> str:
        """Store an error with deduplication."""
        async with self._lock:
            # Check for duplicate
            error_hash = self._calculate_error_hash(error)
            if error_hash in self._error_hashes:
                existing_id = self._error_hashes[error_hash]
                logger.debug(f"Duplicate error detected, returning existing ID: {existing_id}")
                return existing_id
            
            # Store new error
            self._errors[error.id] = error
            self._error_hashes[error_hash] = error.id
            
            # Update indices
            self._errors_by_source[error.source].add(error.id)
            self._errors_by_category[error.category].add(error.id)
            self._errors_by_severity[error.severity].add(error.id)
            
            # Mark as dirty for persistence
            self._dirty = True
            
            # Enforce max errors limit
            await self._enforce_max_errors()
            
            logger.debug(f"Stored error: {error.id}")
            return error.id
    
    async def get_error(self, error_id: str) -> Optional[BaseError]:
        """Get a specific error by ID."""
        return self._errors.get(error_id)
    
    async def get_errors(self, filters: ErrorFilters) -> List[BaseError]:
        """Get errors matching the specified filters."""
        async with self._lock:
            # Start with all error IDs
            candidate_ids = set(self._errors.keys())
            
            # Apply source filter
            if filters.sources:
                source_ids = set()
                for source in filters.sources:
                    source_ids.update(self._errors_by_source[source])
                candidate_ids &= source_ids
            
            # Apply category filter
            if filters.categories:
                category_ids = set()
                for category in filters.categories:
                    category_ids.update(self._errors_by_category[category])
                candidate_ids &= category_ids
            
            # Apply severity filter
            if filters.severities:
                severity_ids = set()
                for severity in filters.severities:
                    severity_ids.update(self._errors_by_severity[severity])
                candidate_ids &= severity_ids
            
            # Get actual error objects and apply time filters
            matching_errors = []
            for error_id in candidate_ids:
                error = self._errors[error_id]
                
                # Apply time filters
                if filters.start_time and error.timestamp < filters.start_time:
                    continue
                if filters.end_time and error.timestamp > filters.end_time:
                    continue
                
                matching_errors.append(error)
            
            # Sort by timestamp (newest first)
            matching_errors.sort(key=lambda e: e.timestamp, reverse=True)
            
            # Apply pagination
            start_idx = filters.offset
            end_idx = start_idx + filters.limit if filters.limit else None
            
            return matching_errors[start_idx:end_idx]
    
    async def get_error_count(self, filters: Optional[ErrorFilters] = None) -> int:
        """Get count of errors matching filters."""
        if filters is None:
            return len(self._errors)
        
        errors = await self.get_errors(filters)
        return len(errors)
    
    async def delete_error(self, error_id: str) -> bool:
        """Delete a specific error."""
        async with self._lock:
            if error_id not in self._errors:
                return False
            
            error = self._errors[error_id]
            
            # Remove from main storage
            del self._errors[error_id]
            
            # Remove from hash mapping
            error_hash = self._calculate_error_hash(error)
            if error_hash in self._error_hashes:
                del self._error_hashes[error_hash]
            
            # Remove from indices
            self._errors_by_source[error.source].discard(error_id)
            self._errors_by_category[error.category].discard(error_id)
            self._errors_by_severity[error.severity].discard(error_id)
            
            self._dirty = True
            logger.debug(f"Deleted error: {error_id}")
            return True
    
    async def cleanup_old_errors(self, retention_days: int) -> int:
        """Remove errors older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        
        old_error_ids = [
            error_id for error_id, error in self._errors.items()
            if error.timestamp < cutoff_time
        ]
        
        deleted_count = 0
        for error_id in old_error_ids:
            if await self.delete_error(error_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old errors")
        
        return deleted_count
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        async with self._lock:
            stats = {
                "total_errors": len(self._errors),
                "by_source": {
                    source.value: len(error_ids) 
                    for source, error_ids in self._errors_by_source.items()
                },
                "by_category": {
                    category.value: len(error_ids)
                    for category, error_ids in self._errors_by_category.items()
                },
                "by_severity": {
                    severity.value: len(error_ids)
                    for severity, error_ids in self._errors_by_severity.items()
                },
                "oldest_error": None,
                "newest_error": None
            }
            
            if self._errors:
                timestamps = [error.timestamp for error in self._errors.values()]
                stats["oldest_error"] = min(timestamps).isoformat()
                stats["newest_error"] = max(timestamps).isoformat()
            
            return stats
    
    def _calculate_error_hash(self, error: BaseError) -> str:
        """Calculate hash for error deduplication."""
        # Use message, source, and category for deduplication
        # This allows similar errors to be grouped together
        hash_content = f"{error.message}|{error.source.value}|{error.category.value}"
        
        # For browser errors, include URL to distinguish same error on different pages
        if isinstance(error, BrowserError) and error.url:
            hash_content += f"|{error.url}"
        
        # For terminal errors, include command to distinguish same error from different commands
        if isinstance(error, TerminalError) and error.command:
            hash_content += f"|{error.command}"
        
        return hashlib.sha256(hash_content.encode()).hexdigest()
    
    async def _enforce_max_errors(self) -> None:
        """Remove oldest errors if we exceed the maximum."""
        if len(self._errors) <= self.max_errors:
            return
        
        # Sort errors by timestamp and remove oldest
        errors_by_time = sorted(
            self._errors.values(),
            key=lambda e: e.timestamp
        )
        
        errors_to_remove = len(self._errors) - self.max_errors
        for error in errors_by_time[:errors_to_remove]:
            await self.delete_error(error.id)
        
        logger.info(f"Removed {errors_to_remove} oldest errors to enforce limit")
    
    async def _load_from_disk(self) -> None:
        """Load errors from disk storage."""
        try:
            errors_file = self.errors_dir / "errors.json"
            if not errors_file.exists():
                return
            
            with open(errors_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            loaded_count = 0
            for error_data in data.get("errors", []):
                try:
                    # Determine error type and create appropriate object
                    if error_data.get("source") == "browser":
                        error = BrowserError.from_dict(error_data)
                    elif error_data.get("source") == "terminal":
                        error = TerminalError.from_dict(error_data)
                    else:
                        error = BaseError.from_dict(error_data)
                    
                    # Store without deduplication check (loading existing data)
                    self._errors[error.id] = error
                    
                    # Update indices
                    self._errors_by_source[error.source].add(error.id)
                    self._errors_by_category[error.category].add(error.id)
                    self._errors_by_severity[error.severity].add(error.id)
                    
                    # Update hash mapping
                    error_hash = self._calculate_error_hash(error)
                    self._error_hashes[error_hash] = error.id
                    
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load error from disk: {e}")
                    continue
            
            logger.info(f"Loaded {loaded_count} errors from disk")
            
        except Exception as e:
            logger.error(f"Failed to load errors from disk: {e}")
    
    async def _save_to_disk(self) -> None:
        """Save errors to disk storage."""
        if not self._dirty:
            return
        
        try:
            errors_file = self.errors_dir / "errors.json"
            backup_file = self.errors_dir / "errors.json.backup"
            
            # Create backup of existing file
            if errors_file.exists():
                errors_file.rename(backup_file)
            
            # Prepare data for serialization
            data = {
                "version": "1.0",
                "saved_at": datetime.utcnow().isoformat(),
                "total_errors": len(self._errors),
                "errors": [error.to_dict() for error in self._errors.values()]
            }
            
            # Write to temporary file first
            temp_file = errors_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.rename(errors_file)
            
            # Remove backup if save was successful
            if backup_file.exists():
                backup_file.unlink()
            
            self._dirty = False
            self._last_save = datetime.utcnow()
            
            logger.debug(f"Saved {len(self._errors)} errors to disk")
            
        except Exception as e:
            logger.error(f"Failed to save errors to disk: {e}")
            # Restore backup if it exists
            backup_file = self.errors_dir / "errors.json.backup"
            if backup_file.exists():
                backup_file.rename(errors_file)
    
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
        """Shutdown the error store and save data."""
        await self.force_save()
        logger.info("Error store shutdown complete")