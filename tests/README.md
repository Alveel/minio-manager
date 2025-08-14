# MinIO Manager Tests

This directory contains comprehensive tests for the MinIO Manager functionality.

## Prerequisites

Before running the tests, you need to have a MinIO test environment running. The easiest way is to use Docker:

```bash
# Start MinIO in development mode
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  quay.io/minio/minio server /data --console-address ":9001"
```

Or using docker-compose:

```yaml
version: '3.8'
services:
  minio:
    image: quay.io/minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data

volumes:
  minio_data:
```

## Running Tests

### Install Test Dependencies

```bash
# Install all dependencies including test dependencies
pdm install --dev

# Or just test dependencies
pdm install --group test
```

### Run All Tests

```bash
# Run all tests
pdm run pytest

# Run with coverage
pdm run pytest --cov=minio_manager --cov-report=html

# Run with verbose output
pdm run pytest -v
```

### Run Specific Test Categories

```bash
# Run only bucket creation tests
pdm run pytest tests/test_bucket_creation.py

# Run only lifecycle policy tests
pdm run pytest tests/test_lifecycle_policies.py

# Run only bucket policy tests
pdm run pytest tests/test_bucket_policies.py

# Run only integration tests
pdm run pytest tests/test_integration.py

# Run only utility tests (no MinIO required)
pdm run pytest tests/test_utilities.py
```

### Run Tests Without MinIO

If you don't have MinIO running, you can run only the utility tests:

```bash
pdm run pytest tests/test_utilities.py
```

All other tests will be automatically skipped if MinIO is not available.

## Test Structure

### conftest.py
Contains shared fixtures and configuration for all tests:
- `test_settings`: MinIO connection settings
- `minio_client`: Pre-configured MinIO client
- `temp_policy_file`: Temporary JSON policy file
- `temp_lifecycle_file`: Temporary lifecycle configuration file
- `test_bucket_name`: Unique bucket name generator
- `cleanup_bucket`: Automatic bucket cleanup after tests
- `requires_minio`: Decorator to skip tests when MinIO unavailable

### test_bucket_creation.py
Tests for bucket creation and management:
- Basic bucket creation
- Bucket versioning (enabled/suspended)
- Bucket name validation
- Error handling for existing buckets

### test_lifecycle_policies.py
Tests for bucket lifecycle policy management:
- Simple lifecycle rules (expiration)
- Non-current version expiration
- Multiple lifecycle rules
- Lifecycle policy from JSON files
- Policy comparison and updates

### test_bucket_policies.py
Tests for bucket policy management:
- Simple bucket policies (Allow/Deny)
- Complex policies with conditions
- Multiple statements
- Policy updates
- Policy from JSON files

### test_integration.py
Integration tests combining multiple features:
- Complete bucket setup (versioning + lifecycle + policy)
- Bucket operations with actual objects
- Policy and access control scenarios
- Full cleanup and teardown procedures

### test_utilities.py
Tests for utility functions and resource classes:
- JSON file reading
- Policy normalization
- MinIO resource class initialization
- Error handling

## Test Features

### Automatic Cleanup
All tests automatically clean up created buckets and their contents after completion using the `cleanup_bucket` fixture.

### MinIO Availability Check
Tests that require MinIO are automatically skipped if MinIO is not available, preventing test failures in CI/CD environments without MinIO.

### Temporary Files
Tests use temporary files for policy and lifecycle configurations, ensuring no leftover files and enabling parallel test execution.

### Comprehensive Coverage
Tests cover:
- ✅ Bucket creation and management
- ✅ Versioning configuration
- ✅ Lifecycle policies
- ✅ Bucket policies
- ✅ Object operations
- ✅ Error handling
- ✅ Resource class functionality
- ✅ Utility functions
- ✅ Integration scenarios

## Example Test Output

```
$ pdm run pytest -v

========================= test session starts =========================
collecting ... collected 45 items

tests/test_bucket_creation.py::TestBucketCreation::test_create_simple_bucket PASSED
tests/test_bucket_creation.py::TestBucketCreation::test_create_bucket_with_versioning_enabled PASSED
tests/test_lifecycle_policies.py::TestLifecyclePolicyCreation::test_create_simple_lifecycle_rule PASSED
tests/test_bucket_policies.py::TestBucketPolicyCreation::test_set_simple_bucket_policy PASSED
tests/test_integration.py::TestIntegrationScenarios::test_complete_bucket_setup PASSED
tests/test_utilities.py::TestUtilities::test_read_json_valid_file PASSED

========================= 45 passed in 12.34s =========================
```

## CI/CD Integration

These tests are designed to work in CI/CD environments:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      minio:
        image: quay.io/minio/minio
        ports:
          - 9000:9000
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        options: --health-cmd "curl -f http://localhost:9000/minio/health/live" --health-interval 30s --health-timeout 20s --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install PDM
      run: pip install pdm
    - name: Install dependencies
      run: pdm install --dev
    - name: Run tests
      run: pdm run pytest --cov=minio_manager --cov-report=xml
```
