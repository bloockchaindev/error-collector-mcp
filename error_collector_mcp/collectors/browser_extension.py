"""Browser extension builder and utilities."""

import json
import zipfile
from pathlib import Path
from typing import Dict, Any
import tempfile


class BrowserExtensionBuilder:
    """Builder for browser extension files."""
    
    def __init__(self, collector_port: int = 8766):
        self.collector_port = collector_port
    
    def build_chrome_extension(self, output_dir: Path) -> Path:
        """Build Chrome extension files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create manifest.json
        manifest = self._get_manifest_v3()
        with open(output_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create content script
        with open(output_dir / "content.js", 'w') as f:
            f.write(self._get_content_script())
        
        # Create background script
        with open(output_dir / "background.js", 'w') as f:
            f.write(self._get_background_script())
        
        # Create popup HTML
        with open(output_dir / "popup.html", 'w') as f:
            f.write(self._get_popup_html())
        
        # Create popup script
        with open(output_dir / "popup.js", 'w') as f:
            f.write(self._get_popup_script())
        
        # Create icons directory and placeholder icon
        icons_dir = output_dir / "icons"
        icons_dir.mkdir(exist_ok=True)
        
        # Create a simple SVG icon
        icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="20" fill="#ff6b6b" stroke="#fff" stroke-width="2"/>
            <text x="24" y="30" text-anchor="middle" fill="white" font-family="Arial" font-size="16" font-weight="bold">!</text>
        </svg>'''
        
        with open(icons_dir / "icon.svg", 'w') as f:
            f.write(icon_svg)
        
        return output_dir
    
    def build_firefox_extension(self, output_dir: Path) -> Path:
        """Build Firefox extension files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create manifest.json (v2 for Firefox)
        manifest = self._get_manifest_v2()
        with open(output_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create content script (same as Chrome)
        with open(output_dir / "content.js", 'w') as f:
            f.write(self._get_content_script_firefox())
        
        # Create background script (v2 format)
        with open(output_dir / "background.js", 'w') as f:
            f.write(self._get_background_script_firefox())
        
        # Create popup files (same as Chrome)
        with open(output_dir / "popup.html", 'w') as f:
            f.write(self._get_popup_html())
        
        with open(output_dir / "popup.js", 'w') as f:
            f.write(self._get_popup_script_firefox())
        
        return output_dir
    
    def create_extension_package(self, extension_dir: Path, output_file: Path) -> Path:
        """Create a packaged extension file."""
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in extension_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extension_dir)
                    zf.write(file_path, arcname)
        
        return output_file
    
    def _get_manifest_v3(self) -> Dict[str, Any]:
        """Get Chrome extension manifest v3."""
        return {
            "manifest_version": 3,
            "name": "Error Collector MCP",
            "version": "1.0.0",
            "description": "Collect JavaScript errors for AI analysis with Kiro",
            "permissions": [
                "activeTab",
                "storage"
            ],
            "host_permissions": [
                "<all_urls>"
            ],
            "content_scripts": [{
                "matches": ["<all_urls>"],
                "js": ["content.js"],
                "run_at": "document_start",
                "all_frames": True
            }],
            "background": {
                "service_worker": "background.js"
            },
            "action": {
                "default_popup": "popup.html",
                "default_title": "Error Collector MCP",
                "default_icon": {
                    "16": "icons/icon.svg",
                    "32": "icons/icon.svg",
                    "48": "icons/icon.svg",
                    "128": "icons/icon.svg"
                }
            },
            "icons": {
                "16": "icons/icon.svg",
                "32": "icons/icon.svg",
                "48": "icons/icon.svg",
                "128": "icons/icon.svg"
            }
        }
    
    def _get_manifest_v2(self) -> Dict[str, Any]:
        """Get Firefox extension manifest v2."""
        return {
            "manifest_version": 2,
            "name": "Error Collector MCP",
            "version": "1.0.0",
            "description": "Collect JavaScript errors for AI analysis with Kiro",
            "permissions": [
                "activeTab",
                "storage",
                "<all_urls>"
            ],
            "content_scripts": [{
                "matches": ["<all_urls>"],
                "js": ["content.js"],
                "run_at": "document_start",
                "all_frames": True
            }],
            "background": {
                "scripts": ["background.js"],
                "persistent": False
            },
            "browser_action": {
                "default_popup": "popup.html",
                "default_title": "Error Collector MCP",
                "default_icon": {
                    "16": "icons/icon.svg",
                    "32": "icons/icon.svg",
                    "48": "icons/icon.svg",
                    "128": "icons/icon.svg"
                }
            },
            "icons": {
                "16": "icons/icon.svg",
                "32": "icons/icon.svg",
                "48": "icons/icon.svg",
                "128": "icons/icon.svg"
            }
        }
    
    def _get_content_script(self) -> str:
        """Get content script for Chrome."""
        return f'''
// Error Collector MCP - Chrome Content Script
(function() {{
    'use strict';
    
    const SERVER_URL = 'http://localhost:{self.collector_port}/collect';
    let errorCount = 0;
    let isEnabled = true;
    
    // Check if collection is enabled
    chrome.storage.sync.get(['errorCollectionEnabled'], function(result) {{
        isEnabled = result.errorCollectionEnabled !== false;
    }});
    
    // Listen for enable/disable messages
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {{
        if (request.type === 'TOGGLE_COLLECTION') {{
            isEnabled = request.enabled;
            sendResponse({{success: true}});
        }}
    }});
    
    function sendError(errorData) {{
        if (!isEnabled) return;
        
        // Add page context
        errorData.page_context = {{
            referrer: document.referrer,
            viewport: {{
                width: window.innerWidth,
                height: window.innerHeight
            }},
            scroll: {{
                x: window.scrollX,
                y: window.scrollY
            }}
        }};
        
        // Send to background script
        chrome.runtime.sendMessage({{
            type: 'ERROR_COLLECTED',
            data: errorData
        }});
        
        // Try direct HTTP send
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
            /Network request failed.*chrome-extension/,
            /Loading chunk \\d+ failed/,
            /ChunkLoadError/
        ];
        
        const ignoredDomains = [
            'chrome-extension://',
            'moz-extension://',
            'safari-extension://',
            'chrome-devtools://'
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
            error_id: `error_${{Date.now()}}_${{errorCount}}`,
            collection_method: 'extension'
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
            error_id: `promise_${{Date.now()}}_${{errorCount}}`,
            collection_method: 'extension'
        }});
    }});
    
    // Override console methods
    const originalError = console.error;
    const originalWarn = console.warn;
    
    console.error = function(...args) {{
        originalError.apply(console, args);
        if (!isEnabled) return;
        
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
                error_id: `console_error_${{Date.now()}}_${{errorCount}}`,
                collection_method: 'extension'
            }});
        }}
    }};
    
    console.warn = function(...args) {{
        originalWarn.apply(console, args);
        if (!isEnabled) return;
        
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
                error_id: `console_warn_${{Date.now()}}_${{errorCount}}`,
                collection_method: 'extension'
            }});
        }}
    }};
    
    // Notify that extension is active
    if (isEnabled) {{
        console.log('Error Collector MCP: Extension active on', window.location.href);
    }}
}})();
'''
    
    def _get_content_script_firefox(self) -> str:
        """Get content script for Firefox (similar to Chrome but with browser API)."""
        return self._get_content_script().replace('chrome.', 'browser.')
    
    def _get_background_script(self) -> str:
        """Get background script for Chrome."""
        return f'''
// Error Collector MCP - Chrome Background Script
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {{
    if (request.type === 'ERROR_COLLECTED') {{
        // Store error in local storage for popup display
        chrome.storage.local.get(['recentErrors'], function(result) {{
            const recentErrors = result.recentErrors || [];
            recentErrors.unshift({{
                ...request.data,
                tab_id: sender.tab.id,
                tab_url: sender.tab.url
            }});
            
            // Keep only last 100 errors
            if (recentErrors.length > 100) {{
                recentErrors.splice(100);
            }}
            
            chrome.storage.local.set({{recentErrors: recentErrors}});
        }});
        
        // Update badge with error count
        chrome.storage.local.get(['errorCount'], function(result) {{
            const errorCount = (result.errorCount || 0) + 1;
            chrome.storage.local.set({{errorCount: errorCount}});
            
            chrome.action.setBadgeText({{
                text: errorCount.toString(),
                tabId: sender.tab.id
            }});
            chrome.action.setBadgeBackgroundColor({{color: '#ff6b6b'}});
        }});
        
        sendResponse({{success: true}});
    }}
}});

// Clear badge when tab is updated
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {{
    if (changeInfo.status === 'loading') {{
        chrome.action.setBadgeText({{text: '', tabId: tabId}});
    }}
}});

// Handle extension installation
chrome.runtime.onInstalled.addListener(function(details) {{
    if (details.reason === 'install') {{
        chrome.storage.sync.set({{errorCollectionEnabled: true}});
        console.log('Error Collector MCP extension installed');
    }}
}});
'''
    
    def _get_background_script_firefox(self) -> str:
        """Get background script for Firefox."""
        return self._get_background_script().replace('chrome.', 'browser.')
    
    def _get_popup_html(self) -> str:
        """Get popup HTML."""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            width: 350px;
            min-height: 200px;
            margin: 0;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
        }
        
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .title {
            font-weight: 600;
            color: #333;
        }
        
        .toggle {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .switch {
            position: relative;
            width: 44px;
            height: 24px;
            background: #ccc;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .switch.active {
            background: #4CAF50;
        }
        
        .switch::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }
        
        .switch.active::after {
            transform: translateX(20px);
        }
        
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .stat {
            text-align: center;
            padding: 8px;
            background: #f5f5f5;
            border-radius: 4px;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: #ff6b6b;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
        
        .recent-errors {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .error-item {
            padding: 8px;
            margin-bottom: 8px;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .error-message {
            font-weight: 500;
            color: #d32f2f;
            margin-bottom: 4px;
        }
        
        .error-details {
            color: #666;
            font-size: 11px;
        }
        
        .no-errors {
            text-align: center;
            color: #666;
            padding: 20px;
        }
        
        .actions {
            margin-top: 16px;
            display: flex;
            gap: 8px;
        }
        
        .btn {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 12px;
        }
        
        .btn:hover {
            background: #f5f5f5;
        }
        
        .btn-primary {
            background: #2196F3;
            color: white;
            border-color: #2196F3;
        }
        
        .btn-primary:hover {
            background: #1976D2;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">Error Collector MCP</div>
        <div class="toggle">
            <span id="toggleLabel">Enabled</span>
            <div class="switch active" id="toggleSwitch"></div>
        </div>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="errorCount">0</div>
            <div class="stat-label">Errors Today</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="pageErrors">0</div>
            <div class="stat-label">This Page</div>
        </div>
    </div>
    
    <div class="recent-errors" id="recentErrors">
        <div class="no-errors">No errors collected yet</div>
    </div>
    
    <div class="actions">
        <button class="btn" id="clearBtn">Clear</button>
        <button class="btn btn-primary" id="exportBtn">Export</button>
    </div>
    
    <script src="popup.js"></script>
</body>
</html>'''
    
    def _get_popup_script(self) -> str:
        """Get popup JavaScript."""
        return '''
// Error Collector MCP - Popup Script
document.addEventListener('DOMContentLoaded', function() {
    const toggleSwitch = document.getElementById('toggleSwitch');
    const toggleLabel = document.getElementById('toggleLabel');
    const errorCountEl = document.getElementById('errorCount');
    const pageErrorsEl = document.getElementById('pageErrors');
    const recentErrorsEl = document.getElementById('recentErrors');
    const clearBtn = document.getElementById('clearBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    // Load current state
    chrome.storage.sync.get(['errorCollectionEnabled'], function(result) {
        const enabled = result.errorCollectionEnabled !== false;
        updateToggleState(enabled);
    });
    
    // Load error statistics
    loadErrorStats();
    
    // Toggle collection
    toggleSwitch.addEventListener('click', function() {
        const isActive = toggleSwitch.classList.contains('active');
        const newState = !isActive;
        
        chrome.storage.sync.set({errorCollectionEnabled: newState});
        updateToggleState(newState);
        
        // Notify content scripts
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            chrome.tabs.sendMessage(tabs[0].id, {
                type: 'TOGGLE_COLLECTION',
                enabled: newState
            });
        });
    });
    
    // Clear errors
    clearBtn.addEventListener('click', function() {
        chrome.storage.local.clear();
        loadErrorStats();
    });
    
    // Export errors
    exportBtn.addEventListener('click', function() {
        chrome.storage.local.get(['recentErrors'], function(result) {
            const errors = result.recentErrors || [];
            const dataStr = JSON.stringify(errors, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            
            const url = URL.createObjectURL(dataBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `error-collector-export-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        });
    });
    
    function updateToggleState(enabled) {
        if (enabled) {
            toggleSwitch.classList.add('active');
            toggleLabel.textContent = 'Enabled';
        } else {
            toggleSwitch.classList.remove('active');
            toggleLabel.textContent = 'Disabled';
        }
    }
    
    function loadErrorStats() {
        chrome.storage.local.get(['recentErrors', 'errorCount'], function(result) {
            const recentErrors = result.recentErrors || [];
            const errorCount = result.errorCount || 0;
            
            errorCountEl.textContent = errorCount;
            
            // Count errors for current page
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                const currentUrl = tabs[0].url;
                const pageErrors = recentErrors.filter(error => error.url === currentUrl);
                pageErrorsEl.textContent = pageErrors.length;
            });
            
            // Display recent errors
            displayRecentErrors(recentErrors.slice(0, 10));
        });
    }
    
    function displayRecentErrors(errors) {
        if (errors.length === 0) {
            recentErrorsEl.innerHTML = '<div class="no-errors">No errors collected yet</div>';
            return;
        }
        
        const errorHtml = errors.map(error => `
            <div class="error-item">
                <div class="error-message">${escapeHtml(error.message.substring(0, 100))}${error.message.length > 100 ? '...' : ''}</div>
                <div class="error-details">
                    ${error.error_type} • ${new URL(error.url).hostname} • ${new Date(error.timestamp).toLocaleTimeString()}
                </div>
            </div>
        `).join('');
        
        recentErrorsEl.innerHTML = errorHtml;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
'''
    
    def _get_popup_script_firefox(self) -> str:
        """Get popup script for Firefox."""
        return self._get_popup_script().replace('chrome.', 'browser.')


def main():
    """CLI entry point for browser extension builder."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Error Collector MCP Browser Extension Builder")
    parser.add_argument("command", choices=["build-chrome", "build-firefox", "build-all"])
    parser.add_argument("--output-dir", type=str, default="./browser-extensions", help="Output directory")
    parser.add_argument("--port", type=int, default=8766, help="Collector server port")
    parser.add_argument("--package", action="store_true", help="Create packaged extension files")
    
    args = parser.parse_args()
    
    builder = BrowserExtensionBuilder(args.port)
    output_dir = Path(args.output_dir)
    
    if args.command in ["build-chrome", "build-all"]:
        chrome_dir = builder.build_chrome_extension(output_dir / "chrome")
        print(f"Chrome extension built in: {chrome_dir}")
        
        if args.package:
            package_file = output_dir / "error-collector-mcp-chrome.zip"
            builder.create_extension_package(chrome_dir, package_file)
            print(f"Chrome extension packaged: {package_file}")
    
    if args.command in ["build-firefox", "build-all"]:
        firefox_dir = builder.build_firefox_extension(output_dir / "firefox")
        print(f"Firefox extension built in: {firefox_dir}")
        
        if args.package:
            package_file = output_dir / "error-collector-mcp-firefox.zip"
            builder.create_extension_package(firefox_dir, package_file)
            print(f"Firefox extension packaged: {package_file}")


if __name__ == "__main__":
    main()