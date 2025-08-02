# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| 0.x.x   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security
vulnerability in Error Collector MCP, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: Send details to security@error-collector-mcp.org
2. **GitHub Security Advisory**: Use GitHub's private vulnerability reporting
   feature
3. **Encrypted Communication**: Use our PGP key for sensitive reports

### What to Include

When reporting a vulnerability, please include:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if available)
- Your contact information

### Response Timeline

- **Initial Response**: Within 24 hours
- **Vulnerability Assessment**: Within 72 hours
- **Fix Development**: Within 7-14 days (depending on severity)
- **Public Disclosure**: After fix is released and users have time to update

## Security Best Practices

### For Users

1. **API Key Security**:
   - Never commit API keys to version control
   - Use environment variables or secure secret management
   - Rotate API keys regularly
   - Use least-privilege API keys when possible

2. **Network Security**:
   - Run the server behind a firewall
   - Use HTTPS in production environments
   - Limit network access to necessary ports only
   - Consider using VPN for remote access

3. **Data Protection**:
   - Regularly backup error data
   - Implement data retention policies
   - Consider data encryption at rest
   - Monitor access logs

4. **System Security**:
   - Keep dependencies updated
   - Run with minimal required privileges
   - Use container security best practices
   - Monitor system resources

### For Developers

1. **Code Security**:
   - Follow secure coding practices
   - Validate all inputs
   - Sanitize error messages before AI processing
   - Use parameterized queries for data access

2. **Dependency Management**:
   - Regularly audit dependencies for vulnerabilities
   - Use dependency scanning tools
   - Pin dependency versions in production
   - Monitor security advisories

3. **Testing**:
   - Include security tests in CI/CD
   - Test with malformed inputs
   - Validate error handling paths
   - Test rate limiting and resource exhaustion

## Known Security Considerations

### Data Sensitivity

- Error messages may contain sensitive information
- Stack traces can reveal internal system details
- File paths may expose system structure
- Environment variables might contain secrets

**Mitigation**: The system includes built-in filtering to remove common
sensitive patterns, but users should review their error patterns and configure
additional filtering as needed.

### API Key Exposure

- OpenRouter API keys provide access to AI services
- Exposed keys can lead to unauthorized usage and costs
- Keys in logs or error messages create security risks

**Mitigation**: Use environment variables, never log API keys, and implement
proper secret management practices.

### Network Exposure

- MCP server listens on network ports
- Browser extensions communicate over HTTP/WebSocket
- Unprotected endpoints can be accessed by malicious actors

**Mitigation**: Use proper firewall configuration, consider HTTPS/WSS in
production, and implement authentication if needed.

## Security Updates

Security updates are released as patch versions and are clearly marked in the
changelog. Users are strongly encouraged to:

1. Subscribe to security notifications
2. Update promptly when security patches are released
3. Test updates in staging environments first
4. Monitor security advisories

## Compliance

This project aims to comply with:

- **OWASP Top 10** security practices
- **CWE/SANS Top 25** vulnerability prevention
- **NIST Cybersecurity Framework** guidelines
- **ISO 27001** security management principles

## Security Tools

We use the following tools to maintain security:

- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **CodeQL**: Semantic code analysis
- **Dependabot**: Automated dependency updates
- **SAST**: Static Application Security Testing

## Contact

For security-related questions or concerns:

- **Security Team**: security@error-collector-mcp.org
- **General Contact**: maintainers@error-collector-mcp.org
- **GitHub**: Use private vulnerability reporting

## Acknowledgments

We appreciate the security research community and will acknowledge researchers
who responsibly disclose vulnerabilities (with their permission).

---

**Last Updated**: February 2025 **Next Review**: May 2025
