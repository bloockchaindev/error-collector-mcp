"""AI summarization service using OpenRouter API."""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import json
import hashlib
from dataclasses import dataclass

import aiohttp
from openai import AsyncOpenAI

from ..models import BaseError, BrowserError, TerminalError, ErrorSummary, ErrorCategory
from ..config import OpenRouterConfig
from .prompt_templates import PromptTemplates


logger = logging.getLogger(__name__)


@dataclass
class SummarizationRequest:
    """Request for error summarization."""
    errors: List[BaseError]
    request_id: str
    priority: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(self, max_requests_per_minute: int = 20):
        self.max_requests_per_minute = max_requests_per_minute
        self.requests = []
        self.backoff_until = None
        self.backoff_multiplier = 1
    
    async def acquire(self) -> bool:
        """Acquire permission to make a request."""
        now = time.time()
        
        # Check if we're in backoff period
        if self.backoff_until and now < self.backoff_until:
            wait_time = self.backoff_until - now
            logger.debug(f"Rate limiter: waiting {wait_time:.1f}s due to backoff")
            await asyncio.sleep(wait_time)
            return False
        
        # Clean old requests
        minute_ago = now - 60
        self.requests = [req_time for req_time in self.requests if req_time > minute_ago]
        
        # Check if we can make a request
        if len(self.requests) >= self.max_requests_per_minute:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = 60 - (now - oldest_request)
            logger.debug(f"Rate limiter: waiting {wait_time:.1f}s due to rate limit")
            await asyncio.sleep(wait_time)
            return False
        
        # Record this request
        self.requests.append(now)
        return True
    
    def set_backoff(self, duration: float = None):
        """Set backoff period after rate limit or error."""
        if duration is None:
            duration = min(60 * self.backoff_multiplier, 300)  # Max 5 minutes
        
        self.backoff_until = time.time() + duration
        self.backoff_multiplier = min(self.backoff_multiplier * 2, 8)
        logger.warning(f"Rate limiter: backing off for {duration:.1f}s")
    
    def reset_backoff(self):
        """Reset backoff after successful request."""
        self.backoff_until = None
        self.backoff_multiplier = 1


