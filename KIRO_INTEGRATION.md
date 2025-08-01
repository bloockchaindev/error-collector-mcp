# Kiro Integration Guide

This guide shows you how to integrate the Error Collector MCP with Kiro for intelligent error analysis and debugging assistance.

## Quick Setup

### 1. Install Error Collector MCP

```bash
# Clone and install the Error Collector MCP
git clone <repository-url>
cd error-collector-mcp
pip install -e .
```

### 2. Create Configuration

```bash
# Create your configuration file
cp config.minimal.json config.json

# Edit config.json and add your OpenRouter API key
{
  "openrouter": {
    "api_key": "your-openrouter-api-key-here"
  }
}
```

Get your free OpenRouter API key from: https://openrouter.ai/

### 3. Configure Kiro MCP Integration

Add the Error Collector MCP to your Kiro MCP configuration:

**Option A: Using the workspace MCP config (`.kiro/settings/mcp.json`)**
```json
{
  "mcpServers": {
    "error-collector": {
      "command": "error-collector-mcp",
      "args": ["serve", "--config", "config.json"],
      "env": {
        "ERROR_COLLECTOR_CONFIG": "config.json"
      },
      "disabled": false,
      "autoApprove": [
        "query_errors",
        "get_error_summary", 
        "get_error_statistics",
        "get_server_status"
      ]
    }
  }
}
```

**Option B: Using the global MCP config (`~/.kiro/settings/mcp.json`)**
```json
{
  "mcpServers": {
    "error-collector": {
      "command": "error-collector-mcp",
      "args": ["serve"],
      "disabled": false,
      "autoApprove": ["query_errors", "get_error_summary", "get_error_statistics"]
    }
  }
}
```

### 4. Start Using with Kiro

Once configured, you can start asking Kiro about errors:

## Example Conversations with Kiro

### Basic Error Queries

**You:** "Show me all JavaScript errors from the last hour"

**Kiro will use:** `query_errors` tool with parameters:
```json
{
  "time_range": "1h",
  "sources": ["browser"],
  "categories": ["syntax", "runtime"]
}
```

**You:** "What terminal errors happened today?"

**Kiro will use:** `query_errors` tool with:
```json
{
  "time_range": "24h", 
  "sources": ["terminal"]
}
```

### AI-Powered Error Analysis

**You:** "Analyze the recent TypeError errors and give me solutions"

**Kiro will:**
1. Query errors with `query_errors`
2. Generate analysis with `get_error_summary`
3. Provide root cause analysis and actionable solutions

**You:** "Summarize all the npm install errors from this week"

**Kiro will:**
1. Find terminal errors related to npm
2. Generate comprehensive summary with solutions
3. Provide specific troubleshooting steps

### System Health and Monitoring

**You:** "How is the error collection system performing?"

**Kiro will use:** `get_server_status` and `get_error_statistics` to provide:
- System health status
- Error processing rates
- Collection statistics
- Component status

**You:** "Show me error trends for the past week"

**Kiro will use:** `get_error_statistics` with trend analysis to show:
- Error frequency patterns
- Peak error periods
- Error type distributions
- System stability trends

## Advanced Integration

### Browser Error Collection

1. **Install Browser Extension:**
```bash
# Build browser extensions
error-collector-mcp build-browser-extension all --package

# Install the generated extension in your browser
# Chrome: Load unpacked extension from browser-extensions/chrome/
# Firefox: Load temporary add-on from browser-extensions/firefox/
```

2. **Use Bookmarklet (Quick Setup):**
```bash
# Start the server
error-collector-mcp serve

# Visit http://localhost:8766/bookmarklet to get the bookmarklet code
# Create a bookmark with the JavaScript code
# Click the bookmark on any page to start collecting errors
```

### Terminal Error Collection

1. **Install Shell Integration:**
```bash
# Automatically detect and install for your shell
error-collector-mcp install-shell-integration

# Or specify your shell
error-collector-mcp install-shell-integration bash
error-collector-mcp install-shell-integration zsh
```

2. **Restart your terminal** or source your shell configuration

### Custom Configuration

Create a comprehensive configuration file:

```json
{
  "openrouter": {
    "api_key": "your-api-key",
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "max_tokens": 1000,
    "temperature": 0.7
  },
  "collection": {
    "enabled_sources": ["browser", "terminal"],
    "ignored_error_patterns": [
      "ResizeObserver loop limit exceeded",
      "Non-Error promise rejection captured"
    ],
    "ignored_domains": [
      "chrome-extension://",
      "localhost:3000"
    ],
    "auto_summarize": true,
    "max_errors_per_minute": 100
  },
  "storage": {
    "data_directory": "~/.error-collector-mcp",
    "max_errors_stored": 10000,
    "retention_days": 30
  },
  "server": {
    "host": "localhost",
    "port": 8000,
    "log_level": "INFO"
  }
}
```

