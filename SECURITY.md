# Security Policy

## Supported Versions

We actively support the following versions of Error Collector MCP with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in Error Collector MCP, please report it responsibly.

### How to Report

1. **Do NOT create a public GitHub issue** for security vulnerabilities
2. **Email us directly** at: [security@yourdomain.com] (replace with actual email)
3. **Include the following information**:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Any suggested fixes (if you have them)

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt of your report within 48 hours
- **Initial Assessment**: We'll provide an initial assessment within 5 business days
- **Updates**: We'll keep you informed of our progress
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days
- **Credit**: We'll credit you in our security advisories (unless you prefer to remain anonymous)

### Security Best Practices

When using Error Collector MCP:

#### Configuration Security
- **Never commit API keys** to version control
- **Use environment variables** for sensitive configuration
- **Restrict file permissions** on configuration files (600 or 640)
- **Regularly rotate API keys**

#### Network Security
- **Use HTTPS** when possible for API communications
- **Configure firewalls** to restrict access to MCP server ports
- **Monitor network traffic** for unusual patterns

#### Data Privacy
- **Review error filtering** to prevent sensitive data collection
- **Configure data retention** policies appropriately
- **Understand data flow** to external services (OpenRouter)

#### Access Control
- **Limit MCP server access** to authorized AI assistants only
- **Use principle of least privilege** for file system access
- **Monitor server logs** for unauthorized access attempts

### Known Security Considerations

#### Data Handling
- Error messages may contain sensitive information
- Configure appropriate filtering to exclude sensitive data
- Be aware that error data is sent to OpenRouter for AI analysis

#### Network Communications
- MCP server listens on localhost by default
- Browser extension communicates with local server
- API calls to OpenRouter are made over HTTPS

#### File System Access
- Server requires read/write access to configured data directory
- Shell integration may execute commands with user privileges
- Browser extension has limited permissions within browser context

### Security Updates

Security updates will be:
- **Released promptly** for critical vulnerabilities
- **Documented** in CHANGELOG.md with security labels
- **Announced** through GitHub security advisories
- **Tagged** with appropriate version numbers

### Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1-2**: Acknowledgment sent
3. **Day 3-7**: Initial assessment and triage
4. **Day 8-30**: Development and testing of fix
5. **Day 30**: Public disclosure and release (may be extended for complex issues)

### Bug Bounty

We currently do not offer a formal bug bounty program, but we greatly appreciate security researchers who help improve our security posture.

### Contact

For security-related questions or concerns:
- **Security Email**: [security@yourdomain.com]
- **General Issues**: [GitHub Issues](https://github.com/yourusername/error-collector-mcp/issues)
- **General Questions**: [GitHub Discussions](https://github.com/yourusername/error-collector-mcp/discussions)

Thank you for helping keep Error Collector MCP secure!