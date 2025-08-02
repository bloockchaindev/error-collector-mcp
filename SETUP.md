# Error Collector MCP - Setup Guide

This guide will help you set up Error Collector MCP quickly and securely.

## Quick Setup (2 minutes)

### 1. Install the Package

```bash
# Install from PyPI (when released)
pip install error-collector-mcp

# Or install from source
git clone https://github.com/error-collector-mcp/error-collector-mcp.git
cd error-collector-mcp
pip install -e .
```

### 2. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
nano .env
```

**Required**: Set your OpenRouter API key in `.env`:

```bash
OPENROUTER_API_KEY=your-api-key-here
```

**Get a free API key**: Visit [OpenRouter.ai](https://openrouter.ai/) and sign
up for a free account.

### 3. Start the Server

```bash
# Start the MCP server
error-collector-mcp serve

# Or using Python module
python -m error_collector_mcp.server
```

That's it! Your Error Collector MCP server is now running.

## Configuration Options

### Environment Variables (.env file)

The easiest way to configure Error Collector MCP is using a `.env` file:

```bash
# Required
OPENROUTER_API_KEY=your-api-key-here

# Optional customizations
ERROR_COLLECTOR_DATA_DIR=/custom/data/path
ERROR_COLLECTOR_SERVER__LOG_LEVEL=INFO
ERROR_COLLECTOR_SERVER__PORT=8000
```

### Configuration File (config.json)

For advanced configuration, you can customize `config.json`:

```json
{
    "openrouter": {
        "api_key": "${OPENROUTER_API_KEY}",
        "model": "qwen/qwen-2.5-coder-32b-instruct:free"
    },
    "collection": {
        "auto_summarize": true,
        "max_errors_per_minute": 100
    },
    "storage": {
        "retention_days": 30,
        "max_errors_stored": 10000
    }
}
```

## Integration with Kiro

Add to your Kiro MCP configuration (`.kiro/settings/mcp.json`):

```json
{
    "mcpServers": {
        "error-collector": {
            "command": "error-collector-mcp",
            "args": ["serve"],
            "env": {
                "OPENROUTER_API_KEY": "your-api-key-here"
            }
        }
    }
}
```

## Integration with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
    "mcpServers": {
        "error-collector": {
            "command": "error-collector-mcp",
            "args": ["serve"]
        }
    }
}
```

## Browser Integration (Optional)

To collect JavaScript errors from your browser:

```bash
# Build browser extension
error-collector-mcp build-browser-extension chrome --package

# Install the extension:
# 1. Go to chrome://extensions/
# 2. Enable Developer mode
# 3. Click "Load unpacked"
# 4. Select the browser-extensions/chrome directory
```

## Terminal Integration (Optional)

To collect terminal command errors:

```bash
# Install shell integration
error-collector-mcp install-shell-integration zsh

# Restart your terminal
source ~/.zshrc
```

## Verification

Test that everything is working:

```bash
# Check server status
curl http://localhost:8000/health

# Or use MCP tools (if integrated with Kiro/Claude)
# The server should respond with error collection and AI summarization capabilities
```

## Troubleshooting

### Common Issues

**1. "No auth credentials found" error**

- Make sure your `OPENROUTER_API_KEY` is set in `.env`
- Verify the API key is valid at [OpenRouter.ai](https://openrouter.ai/)

**2. "Configuration file not found"**

- Make sure you're running from the project directory
- Or specify config path:
  `error-collector-mcp serve --config /path/to/config.json`

**3. "Permission denied" errors**

- Check file permissions on data directory
- Make sure the user has write access to `~/.error-collector-mcp`

**4. Port already in use**

- Change the port: `ERROR_COLLECTOR_SERVER__PORT=8001` in `.env`
- Or kill the existing process: `lsof -ti:8000 | xargs kill`

### Getting Help

- **Documentation**: [README.md](README.md)
- **Issues**:
  [GitHub Issues](https://github.com/error-collector-mcp/error-collector-mcp/issues)
- **Discussions**:
  [GitHub Discussions](https://github.com/error-collector-mcp/error-collector-mcp/discussions)

## Security Notes

- **Never commit `.env` files** to version control
- **Use strong API keys** and rotate them regularly
- **Restrict network access** in production environments
- **Monitor API usage** to avoid unexpected costs

## Next Steps

Once set up, you can:

1. **Collect Errors**: Install browser/terminal integrations
2. **Monitor**: Use MCP tools to query errors and get AI analysis
3. **Customize**: Adjust configuration for your needs
4. **Deploy**: Use Docker or production deployment guides

---

**Need help?** Check our [troubleshooting guide](DEPLOYMENT.md#troubleshooting)
or
[open an issue](https://github.com/error-collector-mcp/error-collector-mcp/issues).
