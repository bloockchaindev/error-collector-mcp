"""Base collector interface for error collection."""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import BaseError


class BaseCollector(ABC):
    """Abstract base class for error collectors."""
    
    def __init__(self, name: str):
        self.name = name
        self._is_collecting = False
    
    @abstractmethod
    async def start_collection(self) -> None:
        """Start collecting errors from the source."""
        pass
    
    @abstractmethod
    async def stop_collection(self) -> None:
        """Stop collecting errors from the source."""
        pass
    
    @abstractmethod
    async def get_collected_errors(self) -> List[BaseError]:
        """Get all collected errors since last retrieval."""
        pass
    
    @property
    def is_collecting(self) -> bool:
        """Check if collector is currently active."""
        return self._is_collecting
    
    async def health_check(self) -> bool:
        """Check if the collector is healthy and operational."""
        return True