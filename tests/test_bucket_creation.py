"""Tests for bucket creation and management."""

import pytest
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import VersioningConfig

from minio_manager.bucket_handler import configure_versioning, handle_bucket
from minio_manager.classes.minio_resources import Bucket
from tests.conftest import requires_minio


@requires_minio
class TestBucketCreation:
    """Test bucket creation functionality."""

    def test_create_simple_bucket(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a simple bucket without versioning."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO client directly
        minio_client.make_bucket(test_bucket_name)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify bucket appears in list
        bucket_names = [bucket.name for bucket in minio_client.list_buckets()]
        assert test_bucket_name in bucket_names

    def test_create_bucket_with_versioning_enabled(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a bucket with versioning enabled."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Enable versioning
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Verify versioning is enabled
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_create_bucket_with_versioning_suspended(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a bucket with versioning suspended."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Set versioning to suspended
        versioning_config = VersioningConfig("Suspended")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Verify versioning is suspended
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Suspended"

    def test_bucket_already_exists(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handling when bucket already exists."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first time
        minio_client.make_bucket(test_bucket_name)
        assert minio_client.bucket_exists(test_bucket_name)

        # Try to create same bucket again - should not raise error
        try:
            minio_client.make_bucket(test_bucket_name)
        except S3Error as e:
            # MinIO returns BucketAlreadyOwnedByYou error which is expected
            assert e.code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]

    def test_invalid_bucket_name(self, minio_client: Minio):
        """Test creating bucket with invalid name."""
        invalid_names = [
            "a",  # Too short
            "ab",  # Too short
            "a" * 64,  # Too long
            "UPPERCASE",  # Contains uppercase
            "bucket_with_underscore",  # Contains underscore
            "bucket..double.dot",  # Contains consecutive dots
            "bucket-",  # Ends with hyphen
            "-bucket",  # Starts with hyphen
        ]

        for invalid_name in invalid_names:
            with pytest.raises((S3Error, ValueError)):
                minio_client.make_bucket(invalid_name)


@requires_minio
class TestBucketHandler:
    """Test the bucket handler functionality."""

    def test_handle_buckets_empty_list(self):
        """Test handling empty bucket list."""
        buckets = []
        # Should not raise any errors - we'll just test that we can create buckets
        # Since there's no handle_buckets function, we'll test handle_bucket individually
        for bucket in buckets:
            handle_bucket(bucket)

    def test_check_bucket_versioning_enabled(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test checking bucket versioning when enabled."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning enabled
        minio_client.make_bucket(test_bucket_name)
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Create Bucket object
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)

        # Test configure_versioning function instead
        # This should work without errors since versioning matches
        configure_versioning(bucket)

    def test_check_bucket_versioning_suspended(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test checking bucket versioning when suspended."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning suspended
        minio_client.make_bucket(test_bucket_name)
        versioning_config = VersioningConfig("Suspended")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Create Bucket object
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)

        # Test configure_versioning function
        configure_versioning(bucket)

    def test_bucket_name_validation_in_bucket_class(self):
        """Test bucket name validation in Bucket class."""
        # Test valid bucket name
        valid_bucket = Bucket(name="valid-bucket-name")
        assert valid_bucket.name == "valid-bucket-name"

        # Test bucket names that should trigger warnings but still create object
        # (The validation in Bucket.__init__ only logs errors, doesn't raise exceptions)
        short_bucket = Bucket(name="ab")  # Too short
        assert short_bucket.name == "ab"

        long_bucket = Bucket(name="a" * 64)  # Too long
        assert long_bucket.name == "a" * 64
