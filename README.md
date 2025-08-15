# minio-manager

[![Release](https://img.shields.io/github/v/release/Alveel/minio-manager?include_prereleases)](https://img.shields.io/github/v/release/Alveel/minio-manager?include_prereleases)
[![Build status](https://img.shields.io/github/actions/workflow/status/Alveel/minio-manager/main.yaml)](https://github.com/alveel/minio-manager/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)](https://img.shields.io/github/commit-activity/m/alveel/minio-manager)
[![License](https://img.shields.io/github/license/alveel/minio-manager)](https://img.shields.io/github/license/alveel/minio-manager)

Declare what MinIO buckets, IAM policies, ILM policies you want, and let MinIO Manager do the work.

- **GitHub repository**: <https://github.com/alveel/minio-manager/>
- **Documentation** <https://alveel.github.io/minio-manager/>

## Description

The concept for management is to have so-called "bucket groups".

Each bucket group is managed by an account that only has access to buckets in that group.

It should be noted that this is explicitly intended for the _creation and updating of resources in MinIO_. It does _not_
delete any resources anywhere.

## Requirements

- [Python](https://www.python.org/) (3.9 or newer)
- [PDM](https://pdm-project.org/)

### For Development and Testing

- [Podman](https://podman.io/) - Required for running local MinIO test environment
- [MinIO Client (mc)](https://min.io/docs/minio/linux/reference/minio-mc.html) - Required for MinIO configuration during testing

## Getting started with your project

Install the environment and the pre-commit hooks with

```bash
make install
```

You are now ready to start development on your project! The CI/CD
pipeline will be triggered when you open a pull request, merge to main,
or when you create a new release.

To quickly configure a local development MinIO, you can run

```shell
make run-test-environment
```
**Note**: requires [Podman](https://podman.io/)!

The test environment uses MinIO version `RELEASE.2025-04-03T14-56-28Z` for consistent and reproducible testing. You can modify the `MINIO_VERSION` variable in the Makefile to use a different version if needed.

Copy `.env.example` to `config.env` and modify to your liking.

By default, MinIO Manager automatically loads a .env file from `config.env`. Of course, you can configure your IDE to load `.env` or any other `env` file instead.

Now you can use debug tools in your IDE to run the Python code.
Configure your debugger to run the Python module `minio_manager` with the environment variables from `.env`.
A sample debugger configuration for Visual Studio Code is configured in `.vscode/launch.json` and should be directly available from "Run and Debug".

Find local MinIO installation on http://localhost:9000.

When you are finished, run

```shell
make stop-test-environment
```

**Note** that the created `secrets-insecure.yaml` will not be removed automatically and will get overwritten by the setup command.

### MinIO Version Configuration

The test environment uses a specific MinIO version (`RELEASE.2025-04-03T14-56-28Z`) defined in the Makefile for consistent and reproducible testing. To use a different version:

1. Edit the `MINIO_VERSION` variable in the Makefile
2. Stop and restart the test environment:
   ```bash
   make stop-test-environment
   make run-test-environment
   ```

This ensures all developers and CI/CD systems use the same MinIO version for testing.

### Bucket Prefix Validation

MinIO Manager supports bucket prefix validation to enforce naming conventions. This is configured via the `MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES` environment variable. 

- **Resource-level validation**: Buckets that don't match allowed prefixes are filtered out during YAML resource parsing
- **Integration testing**: Comprehensive tests verify prefix validation behavior with various scenarios
- **Configuration**: Set allowed prefixes as comma-separated values (e.g., `"test-,demo-,project-"`)

When prefix validation is enabled, only buckets matching the configured prefixes will be processed.

## Testing

MinIO Manager includes a comprehensive test suite covering bucket creation, lifecycle policies, bucket policies, and integration scenarios.

### Quick Testing

```bash
# Run unit tests (no MinIO required)
make test-unit

# Run all tests (MinIO tests will be skipped if no test environment)
make test
```

### Integration Testing

For full integration testing with MinIO:

```bash
# (Stop if running) Start test environment, run all tests
make test-full

# Or manually:
make run-test-environment  # Start MinIO test environment
make test-all             # Run all tests including integration tests
make stop-test-environment # Stop test environment
```

### Test Coverage

```bash
# Generate coverage report
make test-coverage
```

### Available Test Targets

- `make test` - Run tests (MinIO tests skipped if no environment)
- `make test-unit` - Run only unit tests (no MinIO required)
- `make test-integration` - Run integration tests (requires MinIO)
- `make test-all` - Run all tests (requires MinIO test environment)
- `make test-coverage` - Run tests with coverage report
- `make test-full` - Complete cycle: start environment → test → stop environment

### Test Structure

- **`tests/test_integration.py`** - Comprehensive end-to-end integration tests (29 tests)
- **`tests/test_basic.py`** - Basic functionality tests
- **`tests/test_utilities.py`** - Utility function and class tests
- **`tests/test_bucket_creation.py`** - Bucket creation and management tests
- **`tests/test_bucket_prefix_integration.py`** - Bucket prefix validation integration tests
- **`tests/test_lifecycle_policies.py`** - Lifecycle policy tests
- **`tests/test_bucket_policies.py`** - Bucket policy tests
- **`tests/test_resource_parser.py`** - Resource parsing and validation tests
- **`tests/test_secrets.py`** - Secret management tests
- **`tests/test_iam_policies.py`** - IAM policy tests
- **`tests/test_service_account_handler.py`** - Service account management tests

Tests automatically detect MinIO availability and skip integration tests when no test environment is running.

**📚 For detailed testing information, see the [Testing Documentation](https://alveel.github.io/minio-manager/testing/).**

To finalize the set-up for publishing to PyPi or Artifactory, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see
[here](https://fpgmaas.github.io/cookiecutter-pdm/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-pdm/features/codecov/).

## To do features

Check the open [enhancement](https://github.com/Alveel/minio-manager/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) issues.

---

Repository initiated with [fpgmaas/cookiecutter-pdm](https://github.com/fpgmaas/cookiecutter-pdm).
