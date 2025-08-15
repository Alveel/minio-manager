# Testing

MinIO Manager includes a comprehensive test suite covering bucket creation, lifecycle policies, bucket policies, and integration scenarios.

## Test Structure

The test suite is organized into focused test files, each covering specific functionality:

### Core Test Files

- **`test_integration.py`** - Comprehensive end-to-end integration tests (29 tests)
  - End-to-end resource deployment and management
  - Service account creation and credential management  
  - Bucket policy application and lifecycle management
  - Component-level tests for handler functions
  - Resource class initialization and validation
  
- **`test_bucket_creation.py`** - Bucket creation logic and validation
- **`test_bucket_policies.py`** - Bucket policy handling and application
- **`test_lifecycle_policies.py`** - Lifecycle policy configuration and management
- **`test_service_account_handler.py`** - Service account creation and management
- **`test_secrets.py`** - Secret backend functionality (YAML and KeePass)
- **`test_resource_parser.py`** - YAML resource file parsing and validation
- **`test_utilities.py`** - Utility functions and helpers
- **`test_basic.py`** - Basic functionality tests

## Test Environment

### Prerequisites

- **Python 3.9+** with test dependencies installed
- **Podman** for running local MinIO test environment
- **MinIO Client (mc)** for MinIO configuration

### Setup Test Environment

```bash
# Install dependencies and setup
make install

# Start local MinIO test environment (requires Podman)
make run-test-environment

# Configure test environment
make configure-controller
```

The test environment uses **MinIO version `RELEASE.2025-04-03T14-56-28Z`** for consistent and reproducible testing across all environments.

### Test Configuration

Tests use a unified configuration via `tests/fixtures/.testenv`:

```bash
# Core test environment settings
MINIO_MANAGER_SECRET_BACKEND_TYPE=yaml
MINIO_MANAGER_SECRET_BACKEND_PATH=tests/fixtures/testsecrets-insecure.yaml
MINIO_MANAGER_CLUSTER_NAME=test-cluster
MINIO_MANAGER_S3_ENDPOINT=localhost:9000
MINIO_MANAGER_S3_ENDPOINT_SECURE=false
MINIO_MANAGER_MINIO_CONTROLLER_USER=local-test-controller
MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT=true
MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES=integration-test-,test-,demo-
```

## Running Tests

### All Tests

```bash
# Run complete test suite (145 tests)
make test

# Or using pytest directly
pytest
```

### Specific Test Categories

```bash
# Integration tests only
pytest tests/test_integration.py

# Bucket-related tests
pytest tests/test_bucket_creation.py tests/test_bucket_policies.py

# Service account tests
pytest tests/test_service_account_handler.py

# Quick smoke tests
pytest tests/test_basic.py
```

### Test Options

```bash
# Verbose output
pytest -v

# Show coverage report
pytest --cov=minio_manager

# Run with specific markers
pytest -m "not slow"

# Parallel execution (if pytest-xdist installed)
pytest -n auto
```

## Test Features

### Service Account Auto-Creation

Tests validate automatic service account creation with proper credential management:

- Service accounts are automatically created for each bucket
- Credentials are stored in the YAML secret backend
- Access policies are generated based on bucket access requirements
- Cleanup ensures no credential accumulation between test runs

### Bucket Prefix Validation

Comprehensive tests for bucket prefix enforcement:

- Valid prefixes are accepted (`test-`, `demo-`, `integration-test-`)
- Invalid prefixes are rejected with appropriate error messages
- Resource-level validation during YAML parsing
- Integration testing with various prefix scenarios

### Cleanup and Isolation

The test suite includes robust cleanup mechanisms:

- **Session-level cleanup**: Secrets file is reset after each test session
- **Test-level cleanup**: Individual buckets and resources are cleaned up after each test
- **Automatic cleanup**: No manual intervention required between test runs

### YAML Secret Backend

Tests use a file-based YAML secret backend for development and testing:

- **Location**: `tests/fixtures/testsecrets-insecure.yaml`
- **Controller credentials**: Pre-configured for test environment
- **Auto-management**: Service account credentials are automatically added/removed
- **Session cleanup**: File is reset to default state after test completion

## Development Workflow

### Adding New Tests

1. **Choose appropriate test file** based on functionality being tested
2. **Use existing fixtures** from `tests/conftest.py`:
   - `minio_client` - MinIO client connection
   - `test_bucket_name` - Unique bucket name generator
   - `cleanup_bucket` - Automatic bucket cleanup
   - `temp_policy_file` - Temporary policy file creation
   - `temp_lifecycle_file` - Temporary lifecycle policy file

3. **Follow naming conventions**:
   - Test methods: `test_descriptive_name`
   - Test classes: `TestFunctionalityName`
   - Fixtures: `descriptive_fixture_name`

### Test Data Management

- **Temporary files**: Use provided fixtures for policy/lifecycle files
- **Unique names**: Use `test_bucket_name` fixture for unique bucket names
- **Cleanup**: Always use `cleanup_bucket` fixture for bucket management
- **Isolation**: Tests should not depend on external state

### Best Practices

1. **Test isolation**: Each test should be independent and clean up after itself
2. **Descriptive names**: Test names should clearly describe what is being tested
3. **Assert messages**: Include helpful messages in assertions for debugging
4. **Error handling**: Test both success and failure scenarios
5. **Documentation**: Include docstrings for complex test scenarios

## Troubleshooting

### Common Issues

1. **MinIO not running**: Ensure `make run-test-environment` was successful
2. **Connection refused**: Check that MinIO is accessible on `localhost:9000`
3. **Permission errors**: Ensure test environment has proper service account setup
4. **Cleanup failures**: Tests should be resilient to partial cleanup failures

### Debug Mode

```bash
# Run tests with detailed output and no capture
pytest -v -s --tb=long

# Run specific failing test with maximum detail
pytest tests/test_integration.py::TestMinIOManagerIntegration::test_specific_test -vvv
```

### Environment Reset

If test environment becomes corrupted:

```bash
# Stop and restart test environment
make stop-test-environment
make run-test-environment
make configure-controller
```

## Continuous Integration

Tests run automatically in GitHub Actions on:

- Pull requests to main branch
- Pushes to main branch  
- Release creation

The CI environment mirrors the local test setup with the same MinIO version and configuration for consistency.
