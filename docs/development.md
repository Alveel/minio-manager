# Development Guide

This guide covers development setup, contribution guidelines, and project structure for MinIO Manager contributors.

## Quick Start

```bash
# Clone and setup development environment
git clone https://github.com/alveel/minio-manager.git
cd minio-manager/minio-manager-python
make install

# Start local test environment
make run-test-environment

# Run tests
make test
```

## Development Environment

### Prerequisites

- **Python 3.9+** 
- **PDM** (Python Dependency Manager)
- **Podman** (for local MinIO test environment)
- **MinIO Client (mc)** (for MinIO configuration)

### Installation

```bash
# Install dependencies and pre-commit hooks
make install

# Verify installation
pdm list
```

This installs:
- Project dependencies
- Development dependencies (pytest, black, ruff, etc.)
- Pre-commit hooks for code quality

### Local MinIO Environment

```bash
# Start MinIO container (requires Podman)
make run-test-environment

# Configure test environment
make configure-controller

# Access MinIO web interface: http://localhost:9000
# Login: minioadmin / minioadmin

# Stop environment when done
make stop-test-environment
```

**MinIO Version:** The test environment uses `RELEASE.2025-04-03T14-56-28Z` for consistency. Modify `MINIO_VERSION` in Makefile to use different versions.

## Project Structure

```
minio-manager-python/
├── minio_manager/           # Main application code
│   ├── __main__.py         # CLI entry point
│   ├── app.py              # Main application logic
│   ├── *_handler.py        # Resource handlers (bucket, policy, etc.)
│   ├── classes/            # Core classes and utilities
│   └── resources/          # Embedded resources and policies
├── tests/                  # Test suite
│   ├── conftest.py         # Test fixtures and configuration
│   ├── test_*.py           # Test modules
│   └── fixtures/           # Test data and environment files
├── docs/                   # Documentation
├── examples/               # Example configurations
└── Makefile               # Development automation
```

### Key Components

- **Resource Handlers**: Handle bucket creation, policy management, service accounts
- **Classes**: Core abstractions for MinIO resources, settings, secrets
- **Utilities**: Helper functions for comparisons, JSON handling, etc.
- **CLI**: Command-line interface with configuration validation

## Development Workflow

### Code Quality

```bash
# Run all quality checks
make quality

# Individual checks
make check-code        # Ruff linting
make format           # Black formatting
make check-format     # Check formatting without changes
make type-check       # MyPy type checking
```

Pre-commit hooks automatically run these checks before each commit.

### Testing

```bash
# Full test suite
make test

# With coverage report
make test-coverage

# Specific test categories
pytest tests/test_integration.py     # Integration tests
pytest tests/test_bucket_*.py        # Bucket-related tests
pytest tests/test_service_*.py       # Service account tests
```

See [Testing Documentation](testing.md) for detailed testing information.

### Configuration

Development uses YAML secret backend for simplicity:

```yaml
# tests/fixtures/.testenv
MINIO_MANAGER_SECRET_BACKEND_TYPE=yaml
MINIO_MANAGER_SECRET_BACKEND_PATH=tests/fixtures/testsecrets-insecure.yaml
MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT=true
MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES=integration-test-,test-,demo-
```

## Contributing

### Pull Request Process

1. **Fork and clone** the repository
2. **Create feature branch** from main
3. **Make changes** with tests
4. **Run quality checks** (`make quality`)
5. **Run tests** (`make test`)
6. **Submit pull request** with description

### Code Standards

- **Python 3.9+ compatibility**
- **Type hints** for all public APIs
- **Docstrings** for classes and complex functions
- **Tests** for new functionality
- **Black formatting** (enforced by pre-commit)
- **Ruff linting** (enforced by pre-commit)

### Commit Messages

Follow conventional commit format:

```
type(scope): description

feat(bucket): add lifecycle policy validation
fix(secrets): handle missing YAML backend file
docs(testing): add integration test documentation
test(bucket): add bucket prefix validation tests
```

### Adding Features

1. **Design first**: Consider impact on existing APIs
2. **Test-driven**: Write tests before implementation
3. **Documentation**: Update relevant docs
4. **Backwards compatibility**: Avoid breaking changes
5. **Configuration**: Add environment variables if needed

## Debugging

### IDE Setup

**VS Code**: Use `.vscode/launch.json` for debugging:

```json
{
    "name": "Debug MinIO Manager",
    "type": "python",
    "request": "launch",
    "module": "minio_manager",
    "envFile": "${workspaceFolder}/config.env",
    "console": "integratedTerminal"
}
```

### Common Debug Scenarios

```bash
# Debug with verbose logging
MINIO_MANAGER_LOG_LEVEL=DEBUG python -m minio_manager

# Dry run mode for testing configuration
python -m minio_manager --dry-run

# Debug specific resource file
python -m minio_manager --resources-file debug/resources.yaml

# Test connection without applying changes
MINIO_MANAGER_DRY_RUN=true python -m minio_manager
```

### Test Environment Issues

```bash
# Reset test environment
make stop-test-environment
make clean
make run-test-environment
make configure-controller

# Check MinIO connectivity
mc admin info testminio

# Check service account setup
mc admin user svcacct ls testminio local-test-controller
```

## Release Process

### Version Management

Versions follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Create release tag**: `git tag v1.2.3`
4. **Push tag**: `git push origin v1.2.3`
5. **GitHub Actions** handles PyPI publishing

## Architecture Notes

### Design Principles

- **Declarative configuration**: YAML-based resource definitions
- **Idempotent operations**: Safe to run multiple times
- **Fail-fast validation**: Catch errors early in the process
- **Minimal dependencies**: Keep external dependencies focused
- **Testable design**: Comprehensive test coverage

### Extension Points

- **Secret backends**: Add new secret storage mechanisms
- **Resource types**: Add support for new MinIO resources
- **Policy generators**: Custom policy generation logic
- **Validation rules**: Custom resource validation

For implementation examples, see existing handlers in `minio_manager/` directory.
