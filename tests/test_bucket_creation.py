"""Tests for bucket creation and management using minio_manager functions."""

import pytest
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import VersioningConfig
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration, Filter

from minio_manager.bucket_handler import configure_versioning, handle_bucket, configure_lifecycle
from minio_manager.classes.minio_resources import Bucket
from tests.conftest import requires_minio


@requires_minio
class TestBucketCreation:
    """Test bucket creation functionality."""

    def test_create_simple_bucket(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a simple bucket using minio_manager handle_bucket function."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager handle_bucket function
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify bucket appears in list
        bucket_names = [bucket.name for bucket in minio_client.list_buckets()]
        assert test_bucket_name in bucket_names

    def test_create_bucket_with_versioning_enabled(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a bucket with versioning enabled using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning using minio_manager
        versioning_config = VersioningConfig("Enabled")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)
        handle_bucket(bucket)

        # Verify versioning is enabled
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_create_bucket_with_versioning_suspended(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a bucket with versioning suspended using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning suspended using minio_manager
        versioning_config = VersioningConfig("Suspended")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)
        handle_bucket(bucket)

        # Verify versioning is suspended
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Suspended"

    def test_bucket_already_exists(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handling when bucket already exists using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first time using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)
        assert minio_client.bucket_exists(test_bucket_name)

        # Try to create same bucket again using minio_manager - should handle gracefully
        handle_bucket(bucket)  # Should not raise error, bucket handler should handle existing buckets
        assert minio_client.bucket_exists(test_bucket_name)

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
    """Test the bucket handler functionality using minio_manager functions."""

    def test_handle_buckets_empty_list(self):
        """Test handling empty bucket list."""
        buckets = []
        # Should not raise any errors
        for bucket in buckets:
            handle_bucket(bucket)

    def test_create_bucket_with_lifecycle_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating bucket with lifecycle policy using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create lifecycle config
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    rule_id="lifecycle-rule-1",
                    status="Enabled",
                    expiration=Expiration(days=30),
                    rule_filter=Filter(prefix="documents/"),
                )
            ]
        )
        
        # Create bucket with lifecycle using minio_manager
        bucket = Bucket(name=test_bucket_name, lifecycle_config=lifecycle_config)
        handle_bucket(bucket)
        
        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)
        
        # Verify lifecycle policy is applied
        current_lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(current_lifecycle.rules) == 1
        assert current_lifecycle.rules[0].rule_id == "lifecycle-rule-1"

    def test_configure_versioning_function_directly(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test configure_versioning function directly."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Create Bucket object with versioning
        versioning_config = VersioningConfig("Enabled")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)

        # Test configure_versioning function
        configure_versioning(bucket)
        
        # Verify versioning is configured
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_configure_lifecycle_function_directly(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test configure_lifecycle function directly."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Create lifecycle config
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    rule_id="test-lifecycle-rule",
                    status="Enabled",
                    expiration=Expiration(days=60),
                    rule_filter=Filter(prefix="temp/"),
                )
            ]
        )
        
        # Create Bucket object with lifecycle
        bucket = Bucket(name=test_bucket_name, lifecycle_config=lifecycle_config)

        # Test configure_lifecycle function
        configure_lifecycle(bucket)
        
        # Verify lifecycle is configured
        current_lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(current_lifecycle.rules) == 1
        assert current_lifecycle.rules[0].rule_id == "test-lifecycle-rule"
        assert current_lifecycle.rules[0].expiration.days == 60

    def test_check_bucket_versioning_enabled(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test bucket versioning configuration using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning enabled using minio_manager
        versioning_config = VersioningConfig("Enabled")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)
        handle_bucket(bucket)

        # Verify versioning is enabled
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_check_bucket_versioning_suspended(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test bucket versioning suspended using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning suspended using minio_manager
        versioning_config = VersioningConfig("Suspended")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)
        handle_bucket(bucket)

        # Verify versioning is suspended
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Suspended"

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
