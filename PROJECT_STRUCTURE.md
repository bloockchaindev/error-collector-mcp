# Project Structure

This document provides an overview of the Error Collector MCP project structure and organization.

## Repository Structure

```
error-collector-mcp/
├── .github/                    # GitHub-specific files
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── workflows/              # GitHub Actions workflows
│   │   ├── ci.yml             # Continuous Integration
│   │   └── release.yml        # Release automation
│   ├── FUNDING.yml            # Funding/sponsorship info
│   └── pull_request_template.md
├── .kiro/                     # Kiro-specific configuration
│   ├── settings/              # Kiro settings
│   └── specs/                 # Project specifications
├── .vscode/                   # VS Code configuration
├── error_collector_mcp/       # Main package directory
│   ├── collectors/            # Error collection modules
│   ├── config/               # Configuration management
│   ├── mcp_tools/            # MCP tool implementations
│   ├── models/               # Data models and schemas
│   ├── services/             # Business logic services
│   ├── storage/              # Data persistence layer
│   ├── __init__.py
│   ├── health.py             # Health monitoring
│   ├── main.py               # CLI entry point
│   ├── mcp_server.py         # MCP server implementation
│   └── server.py             # FastMCP server
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Shared test fixtures
│   └── test_*.py             # Individual test modules
├── .gitignore                # Git ignore rules
├── .pre-commit-config.yaml   # Pre-commit hooks
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
├── KIRO_INTEGRATION.md       # Kiro integration guide
├── LICENSE                   # MIT license
├── PROJECT_STRUCTURE.md      # This file
├── QUICK_START.md            # Quick start guide
├── README.md                 # Main documentation
├── SECURITY.md               # Security policy
├── config.example.json       # Example configuration
├── config.minimal.json       # Minimal configuration
├── pyproject.toml            # Python project configuration
└── setup_kiro_integration.py # Kiro setup script
```

## Package Structure

### Core Modules

#### `error_collector_mcp/`
Main package containing all source code.

#### `error_collector_mcp/collectors/`
Error collection implementations for different sources:
- `base_collector.py` - Abstract base collector
- `browser_collector.py` - Browser error collection
- `browser_extension.py` - Browser extension utilities
- `shell_wrapper.py` - Shell command wrapping
- `terminal_collector.py` - Terminal error monitoring

#### `error_collector_mcp/config/`
Configuration management:
- `config_schema.py` - Configuration data models
- `config_validator.py` - Configuration validation logic

#### `error_collector_mcp/mcp_tools/`
MCP tool implementations:
- `error_query_tool.py` - Error querying functionality
- `error_statistics_tool.py` - Statistics and analytics
- `error_summary_tool.py` - AI summarization tools

#### `error_collector_mcp/models/`
Data models and schemas:
- `base_error.py` - Base error model
- `browser_error.py` - Browser-specific error model
- `terminal_error.py` - Terminal-specific error model
- `error_summary.py` - AI summary model

#### `error_collector_mcp/services/`
Business logic services:
- `ai_summarizer.py` - AI-powered error analysis
- `config_service.py` - Configuration management service
- `error_manager.py` - Central error coordination
- `integration_example.py` - Integration examples
- `prompt_templates.py` - AI prompt templates

#### `error_collector_mcp/storage/`
Data persistence layer:
- `error_store.py` - Error data storage
- `summary_store.py` - Summary data storage

### Entry Points

#### `error_collector_mcp/main.py`
Command-line interface entry point providing:
- Server management commands
- Configuration validation
- Error querying utilities
- Integration setup tools

#### `error_collector_mcp/server.py`
FastMCP server implementation providing:
- MCP protocol handling
- Tool registration and execution
- Health monitoring endpoints
- Background processing coordination

#### `error_collector_mcp/mcp_server.py`
Core MCP server logic providing:
- Tool implementations
- Error processing workflows
- AI integration coordination
- Status and health reporting

## Configuration Files

### `pyproject.toml`
Python project configuration including:
- Package metadata and dependencies
- Build system configuration
- Tool configurations (black, isort, mypy, pytest)
- Entry point definitions

### `config.example.json`
Comprehensive configuration example showing:
- All available configuration options
- Detailed comments and explanations
- Production-ready settings
- Security best practices

### `config.minimal.json`
Minimal configuration for quick setup:
- Essential settings only
- Quick start compatibility
- Development-friendly defaults

## Development Files

### `.pre-commit-config.yaml`
Pre-commit hooks for code quality:
- Code formatting (black, isort)
- Linting (flake8, mypy)
- Security scanning (bandit)
- General checks (trailing whitespace, etc.)

### `.github/workflows/`
CI/CD automation:
- `ci.yml` - Continuous integration testing
- `release.yml` - Automated releases to PyPI

### `tests/`
Comprehensive test suite:
- Unit tests for all modules
- Integration tests for workflows
- Mock configurations for external services
- Async test support with pytest-asyncio

## Documentation Files

### User Documentation
- `README.md` - Main project documentation
- `QUICK_START.md` - Quick setup guide
- `KIRO_INTEGRATION.md` - Kiro-specific integration

### Developer Documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `PROJECT_STRUCTURE.md` - This file
- `SECURITY.md` - Security policy and practices

### Project Management
- `CHANGELOG.md` - Version history and changes
- `LICENSE` - MIT license text

## Build and Distribution

### Package Building
The project uses modern Python packaging with:
- `setuptools` as build backend
- `pyproject.toml` for configuration
- Automatic version management
- Entry point script generation

### Distribution
- PyPI package distribution
- GitHub releases with automated changelog
- Docker container support (planned)
- Multiple platform support (Windows, macOS, Linux)

## Development Workflow

### Local Development
1. Clone repository
2. Install in development mode: `pip install -e ".[dev]"`
3. Install pre-commit hooks: `pre-commit install`
4. Run tests: `pytest`
5. Format code: `black . && isort .`

### Testing Strategy
- Unit tests for individual components
- Integration tests for complete workflows
- Mock external dependencies (OpenRouter API)
- Async testing with proper fixtures
- Coverage reporting and analysis

### Release Process
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions automatically builds and publishes

## Architecture Principles

### Modularity
- Clear separation of concerns
- Pluggable collector architecture
- Independent service components
- Testable interfaces

### Async-First
- All I/O operations are asynchronous
- Non-blocking error processing
- Concurrent request handling
- Background task processing

### Configuration-Driven
- Behavior controlled through configuration
- Environment variable overrides
- Validation and error reporting
- Secure defaults

### Extensibility
- Plugin architecture for collectors
- Configurable AI prompts
- Custom error filtering
- Multiple storage backends (planned)

This structure supports maintainable, testable, and extensible code while providing a great developer experience.