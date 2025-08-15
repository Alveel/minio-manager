"""Test configuration and fixtures for MinIO Manager tests."""

import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from minio import Minio
from minio.deleteobjects import DeleteObject


# Define custom pytest marks
def pytest_configure(config):
    """Configure pytest and set up test environment variables before any imports."""
    # Load environment variables from .testenv file
    testenv_path = Path(__file__).parent / "fixtures" / ".testenv"
    
    if testenv_path.exists():
        with open(testenv_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
    else:
        # Fallback to hardcoded values if .testenv file doesn't exist
        os.environ["MINIO_MANAGER_SECRET_BACKEND_TYPE"] = "yaml"
        os.environ["MINIO_MANAGER_SECRET_BACKEND_PATH"] = "tests/fixtures/testsecrets-insecure.yaml"
        os.environ["MINIO_MANAGER_CLUSTER_NAME"] = "test-cluster"
        os.environ["MINIO_MANAGER_S3_ENDPOINT"] = "localhost:9000"
        os.environ["MINIO_MANAGER_S3_ENDPOINT_SECURE"] = "false"
        os.environ["MINIO_MANAGER_MINIO_CONTROLLER_USER"] = "local-test-controller"
        os.environ["MINIO_MANAGER_DRY_RUN"] = "false"
        os.environ["MINIO_MANAGER_LOG_LEVEL"] = "INFO"
        os.environ["MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT"] = "true"  # Enable for comprehensive testing
        os.environ["MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING"] = "Suspended"
        os.environ["MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES"] = "integration-test-,test-,demo-"


@pytest.fixture(scope="session", autouse=True)
def clean_secrets_file():
    """Ensure the secrets file starts clean for each test session."""
    secrets_file = Path(__file__).parent / "fixtures" / "testsecrets-insecure.yaml"
    controller_secrets = {
        "local-test-controller": {
            "access_key": "static-for-testing",
            "secret_key": "static-secret-key-for-testing"
        }
    }
    
    try:
        import yaml
        with open(secrets_file, 'w') as f:
            yaml.dump(controller_secrets, f, default_flow_style=False)
    except Exception as e:
        print(f"Error initializing secrets file: {e}")
    
    yield
    # Cleanup happens in pytest_sessionfinish


@pytest.fixture(scope="session")
def minio_client() -> Minio:
    """MinIO client fixture for tests."""
    return Minio(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )


@pytest.fixture
def temp_policy_file() -> Generator[Path, None, None]:
    """Create a temporary policy file for testing."""
    policy_content = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowReadAccess",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::test-bucket/*"],
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(policy_content, f, indent=2)
        temp_path = Path(f.name)

    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.fixture
def temp_lifecycle_file() -> Generator[Path, None, None]:
    """Create a temporary lifecycle policy file for testing."""
    lifecycle_content = {
        "Rules": [
            {
                "ID": "TestLifecycleRule",
                "Status": "Enabled",
                "Expiration": {"Days": 30},
                "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(lifecycle_content, f, indent=2)
        temp_path = Path(f.name)

    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.fixture
def test_bucket_name() -> str:
    """Generate a unique test bucket name."""
    import uuid

    return f"test-bucket-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def cleanup_bucket(minio_client):
    """Fixture to clean up created buckets during test."""
    buckets_to_cleanup = []

    def cleanup_bucket_func(bucket_name):
        """Clean up bucket immediately and register for teardown cleanup."""
        # Immediate cleanup for idempotency
        try:
            if minio_client.bucket_exists(bucket_name):
                # Remove all objects in bucket first
                objects = minio_client.list_objects(bucket_name, recursive=True)
                delete_object_list = [DeleteObject(obj.object_name) for obj in objects]
                if delete_object_list:
                    errors = minio_client.remove_objects(bucket_name, delete_object_list)
                    for error in errors:
                        print(f"Error deleting object: {error}")
                
                # Remove bucket
                minio_client.remove_bucket(bucket_name)
        except Exception as e:
            print(f"Error cleaning up bucket {bucket_name} immediately: {e}")
        
        # Register for teardown cleanup as well (defensive)
        if bucket_name not in buckets_to_cleanup:
            buckets_to_cleanup.append(bucket_name)

    yield cleanup_bucket_func

    # Cleanup after test (defensive - should already be clean)
    for bucket_name in buckets_to_cleanup:
        try:
            if minio_client.bucket_exists(bucket_name):
                # Remove all objects in bucket first
                objects = minio_client.list_objects(bucket_name, recursive=True)
                delete_object_list = [DeleteObject(obj.object_name) for obj in objects]
                if delete_object_list:
                    errors = minio_client.remove_objects(bucket_name, delete_object_list)
                    for error in errors:
                        print(f"Error deleting object: {error}")
                
                # Remove bucket
                minio_client.remove_bucket(bucket_name)
        except Exception as e:
            print(f"Error cleaning up bucket {bucket_name}: {e}")


def pytest_sessionfinish(session, exitstatus):
    """Clean up test data at the end of the test session."""
    # Reset the secrets file to only contain the controller user
    secrets_file = Path(__file__).parent / "fixtures" / "testsecrets-insecure.yaml"
    controller_secrets = {
        "local-test-controller": {
            "access_key": "static-for-testing",
            "secret_key": "static-secret-key-for-testing"
        }
    }
    
    try:
        import yaml
        with open(secrets_file, 'w') as f:
            yaml.dump(controller_secrets, f, default_flow_style=False)
        print(f"Cleaned up secrets file: {secrets_file}")
    except Exception as e:
        print(f"Error cleaning up secrets file: {e}")


requires_minio = pytest.mark.skipif(False, reason="MinIO test environment not available")  # Will be set dynamically
