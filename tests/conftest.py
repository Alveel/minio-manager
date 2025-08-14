"""Test configuration and fixtures for MinIO Manager tests."""

import json
import tempfile
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from minio import Minio


@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment():
    """Ensure test environment is properly set up before any tests run."""
    try:
        # Check if MinIO is accessible and service account exists
        result = subprocess.run(
            ["mc", "admin", "user", "svcacct", "ls", "testminio", "local-test-controller"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # If command succeeds and our test service account is found, we're ready
        if result.returncode == 0 and "static-for-testing" in result.stdout:
            yield
            return
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # If we get here, either MinIO isn't running or service account isn't set up
    print("\n⚠️  Test environment may not be fully configured.")
    print("💡 For integration tests, run: make run-test-environment")
    print("💡 Or manually start MinIO and run: make configure-controller")
    
    yield


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
def cleanup_bucket(minio_client: Minio):
    """Fixture to cleanup buckets after tests."""
    buckets_to_cleanup = []

    def register_bucket(bucket_name: str):
        buckets_to_cleanup.append(bucket_name)

    yield register_bucket

    # Cleanup
    for bucket_name in buckets_to_cleanup:
        try:
            # Remove all objects first
            objects = minio_client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                minio_client.remove_object(bucket_name, obj.object_name)

            # Remove bucket
            if minio_client.bucket_exists(bucket_name):
                minio_client.remove_bucket(bucket_name)
        except Exception as e:
            print(f"Warning: Failed to cleanup bucket {bucket_name}: {e}")


requires_minio = pytest.mark.skipif(False, reason="MinIO test environment not available")  # Will be set dynamically
