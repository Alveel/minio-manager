"""Tests for bucket policy management using individual minio_manager functions."""

import json
import tempfile
from pathlib import Path

import pytest
from minio import Minio
from minio.error import S3Error

from minio_manager.classes.minio_resources import BucketPolicy
from minio_manager.policy_handler import (
    handle_bucket_policy,
    apply_bucket_policy,
    get_existing_bucket_policy,
    delete_existing_bucket_policy,
)
from tests.conftest import requires_minio


@requires_minio
class TestBucketPolicySimple:
    """Test bucket policy operations using individual minio_manager functions."""

    def test_apply_bucket_policy_simple(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test applying a simple bucket policy using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO SDK directly
        minio_client.make_bucket(test_bucket_name)

        # Create simple bucket policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowPublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        # Apply bucket policy using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy using minio_manager
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert current_policy["Version"] == "2012-10-17"
        assert len(current_policy["Statement"]) == 1
        assert current_policy["Statement"][0]["Sid"] == "AllowPublicRead"
        assert current_policy["Statement"][0]["Effect"] == "Allow"

    def test_apply_bucket_policy_with_conditions(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test applying bucket policy with conditions using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO SDK directly
        minio_client.make_bucket(test_bucket_name)

        # Create bucket policy with IP conditions
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowFromSpecificIP",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                    "Condition": {"IpAddress": {"aws:SourceIp": ["192.168.1.0/24", "10.0.0.0/8"]}},
                }
            ],
        }

        # Apply bucket policy using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy using minio_manager
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert "Condition" in current_policy["Statement"][0]
        assert "IpAddress" in current_policy["Statement"][0]["Condition"]
        source_ips = current_policy["Statement"][0]["Condition"]["IpAddress"]["aws:SourceIp"]
        assert "192.168.1.0/24" in source_ips
        assert "10.0.0.0/8" in source_ips

    def test_get_existing_bucket_policy_none(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test getting bucket policy when none exists using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket without policy
        minio_client.make_bucket(test_bucket_name)

        # Try to get non-existent policy using minio_manager
        result = get_existing_bucket_policy(test_bucket_name)
        assert result is None

    def test_delete_existing_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test deleting bucket policy using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with policy
        minio_client.make_bucket(test_bucket_name)
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        # Apply policy first using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))
        
        # Verify policy exists
        existing_policy = get_existing_bucket_policy(test_bucket_name)
        assert existing_policy is not None

        # Delete policy using minio_manager
        delete_existing_bucket_policy(test_bucket_name)

        # Verify policy is deleted
        deleted_policy = get_existing_bucket_policy(test_bucket_name)
        assert deleted_policy is None

    def test_handle_bucket_policy_from_file(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function with policy file using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO SDK directly
        minio_client.make_bucket(test_bucket_name)

        # Create a temporary policy file
        policy_content = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowPublicReadWrite",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(policy_content, f)
            temp_policy_path = f.name

        try:
            # Create BucketPolicy object
            bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=temp_policy_path)
            
            # Use handle_bucket_policy function
            handle_bucket_policy(bucket_policy)
            
            # Verify policy was applied using minio_manager
            current_policy = get_existing_bucket_policy(test_bucket_name)
            
            assert current_policy["Version"] == "2012-10-17"
            assert len(current_policy["Statement"]) == 1
            assert current_policy["Statement"][0]["Sid"] == "AllowPublicReadWrite"
            assert "s3:GetObject" in current_policy["Statement"][0]["Action"]
            assert "s3:PutObject" in current_policy["Statement"][0]["Action"]
            
        finally:
            # Cleanup temporary file
            Path(temp_policy_path).unlink(missing_ok=True)

    def test_handle_bucket_policy_no_file(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function with no policy file."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO SDK directly
        minio_client.make_bucket(test_bucket_name)

        # Create BucketPolicy object with no policy file
        bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=None)
        
        # Use handle_bucket_policy function - should not raise error
        handle_bucket_policy(bucket_policy)
        
        # Verify no policy was applied
        current_policy = get_existing_bucket_policy(test_bucket_name)
        assert current_policy is None

    def test_handle_bucket_policy_update_existing(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function updating existing policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using MinIO SDK directly
        minio_client.make_bucket(test_bucket_name)

        # Set initial policy
        initial_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }
        apply_bucket_policy(test_bucket_name, json.dumps(initial_policy))

        # Create new policy file
        new_policy_content = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowReadWrite",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(new_policy_content, f)
            temp_policy_path = f.name

        try:
            # Create BucketPolicy object
            bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=temp_policy_path)
            
            # Use handle_bucket_policy function to update
            handle_bucket_policy(bucket_policy)
            
            # Verify policy was updated using minio_manager
            current_policy = get_existing_bucket_policy(test_bucket_name)
            
            assert current_policy["Statement"][0]["Sid"] == "AllowReadWrite"
            assert "s3:PutObject" in current_policy["Statement"][0]["Action"]
            
        finally:
            # Cleanup temporary file
            Path(temp_policy_path).unlink(missing_ok=True)


@requires_minio
class TestBucketPolicyDirectSDK:
    """Test bucket policy operations using MinIO SDK directly for comparison."""

    def test_bucket_policy_class_initialization(self):
        """Test BucketPolicy class initialization."""
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file="test-policy.json")

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file == "test-policy.json"

    def test_bucket_policy_no_file(self):
        """Test BucketPolicy with no policy file."""
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file=None)

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file is None