class AISummarizer:
    """AI-powered error summarization service."""
    
    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        # Rate limiting and queue management
        self.rate_limiter = RateLimiter(max_requests_per_minute=15)
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.processing_requests: Dict[str, SummarizationRequest] = {}
        
        # Error grouping
        self.similarity_threshold = 0.8
        self.max_errors_per_summary = 10
        
        # Background processing
        self._processing_task = None
        self._is_running = False
    
    async def start(self) -> None:
        """Start the AI summarizer service."""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_queue())
        logger.info("AI summarizer service started")
    
    async def stop(self) -> None:
        """Stop the AI summarizer service."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AI summarizer service stopped")
    
    async def summarize_error(self, error: BaseError) -> ErrorSummary:
        """Summarize a single error."""
        return await self.summarize_error_group([error])
    
    async def summarize_error_group(self, errors: List[BaseError]) -> ErrorSummary:
        """Summarize a group of related errors."""
        if not errors:
            raise ValueError("Cannot summarize empty error list")
        
        # Limit the number of errors to process
        if len(errors) > self.max_errors_per_summary:
            errors = errors[:self.max_errors_per_summary]
            logger.warning(f"Truncated error group to {self.max_errors_per_summary} errors")
        
        # Create summarization request
        request_id = self._generate_request_id(errors)
        request = SummarizationRequest(
            errors=errors,
            request_id=request_id,
            priority=self._calculate_priority(errors)
        )
        
        # Add to queue
        await self.request_queue.put(request)
        self.processing_requests[request_id] = request
        
        # Wait for processing (with timeout)
        timeout = 60  # 60 seconds timeout
        start_time = time.time()
        
        while request_id in self.processing_requests:
            if time.time() - start_time > timeout:
                # Remove from processing requests
                self.processing_requests.pop(request_id, None)
                raise TimeoutError(f"Summarization request {request_id} timed out")
            
            await asyncio.sleep(0.1)
        
        # The result should be stored in the request object
        if hasattr(request, 'result'):
            return request.result
        else:
            raise RuntimeError(f"Summarization request {request_id} failed")
    
    async def group_similar_errors(self, errors: List[BaseError]) -> List[List[BaseError]]:
        """Group similar errors together for batch summarization."""
        if not errors:
            return []
        
        groups = []
        ungrouped_errors = errors.copy()
        
        while ungrouped_errors:
            # Start a new group with the first ungrouped error
            current_error = ungrouped_errors.pop(0)
            current_group = [current_error]
            
            # Find similar errors
            similar_errors = []
            for error in ungrouped_errors:
                if self._are_errors_similar(current_error, error):
                    similar_errors.append(error)
            
            # Remove similar errors from ungrouped list
            for error in similar_errors:
                ungrouped_errors.remove(error)
                current_group.append(error)
            
            groups.append(current_group)
        
        return groups
    
    async def get_solution_suggestions(self, summary: ErrorSummary) -> List[str]:
        """Get additional solution suggestions for a summary."""
        try:
            # Create a focused prompt for solution generation
            prompt = self._create_solution_prompt(summary)
            
            # Wait for rate limit
            await self.rate_limiter.acquire()
            
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software developer who provides practical, actionable solutions to programming errors. Focus on specific, implementable fixes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=min(500, self.config.max_tokens),
                temperature=0.3,  # Lower temperature for more focused solutions
                timeout=self.config.timeout
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Parse solutions from response
            content = response.choices[0].message.content.strip()
            solutions = self._parse_solutions_from_response(content)
            
            # Reset backoff on success
            self.rate_limiter.reset_backoff()
            
            logger.debug(f"Generated {len(solutions)} additional solutions in {processing_time}ms")
            return solutions
            
        except Exception as e:
            logger.error(f"Failed to generate additional solutions: {e}")
            self.rate_limiter.set_backoff()
            return []
    
    def _generate_request_id(self, errors: List[BaseError]) -> str:
        """Generate a unique request ID for error group."""
        error_ids = sorted([error.id for error in errors])
        content = "|".join(error_ids)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _calculate_priority(self, errors: List[BaseError]) -> int:
        """Calculate priority for summarization request."""
        # Higher priority for more errors and higher severity
        priority = len(errors)
        
        for error in errors:
            if error.severity.value == "critical":
                priority += 10
            elif error.severity.value == "high":
                priority += 5
            elif error.severity.value == "medium":
                priority += 2
        
        return priority
    
    def _are_errors_similar(self, error1: BaseError, error2: BaseError) -> bool:
        """Check if two errors are similar enough to group together."""
        # Same error type and category
        if error1.source != error2.source or error1.category != error2.category:
            return False
        
        # Calculate message similarity
        similarity = self._calculate_message_similarity(error1.message, error2.message)
        if similarity < self.similarity_threshold:
            return False
        
        # Additional checks for specific error types
        if isinstance(error1, BrowserError) and isinstance(error2, BrowserError):
            # Same error type and similar URL
            if error1.error_type != error2.error_type:
                return False
            
            # Check if URLs are from the same domain
            try:
                from urllib.parse import urlparse
                domain1 = urlparse(error1.url).netloc
                domain2 = urlparse(error2.url).netloc
                if domain1 != domain2:
                    return False
            except:
                pass
        
        elif isinstance(error1, TerminalError) and isinstance(error2, TerminalError):
            # Similar commands
            cmd_similarity = self._calculate_message_similarity(error1.command, error2.command)
            if cmd_similarity < 0.6:  # Lower threshold for commands
                return False
        
        return True
    
    def _calculate_message_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between two error messages."""
        if not msg1 or not msg2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(msg1.lower().split())
        tokens2 = set(msg2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
    
    async def _process_queue(self) -> None:
        """Background task to process summarization requests."""
        while self._is_running:
            try:
                # Get request from queue (with timeout)
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the request
                try:
                    summary = await self._process_summarization_request(request)
                    request.result = summary
                except Exception as e:
                    logger.error(f"Failed to process summarization request {request.request_id}: {e}")
                    request.error = e
                finally:
                    # Remove from processing requests
                    self.processing_requests.pop(request.request_id, None)
                
            except Exception as e:
                logger.error(f"Error in summarization queue processing: {e}")
                await asyncio.sleep(1)
    
    async def _process_summarization_request(self, request: SummarizationRequest) -> ErrorSummary:
        """Process a single summarization request."""
        errors = request.errors
        
        # Wait for rate limit
        await self.rate_limiter.acquire()
        
        try:
            # Create prompt
            prompt = self._create_summarization_prompt(errors)
            
            start_time = time.time()
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Parse response
            content = response.choices[0].message.content.strip()
            summary_data = self._parse_summary_response(content)
            
            # Create ErrorSummary object
            summary = ErrorSummary(
                error_ids=[error.id for error in errors],
                root_cause=summary_data.get("root_cause", "Unknown error cause"),
                impact_assessment=summary_data.get("impact_assessment", "Impact unclear"),
                suggested_solutions=summary_data.get("suggested_solutions", []),
                confidence_score=summary_data.get("confidence_score", 0.5),
                model_used=self.config.model,
                processing_time_ms=processing_time
            )
            
            # Reset backoff on success
            self.rate_limiter.reset_backoff()
            
            logger.debug(f"Generated summary for {len(errors)} errors in {processing_time}ms")
            return summary
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            self.rate_limiter.set_backoff()
            raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for error summarization."""
        return PromptTemplates.get_system_prompt()
    
    def _create_summarization_prompt(self, errors: List[BaseError]) -> str:
        """Create a prompt for error summarization."""
        if len(errors) == 1:
            return PromptTemplates.get_single_error_prompt(errors[0])
        else:
            # Check if all errors are from the same category
            categories = set(error.category for error in errors)
            if len(categories) == 1:
                return PromptTemplates.get_category_specific_prompt(list(categories)[0], errors)
            else:
                return PromptTemplates.get_multi_error_prompt(errors)
    
    def _create_solution_prompt(self, summary: ErrorSummary) -> str:
        """Create a prompt for additional solution generation."""
        summary_dict = {
            'root_cause': summary.root_cause,
            'impact_assessment': summary.impact_assessment,
            'suggested_solutions': summary.suggested_solutions
        }
        return PromptTemplates.get_solution_enhancement_prompt(summary_dict)
    
    def _parse_summary_response(self, content: str) -> Dict[str, Any]:
        """Parse the AI response into structured summary data."""
        try:
            # Try to parse as JSON first
            if content.strip().startswith('{'):
                return json.loads(content)
            
            # Fallback: extract information from text
            lines = content.strip().split('\n')
            summary_data = {
                "root_cause": "Error analysis provided",
                "impact_assessment": "Impact assessment provided",
                "suggested_solutions": [],
                "confidence_score": 0.7
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "root cause" in line.lower():
                    current_section = "root_cause"
                elif "impact" in line.lower():
                    current_section = "impact_assessment"
                elif "solution" in line.lower():
                    current_section = "suggested_solutions"
                elif line.startswith('-') or line.startswith('•'):
                    if current_section == "suggested_solutions":
                        solution = line.lstrip('-•').strip()
                        if solution:
                            summary_data["suggested_solutions"].append(solution)
                elif current_section and not line.startswith('-'):
                    if current_section in ["root_cause", "impact_assessment"]:
                        summary_data[current_section] = line
            
            return summary_data
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON, using fallback")
            return {
                "root_cause": content[:200] + "..." if len(content) > 200 else content,
                "impact_assessment": "Unable to assess impact from response",
                "suggested_solutions": ["Review the error details and consult documentation"],
                "confidence_score": 0.3
            }
    
    def _parse_solutions_from_response(self, content: str) -> List[str]:
        """Parse solutions from AI response."""
        solutions = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                solution = line.lstrip('-•').strip()
                if solution and len(solution) > 10:  # Filter out very short solutions
                    solutions.append(solution)
        
        return solutions[:5]  # Limit to 5 solutions