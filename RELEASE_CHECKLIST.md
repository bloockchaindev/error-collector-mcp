# Release Checklist

This checklist ensures all steps are completed before releasing a new version of
Error Collector MCP.

## Pre-Release Checklist

### Code Quality

- [ ] All tests pass (`pytest`)
- [ ] Code coverage is above 80%
- [ ] Code is formatted (`black`, `isort`)
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`flake8`)
- [ ] Security scan passes (`bandit`, `safety`)
- [ ] No TODO/FIXME comments in production code

### Documentation

- [ ] README.md is updated with new features
- [ ] CHANGELOG.md includes all changes
- [ ] API documentation is current
- [ ] Configuration examples are valid
- [ ] Deployment guide is updated
- [ ] Security policy is current

### Configuration

- [ ] Version number updated in `pyproject.toml`
- [ ] Dependencies are pinned and up-to-date
- [ ] Configuration schema is valid
- [ ] Example configurations work
- [ ] Environment variable documentation is complete

### Testing

- [ ] Unit tests cover new functionality
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance testing completed
- [ ] Security testing completed
- [ ] Browser extension tested
- [ ] Shell integration tested

### Security

- [ ] No hardcoded secrets or API keys
- [ ] Security vulnerabilities addressed
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security policy updated if needed
- [ ] Sensitive data filtering tested

## Release Process

### 1. Version Preparation

- [ ] Create release branch (`release/v1.x.x`)
- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md with release notes
- [ ] Update README.md if needed
- [ ] Commit version changes

### 2. Testing

- [ ] Run full test suite locally
- [ ] Test installation from source
- [ ] Test Docker build
- [ ] Test CLI commands
- [ ] Test MCP integration
- [ ] Performance testing

### 3. Documentation

- [ ] Generate API documentation
- [ ] Update deployment guides
- [ ] Review all documentation for accuracy
- [ ] Test documentation examples

### 4. Build and Package

- [ ] Build Python package (`python -m build`)
- [ ] Test package installation (`pip install dist/*.whl`)
- [ ] Build Docker image
- [ ] Test Docker image
- [ ] Verify package metadata

### 5. Pre-Release Testing

- [ ] Deploy to staging environment
- [ ] Run integration tests in staging
- [ ] Performance testing in staging
- [ ] Security testing in staging
- [ ] User acceptance testing

## Release Execution

### 1. Create Release

- [ ] Merge release branch to main
- [ ] Create and push git tag (`git tag v1.x.x`)
- [ ] GitHub Actions CI/CD passes
- [ ] GitHub release created automatically
- [ ] Docker image published to registry

### 2. Package Distribution

- [ ] PyPI package published automatically
- [ ] Docker image available on GitHub Container Registry
- [ ] Release notes published
- [ ] Documentation updated on website

### 3. Verification

- [ ] PyPI package installs correctly
- [ ] Docker image runs correctly
- [ ] GitHub release has correct assets
- [ ] Documentation is accessible
- [ ] All download links work

## Post-Release Checklist

### 1. Monitoring

- [ ] Monitor PyPI download statistics
- [ ] Monitor Docker image pulls
- [ ] Check for installation issues
- [ ] Monitor error reports
- [ ] Review user feedback

### 2. Communication

- [ ] Announce release on GitHub
- [ ] Update project website
- [ ] Notify users of breaking changes
- [ ] Update integration documentation
- [ ] Social media announcement (if applicable)

### 3. Maintenance

- [ ] Monitor for critical issues
- [ ] Prepare hotfix process if needed
- [ ] Update development branch
- [ ] Plan next release cycle
- [ ] Update project roadmap

## Hotfix Process

If critical issues are discovered post-release:

### 1. Assessment

- [ ] Confirm issue severity
- [ ] Determine impact scope
- [ ] Decide if hotfix is needed
- [ ] Create hotfix branch from main

### 2. Fix Development

- [ ] Implement minimal fix
- [ ] Add regression tests
- [ ] Test fix thoroughly
- [ ] Update CHANGELOG.md

### 3. Hotfix Release

- [ ] Follow abbreviated release process
- [ ] Increment patch version
- [ ] Fast-track through CI/CD
- [ ] Communicate urgency to users

## Release Types

### Major Release (x.0.0)

- Breaking changes
- Major new features
- Architecture changes
- Full release process required

### Minor Release (1.x.0)

- New features
- Enhancements
- Non-breaking changes
- Standard release process

### Patch Release (1.1.x)

- Bug fixes
- Security fixes
- Documentation updates
- Abbreviated testing acceptable

## Quality Gates

Each release must pass these quality gates:

### Automated Gates

- [ ] All CI/CD checks pass
- [ ] Code coverage threshold met
- [ ] Security scans pass
- [ ] Performance benchmarks met
- [ ] Documentation builds successfully

### Manual Gates

- [ ] Code review completed
- [ ] Security review completed
- [ ] Documentation review completed
- [ ] Release notes approved
- [ ] Deployment guide tested

## Rollback Plan

If issues are discovered after release:

### 1. Immediate Actions

- [ ] Assess impact and severity
- [ ] Communicate with users
- [ ] Prepare rollback if necessary

### 2. Rollback Process

- [ ] Revert problematic changes
- [ ] Create emergency patch release
- [ ] Update documentation
- [ ] Communicate resolution

### 3. Post-Incident

- [ ] Conduct post-mortem
- [ ] Update release process
- [ ] Improve testing coverage
- [ ] Document lessons learned

## Tools and Resources

### Required Tools

- Python 3.9+ development environment
- Git with appropriate permissions
- Docker and Docker Compose
- Access to PyPI and GitHub Container Registry
- Documentation build tools

### Access Requirements

- GitHub repository write access
- PyPI package maintainer access
- Docker registry push permissions
- Documentation site update access

### Contacts

- **Release Manager**: [Name] <email>
- **Security Team**: security@error-collector-mcp.org
- **Documentation Team**: docs@error-collector-mcp.org
- **Infrastructure Team**: infra@error-collector-mcp.org

---

**Last Updated**: February 2025\
**Version**: 1.0.0\
**Next Review**: May 2025