## Available MCP Tools

When integrated with Kiro, these tools become available:

### 1. `query_errors`
Query and filter collected errors
- **Use case:** "Show me all high-severity errors from the last 6 hours"
- **Parameters:** time_range, sources, categories, severities, limit, group_similar

### 2. `get_error_summary`
Get AI-generated error analysis and solutions
- **Use case:** "Analyze these JavaScript errors and provide solutions"
- **Actions:** generate_new, get_existing, list_recent, get_for_error

### 3. `get_error_statistics`
Get comprehensive error analytics
- **Use case:** "Show me error trends and system health"
- **Reports:** overview, trends, patterns, health, detailed

### 4. `get_server_status`
Get real-time server status and health
- **Use case:** "Is the error collection system working properly?"

### 5. `simulate_error`
Generate test errors for demonstration
- **Use case:** "Create some sample errors to test the system"

### 6. `health_check`
Perform comprehensive system health check
- **Use case:** "Check if all components are healthy"

## Example Kiro Workflows

### Debugging a Production Issue

**You:** "I'm seeing errors on my website, help me debug"

**Kiro will:**
1. Query recent browser errors from your site
2. Analyze error patterns and frequency
3. Generate AI summary with root cause analysis
4. Provide specific solutions and debugging steps
5. Show related errors that might be connected

### Monitoring Development Environment

**You:** "Check my development environment for any issues"

**Kiro will:**
1. Get system health status
2. Show recent terminal errors from builds/tests
3. Analyze error trends over time
4. Provide recommendations for improvement
5. Alert about any concerning patterns

### Code Review Error Analysis

**You:** "Analyze errors from my recent code changes"

**Kiro will:**
1. Filter errors by recent time period
2. Group similar errors together
3. Generate summaries for each error group
4. Provide specific code fixes and improvements
5. Show impact assessment for each issue

## Troubleshooting

### Common Issues

1. **MCP Server Not Starting**
```bash
# Check configuration
error-collector-mcp serve --config config.json

# Check logs
tail -f ~/.error-collector-mcp/server.log
```

2. **No Errors Being Collected**
```bash
# Test error simulation
error-collector-mcp serve &
# In another terminal:
curl -X POST http://localhost:8766/collect -H "Content-Type: application/json" -d '{"message":"test error"}'
```

3. **OpenRouter API Issues**
- Verify your API key is correct
- Check you have credits/quota available
- Ensure network connectivity to OpenRouter

### Verification Steps

1. **Test MCP Connection:**
Ask Kiro: "Can you check the error collector status?"

2. **Test Error Collection:**
Ask Kiro: "Simulate a test error and show it to me"

3. **Test AI Analysis:**
Ask Kiro: "Analyze any recent errors and provide solutions"

## Best Practices

### For Development
- Enable auto-summarization for immediate feedback
- Use browser extension for comprehensive frontend error tracking
- Install shell integration for build/test error capture
- Set appropriate retention periods for your workflow

### For Production Monitoring
- Configure error filtering to reduce noise
- Set up appropriate retention policies
- Monitor system health regularly
- Use trend analysis to identify patterns

### For Team Collaboration
- Share configuration files in your repository
- Document common error patterns and solutions
- Use Kiro's error analysis for code reviews
- Set up alerts for critical error patterns

## Advanced Features

### Custom Error Patterns
Configure custom error patterns to ignore or prioritize:

```json
{
  "collection": {
    "ignored_error_patterns": [
      "your-custom-pattern-here"
    ]
  }
}
```

### Multiple Environments
Run separate instances for different environments:

```bash
# Development
ERROR_COLLECTOR_CONFIG=dev-config.json error-collector-mcp serve

# Staging  
ERROR_COLLECTOR_CONFIG=staging-config.json error-collector-mcp serve
```

### Integration with CI/CD
Include error collection in your build process:

```yaml
# GitHub Actions example
- name: Start Error Collector
  run: error-collector-mcp serve &
  
- name: Run Tests
  run: npm test
  
- name: Analyze Test Errors
  run: |
    # Use Kiro to analyze any test failures
    kiro "Analyze any test errors from the last 10 minutes"
```

## Getting Help

If you encounter issues:

1. Check the server logs: `~/.error-collector-mcp/server.log`
2. Verify MCP configuration in Kiro
3. Test individual components with the CLI tools
4. Ask Kiro to check system health: "Check error collector health"

The Error Collector MCP transforms how you debug and monitor errors by providing intelligent, AI-powered analysis directly through Kiro's natural language interface.