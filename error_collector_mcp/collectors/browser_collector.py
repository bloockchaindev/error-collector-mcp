"""Browser console error collector with multiple collection methods."""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Set
from dataclasses import dataclass
import tempfile
import websockets
import aiohttp
from aiohttp import web

from .base_collector import BaseCollector
from ..models import BrowserError, ErrorSeverity


logger = logging.getLogger(__name__)


@dataclass
class BrowserErrorData:
    """Raw browser error data before processing."""
    message: str
    source: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_type: str = "Error"
    stack_trace: Optional[str] = None
    url: str = ""
    user_agent: str = ""
    page_title: str = ""
    timestamp: Optional[datetime] = None
    additional_data: Dict[str, Any] = None


class BrowserConsoleCollector(BaseCollector):
    """Collector for browser console errors with multiple collection methods."""
    
    def __init__(self, name: str = "browser", port: int = 8765):
        super().__init__(name)
        self._collected_errors: List[BrowserError] = []
        self._error_callbacks: List[Callable[[BrowserError], None]] = []
        
        # WebSocket server for real-time collection
        self._websocket_port = port
        self._websocket_server = None
        self._connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # HTTP server for bookmarklet/extension communication
        self._http_port = port + 1
        self._http_server = None
        self._http_app = None
        
        # File-based collection
        self._log_file = self._get_log_file()
        
        # Error filtering
        self._ignored_patterns = [
            r"ResizeObserver loop limit exceeded",
            r"Non-Error promise rejection captured",
            r"Script error\.",
            r"Network request failed.*chrome-extension"
        ]
        self._ignored_domains = [
            "chrome-extension://",
            "moz-extension://",
            "safari-extension://"
        ]
    
    async def start_collection(self) -> None:
        """Start collecting browser console errors."""
        if self._is_collecting:
            logger.warning("Browser collector is already running")
            return
        
        self._is_collecting = True
        
        # Start WebSocket server
        await self._start_websocket_server()
        
        # Start HTTP server
        await self._start_http_server()
        
        # Start file monitoring
        asyncio.create_task(self._monitor_log_file())
        
        logger.info(f"Browser error collection started on ports {self._websocket_port} (WS) and {self._http_port} (HTTP)")
        logger.info(f"Log file: {self._log_file}")
    
    async def stop_collection(self) -> None:
        """Stop collecting browser console errors."""
        if not self._is_collecting:
            return
        
        self._is_collecting = False
        
        # Stop WebSocket server
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()
            self._websocket_server = None
        
        # Stop HTTP server
        if self._http_server:
            await self._http_server.cleanup()
            self._http_server = None
        
        logger.info("Browser error collection stopped")
    
    async def get_collected_errors(self) -> List[BrowserError]:
        """Get all collected errors since last retrieval."""
        errors = self._collected_errors.copy()
        self._collected_errors.clear()
        return errors
    
    def add_error_callback(self, callback: Callable[[BrowserError], None]) -> None:
        """Add a callback to be notified of new errors."""
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[BrowserError], None]) -> None:
        """Remove an error callback."""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def get_bookmarklet_code(self) -> str:
        """Generate bookmarklet code for manual error collection."""
        bookmarklet_js = f"""
javascript:(function(){{
    const originalConsoleError = console.error;
    const originalConsoleWarn = console.warn;
    const serverUrl = 'http://localhost:{self._http_port}/collect';
    
    function sendError(errorData) {{
        fetch(serverUrl, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(errorData),
            mode: 'cors'
        }}).catch(e => console.log('Failed to send error:', e));
    }}
    
    // Override console methods
    console.error = function(...args) {{
        originalConsoleError.apply(console, args);
        sendError({{
            message: args.join(' '),
            source: 'console.error',
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString(),
            error_type: 'ConsoleError'
        }});
    }};
    
    console.warn = function(...args) {{
        originalConsoleWarn.apply(console, args);
        sendError({{
            message: args.join(' '),
            source: 'console.warn',
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString(),
            error_type: 'ConsoleWarning'
        }});
    }};
    
    // Capture unhandled errors
    window.addEventListener('error', function(event) {{
        sendError({{
            message: event.message,
            source: event.filename,
            line_number: event.lineno,
            column_number: event.colno,
            error_type: event.error ? event.error.constructor.name : 'Error',
            stack_trace: event.error ? event.error.stack : null,
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString()
        }});
    }});
    
    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {{
        sendError({{
            message: event.reason ? event.reason.toString() : 'Unhandled Promise Rejection',
            source: 'promise',
            error_type: 'UnhandledPromiseRejection',
            stack_trace: event.reason && event.reason.stack ? event.reason.stack : null,
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString()
        }});
    }});
    
    alert('Error Collector MCP activated for this page!');
}})();
"""
        return bookmarklet_js.replace('\n', '').replace('    ', '')
    
    def get_browser_extension_manifest(self) -> Dict[str, Any]:
        """Generate browser extension manifest."""
        return {
            "manifest_version": 3,
            "name": "Error Collector MCP",
            "version": "1.0",
            "description": "Collect JavaScript errors for AI analysis",
            "permissions": ["activeTab", "storage"],
            "host_permissions": ["<all_urls>"],
            "content_scripts": [{
                "matches": ["<all_urls>"],
                "js": ["content.js"],
                "run_at": "document_start"
            }],
            "background": {
                "service_worker": "background.js"
            },
            "action": {
                "default_popup": "popup.html",
                "default_title": "Error Collector MCP"
            }
        }
    
    def get_extension_content_script(self) -> str:
        """Generate content script for browser extension."""
        return f"""
// Error Collector MCP Content Script
(function() {{
    'use strict';
    
    const SERVER_URL = 'http://localhost:{self._http_port}/collect';
    let errorCount = 0;
    
    function sendError(errorData) {{
        // Send to background script
        chrome.runtime.sendMessage({{
            type: 'ERROR_COLLECTED',
            data: errorData
        }});
        
        // Also try direct HTTP (if CORS allows)
        fetch(SERVER_URL, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(errorData),
            mode: 'cors'
        }}).catch(e => console.debug('Direct send failed:', e));
    }}
    
    function shouldIgnoreError(message, source) {{
        const ignoredPatterns = [
            /ResizeObserver loop limit exceeded/,
            /Non-Error promise rejection captured/,
            /Script error\\./,
            /Network request failed.*chrome-extension/
        ];
        
        const ignoredDomains = [
            'chrome-extension://',
            'moz-extension://',
            'safari-extension://'
        ];
        
        // Check patterns
        for (const pattern of ignoredPatterns) {{
            if (pattern.test(message)) return true;
        }}
        
        // Check domains
        for (const domain of ignoredDomains) {{
            if (source && source.includes(domain)) return true;
        }}
        
        return false;
    }}
    
    // Capture JavaScript errors
    window.addEventListener('error', function(event) {{
        if (shouldIgnoreError(event.message, event.filename)) return;
        
        errorCount++;
        sendError({{
            message: event.message,
            source: event.filename || 'unknown',
            line_number: event.lineno,
            column_number: event.colno,
            error_type: event.error ? event.error.constructor.name : 'Error',
            stack_trace: event.error ? event.error.stack : null,
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString(),
            error_id: `error_${{Date.now()}}_${{errorCount}}`
        }});
    }}, true);
    
    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {{
        const message = event.reason ? event.reason.toString() : 'Unhandled Promise Rejection';
        if (shouldIgnoreError(message, '')) return;
        
        errorCount++;
        sendError({{
            message: message,
            source: 'promise',
            error_type: 'UnhandledPromiseRejection',
            stack_trace: event.reason && event.reason.stack ? event.reason.stack : null,
            url: window.location.href,
            user_agent: navigator.userAgent,
            page_title: document.title,
            timestamp: new Date().toISOString(),
            error_id: `promise_${{Date.now()}}_${{errorCount}}`
        }});
    }});
    
    // Override console methods to capture console errors
    const originalError = console.error;
    const originalWarn = console.warn;
    
    console.error = function(...args) {{
        originalError.apply(console, args);
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        
        if (!shouldIgnoreError(message, '')) {{
            errorCount++;
            sendError({{
                message: message,
                source: 'console.error',
                error_type: 'ConsoleError',
                url: window.location.href,
                user_agent: navigator.userAgent,
                page_title: document.title,
                timestamp: new Date().toISOString(),
                error_id: `console_error_${{Date.now()}}_${{errorCount}}`
            }});
        }}
    }};
    
    console.warn = function(...args) {{
        originalWarn.apply(console, args);
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        
        if (!shouldIgnoreError(message, '')) {{
            errorCount++;
            sendError({{
                message: message,
                source: 'console.warn',
                error_type: 'ConsoleWarning',
                url: window.location.href,
                user_agent: navigator.userAgent,
                page_title: document.title,
                timestamp: new Date().toISOString(),
                error_id: `console_warn_${{Date.now()}}_${{errorCount}}`
            }});
        }}
    }};
    
    // Notify that error collection is active
    console.log('Error Collector MCP: Active on', window.location.href);
}})();
"""
    
    async def health_check(self) -> bool:
        """Check if the browser collector is healthy."""
        try:
            # Check if servers are running
            websocket_healthy = self._websocket_server is not None
            http_healthy = self._http_server is not None
            
            return websocket_healthy and http_healthy and self._is_collecting
        except Exception as e:
            logger.error(f"Browser collector health check failed: {e}")
            return False
    
    def _get_log_file(self) -> Path:
        """Get the log file path for browser errors."""
        temp_dir = Path(tempfile.gettempdir()) / "error-collector-mcp"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir / "browser_errors.log"
    
    async def _start_websocket_server(self) -> None:
        """Start WebSocket server for real-time error collection."""
        try:
            self._websocket_server = await websockets.serve(
                self._handle_websocket_connection,
                "localhost",
                self._websocket_port
            )
            logger.info(f"WebSocket server started on port {self._websocket_port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _start_http_server(self) -> None:
        """Start HTTP server for bookmarklet/extension communication."""
        try:
            self._http_app = web.Application()
            
            # Add CORS middleware
            self._http_app.middlewares.append(self._cors_middleware)
            
            # Add routes
            self._http_app.router.add_post('/collect', self._handle_http_error)
            self._http_app.router.add_get('/bookmarklet', self._serve_bookmarklet)
            self._http_app.router.add_get('/extension/manifest.json', self._serve_extension_manifest)
            self._http_app.router.add_get('/extension/content.js', self._serve_extension_content)
            self._http_app.router.add_get('/status', self._serve_status)
            
            runner = web.AppRunner(self._http_app)
            await runner.setup()
            
            site = web.TCPSite(runner, 'localhost', self._http_port)
            await site.start()
            
            self._http_server = runner
            logger.info(f"HTTP server started on port {self._http_port}")
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle WebSocket connections from browsers."""
        self._connected_clients.add(websocket)
        logger.debug(f"WebSocket client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    error_data = json.loads(message)
                    await self._process_browser_error_data(error_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.debug("WebSocket client disconnected")
        finally:
            self._connected_clients.discard(websocket)
    
    async def _handle_http_error(self, request):
        """Handle HTTP POST requests with error data."""
        try:
            error_data = await request.json()
            await self._process_browser_error_data(error_data)
            return web.json_response({"status": "success"})
        except Exception as e:
            logger.error(f"Error processing HTTP error data: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=400)
    
    async def _serve_bookmarklet(self, request):
        """Serve bookmarklet code."""
        bookmarklet = self.get_bookmarklet_code()
        return web.Response(
            text=f"javascript:{bookmarklet}",
            content_type="text/plain"
        )
    
    async def _serve_extension_manifest(self, request):
        """Serve browser extension manifest."""
        manifest = self.get_browser_extension_manifest()
        return web.json_response(manifest)
    
    async def _serve_extension_content(self, request):
        """Serve browser extension content script."""
        content_script = self.get_extension_content_script()
        return web.Response(
            text=content_script,
            content_type="application/javascript"
        )
    
    async def _serve_status(self, request):
        """Serve collector status."""
        status = {
            "collecting": self._is_collecting,
            "websocket_port": self._websocket_port,
            "http_port": self._http_port,
            "connected_clients": len(self._connected_clients),
            "errors_collected": len(self._collected_errors),
            "log_file": str(self._log_file)
        }
        return web.json_response(status)
    
    @web.middleware
    async def _cors_middleware(self, request, handler):
        """CORS middleware for HTTP server."""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
    
    async def _process_browser_error_data(self, error_data: Dict[str, Any]) -> None:
        """Process raw browser error data and create BrowserError."""
        try:
            # Convert to BrowserErrorData first
            browser_error_data = BrowserErrorData(
                message=error_data.get('message', ''),
                source=error_data.get('source', ''),
                line_number=error_data.get('line_number'),
                column_number=error_data.get('column_number'),
                error_type=error_data.get('error_type', 'Error'),
                stack_trace=error_data.get('stack_trace'),
                url=error_data.get('url', ''),
                user_agent=error_data.get('user_agent', ''),
                page_title=error_data.get('page_title', ''),
                timestamp=datetime.fromisoformat(error_data['timestamp'].replace('Z', '+00:00')) if error_data.get('timestamp') else datetime.utcnow(),
                additional_data=error_data.get('additional_data', {})
            )
            
            # Check if error should be ignored
            if self._should_ignore_error(browser_error_data):
                return
            
            # Create BrowserError
            browser_error = BrowserError(
                message=browser_error_data.message,
                url=browser_error_data.url,
                user_agent=browser_error_data.user_agent,
                page_title=browser_error_data.page_title,
                line_number=browser_error_data.line_number,
                column_number=browser_error_data.column_number,
                error_type=browser_error_data.error_type,
                stack_trace=browser_error_data.stack_trace,
                timestamp=browser_error_data.timestamp,
                severity=self._determine_error_severity(browser_error_data)
            )
            
            # Collect the error
            await self._collect_error(browser_error)
            
        except Exception as e:
            logger.error(f"Failed to process browser error data: {e}")
    
    def _should_ignore_error(self, error_data: BrowserErrorData) -> bool:
        """Check if error should be ignored based on patterns and domains."""
        import re
        
        # Check ignored patterns
        for pattern in self._ignored_patterns:
            if re.search(pattern, error_data.message, re.IGNORECASE):
                return True
        
        # Check ignored domains
        for domain in self._ignored_domains:
            if domain in error_data.url or domain in error_data.source:
                return True
        
        return False
    
    def _determine_error_severity(self, error_data: BrowserErrorData) -> ErrorSeverity:
        """Determine error severity based on error data."""
        message_lower = error_data.message.lower()
        error_type_lower = error_data.error_type.lower()
        
        # Critical errors
        if any(keyword in message_lower for keyword in [
            "out of memory", "stack overflow", "maximum call stack"
        ]):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(keyword in error_type_lower for keyword in [
            "error", "exception"
        ]) and error_type_lower not in ["consoleerror", "consolewarning"]:
            return ErrorSeverity.HIGH
        
        # Medium severity for console errors
        if "consoleerror" in error_type_lower:
            return ErrorSeverity.MEDIUM
        
        # Low severity for warnings
        if any(keyword in error_type_lower for keyword in [
            "warning", "consolewarning"
        ]):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    async def _collect_error(self, error: BrowserError) -> None:
        """Collect a browser error."""
        self._collected_errors.append(error)
        
        # Log to file
        self._log_error_to_file(error)
        
        # Notify callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        logger.debug(f"Collected browser error: {error.message[:100]}...")
    
    def _log_error_to_file(self, error: BrowserError) -> None:
        """Log error to file for persistence."""
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                json.dump(error.to_dict(), f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to log error to file: {e}")
    
    async def _monitor_log_file(self) -> None:
        """Monitor log file for externally added errors."""
        if not self._log_file.exists():
            self._log_file.touch()
        
        last_size = self._log_file.stat().st_size
        
        while self._is_collecting:
            try:
                current_size = self._log_file.stat().st_size
                
                if current_size > last_size:
                    # Read new content
                    with open(self._log_file, 'r', encoding='utf-8') as f:
                        f.seek(last_size)
                        new_content = f.read()
                    
                    # Process new log entries
                    for line in new_content.strip().split('\n'):
                        if line.strip():
                            try:
                                error_data = json.loads(line)
                                await self._process_browser_error_data(error_data)
                            except json.JSONDecodeError:
                                continue
                    
                    last_size = current_size
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error monitoring log file: {e}")
                await asyncio.sleep(5)