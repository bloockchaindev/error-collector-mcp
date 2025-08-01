# 🚀 Error Collector MCP - Quick Start Guide

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Free%20API-orange.svg)](https://openrouter.ai/)

> **Get intelligent error collection and AI-powered debugging in any project in
> under 5 minutes.**

The Error Collector MCP automatically captures browser console errors and
terminal errors, then uses AI to provide intelligent summaries and debugging
suggestions through your favorite AI assistant (Kiro, Claude, etc.).

## 📋 Table of Contents

- [Quick Installation](#-quick-installation)
- [2-Minute Setup](#-2-minute-setup)
- [Enable Error Collection](#-enable-error-collection)
- [Using with Your AI Assistant](#-using-with-your-ai-assistant)
- [Project-Specific Configurations](#-project-specific-configurations)
- [Available Commands](#️-available-commands)
- [Troubleshooting](#-troubleshooting)
- [Examples](#-project-structure-examples)
- [Next Steps](#-next-steps)

## 📦 Quick Installation

### Option A: Install from PyPI (Recommended)

```bash
pip install error-collector-mcp
```

### Option B: Install from Source

```bash
git clone https://github.com/yourusername/error-collector-mcp.git
cd error-collector-mcp
pip install -e .
```

> **Prerequisites:** Python 3.8+ and a free
> [OpenRouter API key](https://openrouter.ai/)

## ⚡ 2-Minute Setup

### 1. Create Configuration

```bash
# Copy the minimal config template
cp config.minimal.json my-config.json
```

**Edit `my-config.json`:**

```json
{
  "openrouter": {
    "api_key": "your-openrouter-api-key-here"
  }
}
```

> 🔑 **Get your free OpenRouter API key:** https://openrouter.ai/

### 2. Start the MCP Server

```bash
error-collector-mcp serve --config my-config.json
```

### 3. Connect to Your AI Assistant

<details>
<summary><strong>🎯 Kiro (Automatic Setup - Recommended)</strong></summary>

```bash
python setup_kiro_integration.py
```

The setup script will automatically configure everything for you!

</details>

<details>
<summary><strong>🎯 Kiro (Manual Setup)</strong></summary>

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "error-collector": {
      "command": "error-collector-mcp",
      "args": ["serve", "--config", "/absolute/path/to/my-config.json"],
      "disabled": false,
      "autoApprove": [
        "query_errors",
        "get_error_summary",
        "get_error_statistics"
      ]
    }
  }
}
```

</details>

<details>
<summary><strong>🤖 Claude Desktop</strong></summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "error-collector": {
      "command": "error-collector-mcp",
      "args": ["serve", "--config", "/absolute/path/to/my-config.json"]
    }
  }
}
```

</details>

<details>
<summary><strong>🔧 Other MCP-Compatible Tools</strong></summary>

The Error Collector MCP follows the standard MCP protocol and works with any
MCP-compatible AI tool. Add the server configuration using your tool's MCP setup
method.

</details>

### 4. Test the Integration

Ask your AI assistant:

```
"Check the error collector status"
"Simulate a test error and show it to me"
```

✅ **You're ready!** The Error Collector MCP is now integrated with your AI
assistant.

## 🌐 Enable Error Collection

### 🌐 Browser Errors (Web Development)

<details>
<summary><strong>⚡ Quick Setup - Bookmarklet (1 minute)</strong></summary>

```bash
error-collector-mcp build-browser-extension bookmarklet
```

Copy the generated bookmarklet to your browser bookmarks and click it on any
page to start collecting errors.

</details>

<details>
<summary><strong>🔧 Full Setup - Browser Extension (5 minutes)</strong></summary>

```bash
# Build extensions for all browsers
error-collector-mcp build-browser-extension all --package
```

**Chrome Installation:**

1. Go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `browser-extensions/chrome/` folder

**Firefox Installation:**

1. Go to `about:debugging`
2. Click "This Firefox"
3. Click "Load Temporary Add-on"
4. Select any file in the `browser-extensions/firefox/` folder

</details>

### 💻 Terminal Errors (All Development)

```bash
# Install shell integration
error-collector-mcp install-shell-integration

# Restart terminal or run:
source ~/.bashrc  # or ~/.zshrc for zsh
```

> 💡 **Pro tip:** Terminal integration captures errors from npm, pip, cargo,
> make, and other build tools automatically.

## 💬 Using with Your AI Assistant

Once set up, try these natural language commands:

### 🔍 Error Monitoring

```
"What errors happened in the last hour?"
"Show me all JavaScript errors from my React app"
"Are there any critical errors I should know about?"
```

### 🧠 Error Analysis

```
"Analyze the recent TypeScript compilation errors"
"What's causing the 404 errors on my API?"
"Summarize the database connection issues"
```

### 🛠️ Debugging Help

```
"Help me fix the authentication errors"
"What's the root cause of these React rendering errors?"
"Suggest solutions for the npm install failures"
```

### 📊 Project Health

```
"What's my current error rate?"
"Show me error trends for this week"
"Are there any recurring error patterns?"
```

> 🎯 **The AI understands context** - it knows your project structure, recent
> changes, and can provide targeted solutions.

## ⚙️ Project-Specific Configurations

<details>
<summary><strong>🌐 Web Development Project</strong></summary>
```json
{
  "openrouter": {
    "api_key": "your-key"
  },
  "collection": {
    "enabled_sources": ["browser", "terminal"],
    "ignored_domains": [
      "localhost:3000",
      "localhost:8080"
    ],
    "ignored_error_patterns": [
      "ResizeObserver loop limit exceeded",
      "Script error\\."
    ]
  },
  "storage": {
    "data_directory": "./project-errors"
  }
}
```

</details>

<details>
<summary><strong>🟢 Node.js/Backend Project</strong></summary>
```json
{
  "openrouter": {
    "api_key": "your-key"
  },
  "collection": {
    "enabled_sources": ["terminal"],
    "ignored_error_patterns": [
      "DeprecationWarning",
      "ExperimentalWarning"
    ]
  }
}
```

</details>

<details>
<summary><strong>🐍 Python Project</strong></summary>
```json
{
  "openrouter": {
    "api_key": "your-key"
  },
  "collection": {
    "enabled_sources": ["terminal"],
    "ignored_error_patterns": [
      "UserWarning",
      "FutureWarning"
    ]
  }
}
```

</details>

## 🛠️ Command Reference

<details>
<summary><strong>Click to expand command reference</strong></summary>

### Server Management

```bash
# Start server
error-collector-mcp serve --config config.json

# Check server health
error-collector-mcp health-check

# View server status
error-collector-mcp status
```

### Error Management

```bash
# Query recent errors
error-collector-mcp query --time-range 1h --limit 10

# Simulate test errors
error-collector-mcp simulate-error browser 2
error-collector-mcp simulate-error terminal 1

# View error statistics
error-collector-mcp stats --report-type overview
```

### Configuration

```bash
# Validate configuration
error-collector-mcp validate --config config.json

# Show current configuration
error-collector-mcp config --show
```

</details>

## 🚨 Troubleshooting

<details>
<summary><strong>❌ Server Won't Start</strong></summary>
```bash
# Check configuration
error-collector-mcp validate --config your-config.json

# Run with debug logging

error-collector-mcp serve --config your-config.json --log-level DEBUG

````
</details>

<details>
<summary><strong>🔍 No Errors Being Collected</strong></summary>
```bash
# Check collector status
error-collector-mcp status

# Test with simulation
error-collector-mcp simulate-error browser 1

# Verify browser extension is installed and active
# Verify shell integration: echo $ERROR_COLLECTOR_ENABLED
````

</details>

<details>
<summary><strong>🤖 AI Summarization Not Working</strong></summary>
```bash
# Test OpenRouter connection
curl -H "Authorization: Bearer your-key" https://openrouter.ai/api/v1/models

# Check API key in config

error-collector-mcp config --show | grep api_key

```
</details>

<details>
<summary><strong>🔗 MCP Connection Issues</strong></summary>
1. Verify the command path in your AI tool's MCP config
2. Check that the server is running: `ps aux | grep error-collector-mcp`
3. Ensure no port conflicts (default: 8000)
4. Restart your AI assistant after config changes

</details>

## 📁 Project Structure Examples

<details>
<summary><strong>📂 Single Project Setup</strong></summary>
```

my-project/ ├── error-collector-config.json ├── src/ ├── package.json └──
.kiro/settings/mcp.json

```
</details>

<details>
<summary><strong>🏗️ Multi-Service Project Setup</strong></summary>
```

my-app/ ├── frontend/ │ └── frontend-errors.json ├── backend/ │ └──
backend-errors.json ├── shared/ │ └── shared-errors.json └──
.kiro/settings/mcp.json

```
</details>

## 🔗 Next Steps

1. **Customize Configuration**: Adjust error filtering and collection settings for your project
2. **Set Up Team Integration**: Share configurations and set up centralized error collection
3. **Explore Advanced Features**: Custom error patterns, multiple environments, CI/CD integration
4. **Read Full Documentation**: Check `README.md` and `KIRO_INTEGRATION.md` for detailed guides

## 📚 Additional Resources

| Resource | Description |
|----------|-------------|
| [📖 Full Documentation](README.md) | Complete feature documentation |
| [🎯 Kiro Integration Guide](KIRO_INTEGRATION.md) | Detailed Kiro setup guide |
| [⚙️ Configuration Reference](config.example.json) | All configuration options |
| [🔗 OpenRouter Free Models](https://openrouter.ai/models?pricing=free) | Available AI models |

## 🆘 Getting Help

| Issue | Solution |
|-------|----------|
| 📋 **Check Logs** | `~/.error-collector-mcp/server.log` |
| 🧪 **Test Manually** | `error-collector-mcp serve --config config.json` |
| 🤖 **Ask Your AI** | "Check error collector health and diagnose any issues" |
| 🐛 **Report Bugs** | [Create GitHub Issue](https://github.com/yourusername/error-collector-mcp/issues) |

## 🌟 What's Next?

After completing this quick start:

1. ⭐ **Star this repo** if you find it helpful
2. 🔄 **Share with your team** - error collection works better with more data
3. 🛠️ **Customize for your workflow** - adjust filters and patterns
4. 💡 **Contribute** - we welcome PRs and feature requests!

---

<div align="center">

**🎉 That's it! You now have intelligent error collection and AI-powered debugging.**

The Error Collector MCP will automatically capture, analyze, and help you solve errors as they occur in your development workflow.

[![GitHub stars](https://img.shields.io/github/stars/yourusername/error-collector-mcp?style=social)](https://github.com/yourusername/error-collector-mcp)
[![Follow on Twitter](https://img.shields.io/twitter/follow/yourusername?style=social)](https://twitter.com/yourusername)

</div>
```
