# Contributing to Error Collector MCP

Thank you for your interest in contributing to Error Collector MCP! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/error-collector-mcp.git
   cd error-collector-mcp
   ```
3. **Set up development environment**:
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

### Prerequisites
- Python 3.9+
- Git
- OpenRouter API key (for testing AI features)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/error-collector-mcp.git
cd error-collector-mcp

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Configuration for Development
```bash
# Copy example config
cp config.example.json config.dev.json

# Edit with your OpenRouter API key
# Set environment variable
export ERROR_COLLECTOR_CONFIG=config.dev.json
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=error_collector_mcp --cov-report=html

# Run specific test file
pytest tests/test_mcp_server.py

# Run tests with verbose output
pytest -v
```

### Test Structure
- `tests/` - All test files
- `tests/conftest.py` - Shared test fixtures
- `tests/test_*.py` - Individual test modules
- Use `pytest-asyncio` for async tests
- Mock external dependencies (OpenRouter API, file system)

### Writing Tests
```python
import pytest
from error_collector_mcp.services import ErrorManager

@pytest.mark.asyncio
async def test_error_registration():
    manager = ErrorManager()
    await manager.initialize()
    
    # Test your functionality
    result = await manager.register_error(test_error)
    assert result.success
    
    await manager.cleanup()
```

## 🎨 Code Style

We use automated code formatting and linting:

### Formatting
```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Run both
black . && isort .
```

### Linting
```bash
# Type checking with mypy
mypy error_collector_mcp/

# Pre-commit checks (runs automatically on commit)
pre-commit run --all-files
```

### Code Style Guidelines
- Follow PEP 8 (enforced by black)
- Use type hints for all functions
- Write docstrings for public functions and classes
- Keep functions focused and small
- Use descriptive variable names

## 📝 Commit Guidelines

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat(mcp): add error statistics tool"
git commit -m "fix(browser): handle undefined error objects"
git commit -m "docs: update installation instructions"
```

## 🔄 Pull Request Process

### Before Submitting
1. **Update tests** - Add tests for new functionality
2. **Update documentation** - Update README, docstrings, etc.
3. **Run full test suite** - Ensure all tests pass
4. **Check code style** - Run black, isort, mypy
5. **Test manually** - Verify your changes work end-to-end

### PR Template
When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process
1. **Automated checks** must pass (tests, linting)
2. **Code review** by maintainers
3. **Manual testing** if needed
4. **Approval** and merge

## 🏗️ Architecture Overview

### Core Components
```
error_collector_mcp/
├── collectors/          # Error collection from various sources
├── config/             # Configuration management
├── mcp_tools/          # MCP tool implementations
├── models/             # Data models and schemas
├── services/           # Business logic services
├── storage/            # Data persistence
├── main.py             # CLI entry point
├── mcp_server.py       # MCP server implementation
└── server.py           # FastMCP server
```

### Key Design Principles
- **Async-first**: All I/O operations are asynchronous
- **Modular**: Components are loosely coupled
- **Testable**: Easy to mock and test individual components
- **Configurable**: Behavior controlled through configuration
- **Extensible**: Easy to add new collectors and tools

## 🐛 Bug Reports

### Before Reporting
1. **Search existing issues** - Check if already reported
2. **Try latest version** - Update to latest release
3. **Minimal reproduction** - Create smallest example that shows the bug

### Bug Report Template
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.0]
- Error Collector MCP: [e.g., 0.1.0]
- AI Assistant: [e.g., Kiro, Claude Desktop]

## Additional Context
Logs, screenshots, configuration files, etc.
```

## 💡 Feature Requests

### Before Requesting
1. **Check existing issues** - May already be planned
2. **Consider scope** - Should fit project goals
3. **Think about implementation** - How would it work?

### Feature Request Template
```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other ways to solve the problem

## Additional Context
Examples, mockups, related issues, etc.
```

## 🏷️ Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or improvement
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `question` - Further information requested
- `wontfix` - This will not be worked on

## 🎯 Areas for Contribution

### High Priority
- **Error Pattern Recognition** - Improve AI error categorization
- **Performance Optimization** - Reduce memory usage and improve speed
- **Browser Extension** - Enhance browser error collection
- **Documentation** - Improve guides and examples

### Medium Priority
- **Additional Collectors** - Support for more error sources
- **Configuration UI** - Web interface for configuration
- **Metrics Dashboard** - Visual error analytics
- **CI/CD Integration** - GitHub Actions, GitLab CI support

### Good First Issues
- **Test Coverage** - Add tests for existing functionality
- **Error Messages** - Improve error message clarity
- **Code Cleanup** - Refactor and simplify code
- **Documentation** - Fix typos, add examples

## 📚 Resources

### Documentation
- [README.md](README.md) - Main project documentation
- [QUICK_START.md](QUICK_START.md) - Quick start guide
- [KIRO_INTEGRATION.md](KIRO_INTEGRATION.md) - Kiro integration guide

### External Resources
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [OpenRouter](https://openrouter.ai/) - AI API service
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

## 🤝 Community

### Getting Help
- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and general discussion
- **Code Review** - Learn from PR reviews

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow GitHub's community guidelines

## 🎉 Recognition

Contributors are recognized in:
- **README.md** - Contributors section
- **Release Notes** - Feature attribution
- **GitHub** - Contributor graphs and statistics

Thank you for contributing to Error Collector MCP! 🚀