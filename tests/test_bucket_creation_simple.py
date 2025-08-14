"""Tests for bucket creation and management using individual minio_manager functions."""

import pytest
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import VersioningConfig
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration, Filter

from minio_manager.bucket_handler import configure_versioning, configure_lifecycle, check_bucket_lifecycle
from minio_manager.classes.minio_resources import Bucket
from tests.conftest import requires_minio


@requires_minio
class TestBucketCreationSimple:
    """Test bucket creation using individual minio_manager functions."""

    def test_configure_versioning_enable(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test enabling versioning using minio_manager configure_versioning."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Create Bucket object with versioning enabled
        versioning_config = VersioningConfig("Enabled")
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)

        # Test configure_versioning function
        configure_versioning(bucket)
        
        # Verify versioning is enabled
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_configure_versioning_suspend(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test suspending versioning using minio_manager configure_versioning."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Enable versioning first
        enable_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, enable_config)
        
        # Now suspend it using minio_manager
        suspend_config = VersioningConfig("Suspended")
        bucket = Bucket(name=test_bucket_name, versioning=suspend_config)
        configure_versioning(bucket)
        
        # Verify versioning is suspended
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Suspended"

    def test_configure_versioning_no_change_needed(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test configure_versioning when no change is needed."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Enable versioning
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)
        
        # Try to enable again with minio_manager (should be no-op)
        bucket = Bucket(name=test_bucket_name, versioning=versioning_config)
        configure_versioning(bucket)
        
        # Verify versioning is still enabled
        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

    def test_configure_lifecycle_with_expiration(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test configuring lifecycle policy using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Create lifecycle config with correct API
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    "Enabled",
                    rule_id="test-lifecycle-rule",
                    expiration=Expiration(days=30),
                    rule_filter=Filter(prefix="documents/"),
                )
            ]
        )

        # Create Bucket object with lifecycle_config
        bucket = Bucket(name=test_bucket_name, lifecycle_config=lifecycle_config)

        # Use configure_lifecycle function
        configure_lifecycle(bucket)
        
        # Verify lifecycle is configured
        current_lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(current_lifecycle.rules) == 1
        assert current_lifecycle.rules[0].rule_id == "test-lifecycle-rule"
        assert current_lifecycle.rules[0].expiration.days == 30

    def test_check_bucket_lifecycle_no_existing_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test check_bucket_lifecycle when no existing policy exists."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Create lifecycle config
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    "Enabled",
                    rule_id="new-rule",
                    expiration=Expiration(days=60),
                    rule_filter=Filter(prefix="temp/"),
                )
            ]
        )

        # Create Bucket object with lifecycle_config
        bucket = Bucket(name=test_bucket_name, lifecycle_config=lifecycle_config)        # Test check_bucket_lifecycle function - should return False (update needed)
        result = check_bucket_lifecycle(bucket)
        assert result is False  # No existing policy, so update is needed

    def test_check_bucket_lifecycle_with_existing_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test check_bucket_lifecycle when policy already exists."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        minio_client.make_bucket(test_bucket_name)
        
        # Set initial lifecycle policy
        initial_lifecycle = LifecycleConfig(
            [
                Rule(
                    "Enabled",
                    rule_id="existing-rule",
                    expiration=Expiration(days=30),
                    rule_filter=Filter(prefix="old/"),
                )
            ]
        )
        minio_client.set_bucket_lifecycle(test_bucket_name, initial_lifecycle)
        
        # Create different lifecycle config to compare
        new_lifecycle = LifecycleConfig(
            [
                Rule(
                    "Enabled",
                    rule_id="new-rule",
                    expiration=Expiration(days=60),
                    rule_filter=Filter(prefix="new/"),
                )
            ]
        )

        # Create Bucket object with new lifecycle_config
        bucket = Bucket(name=test_bucket_name, lifecycle_config=new_lifecycle)        # Test check_bucket_lifecycle function - should return True (needs update)
        result = check_bucket_lifecycle(bucket)
        assert result is True  # Different policy, so update is needed


@requires_minio  
class TestBucketCreationDirectSDK:
    """Test bucket creation using MinIO SDK directly for comparison."""

    def test_create_simple_bucket_sdk(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating a simple bucket using MinIO SDK directly."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO client directly
        minio_client.make_bucket(test_bucket_name)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify bucket appears in list
        bucket_names = [bucket.name for bucket in minio_client.list_buckets()]
        assert test_bucket_name in bucket_names

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
