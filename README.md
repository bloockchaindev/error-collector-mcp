# Error Collector MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/error-collector-mcp.svg)](https://badge.fury.io/py/error-collector-mcp)
[![CI](https://github.com/yourusername/error-collector-mcp/workflows/CI/badge.svg)](https://github.com/yourusername/error-collector-mcp/actions)
[![codecov](https://codecov.io/gh/yourusername/error-collector-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/error-collector-mcp)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Free%20API-orange.svg)](https://openrouter.ai/)

An open-source Model Context Protocol (MCP) server that intelligently collects
errors from browser console and terminal, then uses OpenRouter's free models to
generate summaries for AI agents like Kiro.

## Features

- **Browser Console Error Collection**: Captures JavaScript errors, console
  errors, and unhandled promise rejections
- **Terminal Error Monitoring**: Monitors command failures and compilation
  errors
- **AI-Powered Summarization**: Uses OpenRouter's free models to generate
  intelligent error summaries
- **MCP Integration**: Exposes error data through standard MCP tools for AI
  agents
- **Local & Private**: Runs entirely on your local machine with configurable
  privacy settings
- **Open Source**: MIT licensed and fully customizable

## 🚀 Quick Start

### Option 1: Interactive Setup Script (Recommended)

```bash
# Run the interactive setup script
./setup.sh

# Or on Windows
setup.bat

# Or directly with Python
python3 setup.py
```

The setup script will:

- ✅ Check system requirements
- ✅ Install the package
- ✅ Configure environment variables
- ✅ Set up integrations (Kiro, browser, terminal)
- ✅ Test the installation
- ✅ Start the server

### Option 2: Manual Setup

```bash
# 1. Install
pip install error-collector-mcp

# 2. Configure
cp .env.example .env
# Add your OpenRouter API key to .env

# 3. Run
error-collector-mcp serve
```

📖 **Detailed Setup**: See [SETUP.md](SETUP.md) for complete installation and
configuration instructions.

4. **Install shell integration** (optional):
   ```bash
   # Automatically detect and install for your shell
   error-collector-mcp install-shell-integration

   # Or specify a shell
   error-collector-mcp install-shell-integration bash
   ```

5. **Configure in Kiro**: Add to your MCP configuration:
   ```json
   {
     "mcpServers": {
       "error-collector": {
         "command": "error-collector-mcp",
         "args": ["--config", "config.json"]
       }
     }
   }
   ```

## Development

This project is currently under development. See the implementation tasks in
`.kiro/specs/error-collector-mcp/tasks.md` for current progress.

### Quick Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/error-collector-mcp.git
cd error-collector-mcp

# Run the automated setup script
python setup_repository.py --dev --api-key your-openrouter-key

# Or set up manually:
pip install -e ".[dev]"
pre-commit install
```

### Development Commands

```bash
# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy .

# Run all quality checks
pre-commit run --all-files

# Build package
python -m build
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t error-collector-mcp .
docker run -p 8000:8000 -v $(pwd)/config.json:/app/config.json error-collector-mcp
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for
guidelines.

### Quick Contribution Setup

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/yourusername/error-collector-mcp.git
cd error-collector-mcp

# Set up development environment
python setup_repository.py --dev

# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes and commit
git commit -m "feat: add your feature"

# Push and create a pull request
git push origin feature/your-feature-name
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Configuration

### Environment Variables

You can override configuration values using environment variables:

```bash
# OpenRouter API key
export ERROR_COLLECTOR_OPENROUTER__API_KEY="your-api-key"

# Log level
export ERROR_COLLECTOR_SERVER__LOG_LEVEL="DEBUG"

# Data directory
export ERROR_COLLECTOR_STORAGE__DATA_DIRECTORY="/custom/path"
```

### Configuration Validation

The server validates your configuration on startup and provides helpful error
messages and suggestions for common issues.

### Error Filtering

Configure which errors to ignore:

```json
{
  "collection": {
    "ignored_error_patterns": [
      "ResizeObserver loop limit exceeded",
      "Script error\\."
    ],
    "ignored_domains": [
      "chrome-extension://",
      "localhost:3000"
    ]
  }
}
```

## Termi

nal Error Collection

The terminal collector can monitor command execution and capture errors in
several ways:

### Automatic Shell Integration

Install shell hooks to automatically capture command failures:

```bash
# Install for your current shell
error-collector-mcp install-shell-integration

# Install for specific shell
error-collector-mcp install-shell-integration bash
error-collector-mcp install-shell-integration zsh
error-collector-mcp install-shell-integration fish
```

### Manual Command Execution

Use the collector programmatically to execute and monitor commands:

```python
from error_collector_mcp.collectors import TerminalCollector

collector = TerminalCollector()
await collector.start_collection()

# Execute a command and capture any errors
result = await collector.execute_command("npm install")
if result.exit_code != 0:
    print(f"Command failed: {result.stderr}")

# Get collected errors
errors = await collector.get_collected_errors()
```

### Log File Monitoring

Monitor existing log files for error patterns:

```python
# Monitor a log file for errors
await collector.monitor_command_file("/path/to/build.log")
```

### Error Patterns

The terminal collector recognizes common error patterns from:

- **Compilation errors**: GCC, Clang, TypeScript, etc.
- **Package management**: npm, pip, cargo, apt, brew
- **Network issues**: Connection failures, timeouts, DNS errors
- **Permission errors**: Access denied, insufficient privileges
- **Resource errors**: Out of memory, disk space, quotas
- **Git operations**: Authentication, merge conflicts, network issues## Browser
  Error Collection

The browser collector can capture JavaScript errors, console errors, and
unhandled promise rejections using multiple methods:

### Browser Extension (Recommended)

Build and install browser extensions for automatic error collection:

```bash
# Build extensions for all browsers
error-collector-mcp build-browser-extension all --package

# Build for specific browser
error-collector-mcp build-browser-extension chrome --package
error-collector-mcp build-browser-extension firefox --package
```

**Installation:**

- **Chrome**: Go to `chrome://extensions/`, enable Developer mode, click "Load
  unpacked"
- **Firefox**: Go to `about:debugging`, click "This Firefox", click "Load
  Temporary Add-on"

### Bookmarklet

For quick testing or one-time use, you can use a bookmarklet:

1. Start the error collector server
2. Visit `http://localhost:8766/bookmarklet` to get the bookmarklet code
3. Create a bookmark with the JavaScript code as the URL
4. Click the bookmark on any page to activate error collection

### Manual Integration

For custom applications, integrate error collection directly:

```javascript
// Send errors to the collector
fetch("http://localhost:8766/collect", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "Error message",
    source: "script.js",
    line_number: 42,
    error_type: "TypeError",
    url: window.location.href,
    timestamp: new Date().toISOString(),
  }),
});
```

### WebSocket Connection

For real-time error streaming:

```javascript
const ws = new WebSocket("ws://localhost:8765");
ws.onopen = function () {
  // Send error data as JSON
  ws.send(JSON.stringify(errorData));
};
```

### Error Types Captured

- **JavaScript Errors**: Syntax errors, reference errors, type errors
- **Console Errors**: console.error() and console.warn() calls
- **Unhandled Promise Rejections**: Async errors that aren't caught
- **Network Errors**: Failed fetch requests and resource loading
- **Custom Errors**: Application-specific error reporting

### Error Filtering

The browser collector automatically filters out common noise:

- Browser extension errors
- ResizeObserver loop warnings
- Script error messages from cross-origin scripts
- Development server hot-reload errors#

# AI-Powered Error Summarization

The Error Collector MCP uses OpenRouter's free AI models to generate intelligent
summaries of collected errors, making it easier for AI agents like Kiro to
understand and solve problems.

### Features

- **Intelligent Error Analysis**: AI identifies root causes and provides
  actionable solutions
- **Error Grouping**: Similar errors are automatically grouped for batch
  analysis
- **Context-Aware Prompts**: Specialized prompts for different error types
  (browser, terminal, etc.)
- **Rate Limiting**: Built-in rate limiting with exponential backoff to respect
  API limits
- **Confidence Scoring**: AI provides confidence scores for its analysis
- **Solution Enhancement**: Additional solution suggestions beyond the initial
  analysis

### Supported Models

The system uses OpenRouter's free tier models by default:

- `meta-llama/llama-3.1-8b-instruct:free` (default)
- Other free models available through OpenRouter

### Configuration

Configure AI summarization in your `config.json`:

```json
{
  "openrouter": {
    "api_key": "your-openrouter-api-key",
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "max_tokens": 1000,
    "temperature": 0.7,
    "timeout": 30,
    "max_retries": 3
  }
}
```

### Error Analysis Types

The AI provides different types of analysis based on error characteristics:

#### Browser Errors

- JavaScript syntax and runtime errors
- Browser compatibility issues
- Modern JavaScript solutions
- Debugging tool recommendations

#### Terminal Errors

- Command-line tool failures
- Permission and dependency issues
- Exit code interpretation
- System diagnostic steps

#### Multi-Error Analysis

- Pattern recognition across related errors
- Cascading failure analysis
- Root cause identification
- Systematic solution approaches

### API Usage

```python
from error_collector_mcp.services import AISummarizer
from error_collector_mcp.config import OpenRouterConfig

# Initialize summarizer
config = OpenRouterConfig(api_key="your-key")
summarizer = AISummarizer(config)

await summarizer.start()

# Summarize a single error
summary = await summarizer.summarize_error(error)

# Summarize multiple related errors
summary = await summarizer.summarize_error_group(errors)

# Get additional solutions
extra_solutions = await summarizer.get_solution_suggestions(summary)

await summarizer.stop()
```

### Privacy and Security

- Only error messages and relevant context are sent to OpenRouter
- No sensitive data (API keys, passwords, personal info) is included
- All processing respects rate limits and API terms of service
- Local fallback available when API is unavailable## Error Management and
  Coordination

The Error Manager serves as the central coordinator for all error collection,
processing, and AI summarization activities.

### Key Features

- **Centralized Error Processing**: Single point for all error registration and
  management
- **Collector Management**: Register and manage multiple error collectors
  (browser, terminal)
- **Automatic Summarization**: Intelligent grouping and auto-summarization of
  related errors
- **Background Processing**: Asynchronous processing queues for high-performance
  operation
- **Health Monitoring**: Comprehensive health checks for all components
- **Statistics Collection**: Detailed metrics and analytics

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Collectors    │───▶│  Error Manager   │───▶│  AI Summarizer  │
│ (Browser/Term)  │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │     Storage      │
                       │ (Errors/Summary) │
                       └──────────────────┘
```

### Usage Example

```python
from error_collector_mcp.services import ErrorCollectorMCPService

# Initialize complete service
service = ErrorCollectorMCPService("config.json")

await service.initialize()
await service.start()

# Service automatically:
# - Collects errors from registered sources
# - Groups similar errors
# - Generates AI summaries
# - Provides health monitoring

# Get service status
status = await service.get_service_status()
print(f"Errors processed: {status['statistics']['manager']['total_errors_processed']}")

await service.stop()
```

### Error Processing Flow

1. **Collection**: Errors captured by collectors (browser extension, terminal
   wrapper)
2. **Registration**: Errors registered with Error Manager
3. **Filtering**: Unwanted errors filtered based on configuration
4. **Storage**: Errors stored in persistent storage with deduplication
5. **Grouping**: Similar errors grouped for batch processing
6. **Summarization**: AI generates intelligent summaries
7. **Availability**: Summaries available through MCP tools for Kiro

### Auto-Summarization

The system automatically generates summaries when:

- **Threshold reached**: Multiple similar errors (configurable, default: 5)
- **Time-based**: Periodic summarization of pending errors (default: 5 minutes)
- **Manual request**: Explicit summary requests through API

### Statistics and Monitoring

Track comprehensive metrics:

- Total errors processed by source type
- Summaries generated (manual vs automatic)
- Collector health and activity status
- Processing queue status and performance
- Storage utilization and cleanup statistics

### Health Checks

Regular health monitoring of:

- **Storage Systems**: Error and summary stores
- **Collectors**: Browser and terminal collectors
- **AI Service**: OpenRouter API connectivity
- **Processing Queues**: Background task status## MCP Tools for Kiro Integration

The Error Collector MCP provides three main tools that Kiro can use to query
errors, get AI summaries, and analyze statistics.

### Available Tools

#### 1. Query Errors (`query_errors`)

Query and filter collected errors with various criteria:

```json
{
  "time_range": "24h",
  "sources": ["browser", "terminal"],
  "categories": ["runtime", "syntax"],
  "severities": ["high", "critical"],
  "limit": 20,
  "group_similar": true
}
```

**Features:**

- Time-based filtering (1h, 6h, 24h, 7d, 30d, all)
- Source filtering (browser, terminal, unknown)
- Category filtering (syntax, runtime, network, permission, resource, logic)
- Severity filtering (low, medium, high, critical)
- Pagination support
- Error grouping for similar issues
- Rich context inclusion

#### 2. Error Summary (`get_error_summary`)

Get AI-generated summaries and analysis of errors:

```json
{
  "action": "generate_new",
  "error_ids": ["error-id-1", "error-id-2"],
  "enhance_solutions": true
}
```

**Actions:**

- `get_existing`: Retrieve existing summary by ID
- `generate_new`: Create new AI summary for specified errors
- `get_for_error`: Get all summaries containing specific error
- `list_recent`: List recent summaries with filtering

**Features:**

- Root cause analysis
- Impact assessment
- Actionable solution suggestions
- Confidence scoring
- Solution enhancement with additional AI suggestions

#### 3. Error Statistics (`get_error_statistics`)

Get comprehensive statistics and analytics:

```json
{
  "report_type": "overview",
  "time_range": "24h",
  "include_recommendations": true
}
```

**Report Types:**

- `overview`: High-level statistics and breakdowns
- `trends`: Time-series analysis and trend detection
- `patterns`: Error pattern recognition and correlations
- `health`: System health and performance metrics
- `detailed`: Comprehensive report combining all types

### Running the MCP Server

Start the MCP server for Kiro integration:

```bash
# Run with default configuration
error-collector-mcp serve

# Run with custom config and data directory
error-collector-mcp serve --config custom-config.json --data-dir /path/to/data
```

### Kiro Configuration

Add to your Kiro MCP configuration:

```json
{
  "mcpServers": {
    "error-collector": {
      "command": "error-collector-mcp",
      "args": ["serve", "--config", "config.json"]
    }
  }
}
```

### Example Usage in Kiro

Once configured, you can use these tools in Kiro:

**Query recent errors:**

```
Show me all high-severity browser errors from the last 6 hours
```

**Get error analysis:**

```
Analyze and summarize the JavaScript errors from example.com
```

**Check system health:**

```
What's the current error rate and system health status?
```

**Identify patterns:**

```
Are there any recurring error patterns I should be concerned about?
```

### Tool Responses

All tools return structured JSON responses:

```json
{
  "success": true,
  "data": {
    // Tool-specific data
  }
}
```

Error responses include detailed error information:

```json
{
  "success": false,
  "error": {
    "type": "error_type",
    "message": "Error description",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Utility Tools

Additional utility tools for testing and monitoring:

- `get_server_status`: Get comprehensive server status
- `simulate_error`: Generate test errors for demonstration

### Performance Considerations

- Tools are optimized for real-time queries
- Large result sets are paginated automatically
- AI summarization respects rate limits
- Background processing doesn't block tool responses
- Comprehensive caching for frequently accessed data#

# Complete MCP Server Application

The Error Collector MCP provides a complete FastMCP server application with
comprehensive error collection, AI analysis, and health monitoring.

### Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastMCP Server                           │
├─────────────────────────────────────────────────────────────┤
│  MCP Tools: query_errors, get_error_summary,               │
│             get_error_statistics, health_check             │
├─────────────────────────────────────────────────────────────┤
│                 Error Manager Service                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Collectors  │  │   Storage   │  │   AI Summarizer     │  │
│  │ (Browser/   │  │ (Errors/    │  │   (OpenRouter)      │  │
│  │ Terminal)   │  │ Summaries)  │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Server Features

#### Core MCP Tools

- **query_errors**: Advanced error querying with filtering and pagination
- **get_error_summary**: AI-powered error analysis and solutions
- **get_error_statistics**: Comprehensive analytics and reporting
- **get_server_status**: Real-time server health and status
- **simulate_error**: Testing and demonstration utilities
- **health_check**: Detailed component health monitoring
- **cleanup_old_data**: Data retention and cleanup management

#### Health Monitoring

- **Component Health Checks**: Monitor all system components
- **Resource Monitoring**: Track CPU, memory, and disk usage
- **Health History**: Maintain health check history and trends
- **Status Levels**: Healthy, Warning, Critical, Unknown
- **Automatic Alerts**: Identify and report system issues

#### Server Management

- **Graceful Startup/Shutdown**: Proper initialization and cleanup
- **Signal Handling**: Respond to system signals appropriately
- **Configuration Management**: Environment-based configuration
- **Error Recovery**: Resilient operation with component failures
- **Background Processing**: Non-blocking error processing

### Running the Server

#### Command Line

```bash
# Start with default configuration
error-collector-mcp serve

# Start with custom configuration
error-collector-mcp serve --config custom-config.json --data-dir /path/to/data

# Set configuration via environment variables
export ERROR_COLLECTOR_CONFIG=config.json
export ERROR_COLLECTOR_DATA_DIR=/custom/data/path
error-collector-mcp serve
```

#### Direct Python Execution

```bash
# Run the FastMCP server directly
python -m error_collector_mcp.server

# Or with configuration
python -m error_collector_mcp.server config.json
```

### Health Monitoring

The server includes comprehensive health monitoring:

```python
from error_collector_mcp.health import HealthMonitor

# Create health monitor
monitor = HealthMonitor(error_manager)

# Perform health check
health = await monitor.perform_health_check()

# Check overall status
print(f"System Status: {health.overall_status}")

# Review individual checks
for check in health.checks:
    print(f"{check.name}: {check.status} - {check.message}")

# Get health trends
trends = monitor.get_health_trends()
print(f"System Stability: {trends['stability']}")
```

### Server Status API

Monitor server status through MCP tools:

```json
{
  "tool": "get_server_status",
  "arguments": {
    "include_details": true
  }
}
```

Response includes:

- Overall system health status
- Component-level health information
- Error processing statistics
- Collector status and activity
- Storage utilization metrics
- AI summarization performance

### Production Deployment

#### System Service (systemd)

```ini
[Unit]
Description=Error Collector MCP Server
After=network.target

[Service]
Type=simple
User=error-collector
WorkingDirectory=/opt/error-collector-mcp
Environment=ERROR_COLLECTOR_CONFIG=/etc/error-collector-mcp/config.json
Environment=ERROR_COLLECTOR_DATA_DIR=/var/lib/error-collector-mcp
ExecStart=/opt/error-collector-mcp/venv/bin/error-collector-mcp serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
ENV ERROR_COLLECTOR_CONFIG=config.json
ENV ERROR_COLLECTOR_DATA_DIR=/data

VOLUME ["/data"]
CMD ["error-collector-mcp", "serve"]
```

#### Process Management

```bash
# Start server in background
nohup error-collector-mcp serve > server.log 2>&1 &

# Monitor server logs
tail -f server.log

# Check server health
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "health_check", "arguments": {}}}'
```

### Performance Optimization

#### Configuration Tuning

```json
{
  "collection": {
    "max_errors_per_minute": 200,
    "auto_summarize": true,
    "group_similar_errors": true
  },
  "storage": {
    "max_errors_stored": 50000,
    "retention_days": 90
  },
  "server": {
    "max_concurrent_requests": 20
  }
}
```

#### Resource Management

- **Memory**: Configure max errors and summaries stored
- **CPU**: Adjust concurrent request limits
- **Disk**: Set appropriate retention policies
- **Network**: Configure rate limiting and timeouts

### Monitoring and Observability

#### Metrics Collection

- Error processing rates and volumes
- AI summarization performance and accuracy
- Storage utilization and growth trends
- Component health and availability
- Resource usage patterns

#### Logging

- Structured JSON logging for analysis
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Component-specific logging with context
- Performance metrics and timing information

#### Alerting Integration

- Health check failures trigger alerts
- Resource threshold violations
- Component unavailability notifications
- Performance degradation warnings

The complete MCP server provides enterprise-grade error collection and analysis
capabilities with comprehensive monitoring, health checks, and production-ready
deployment options.
