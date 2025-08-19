"""Unit tests for bucket policy management using minio_manager classes and functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from minio import Minio

from minio_manager.bucket_handler import handle_bucket
from minio_manager.classes.minio_resources import Bucket, BucketPolicy
from minio_manager.policy_handler import (
    apply_bucket_policy,
    delete_existing_bucket_policy,
    get_existing_bucket_policy,
    handle_bucket_policy,
    resolve_bucket_policy_file,
)
from tests.conftest import requires_minio


@requires_minio
class TestBucketPolicyFunctions:
    """Unit tests for minio_manager bucket policy functions."""

    @patch("minio_manager.policy_handler.settings")
    def test_resolve_bucket_policy_file_explicit_policy(self, mock_settings):
        """Test resolving when bucket has explicit policy file."""
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file="custom-policy.json")

        result = resolve_bucket_policy_file(bucket_policy)

        assert result == "custom-policy.json"

    @patch("minio_manager.policy_handler.settings")
    def test_resolve_bucket_policy_file_default_policy(self, mock_settings):
        """Test resolving when no explicit policy but default policy exists."""
        mock_settings.default_bucket_policy_file = "default-policy.json"

        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file=None)

        result = resolve_bucket_policy_file(bucket_policy)

        assert result == "default-policy.json"

    @patch("minio_manager.policy_handler.settings")
    def test_resolve_bucket_policy_file_no_policy(self, mock_settings):
        """Test resolving when no explicit policy and no default policy."""
        mock_settings.default_bucket_policy_file = None

        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file=None)

        result = resolve_bucket_policy_file(bucket_policy)

        assert result is None

    def test_apply_bucket_policy_simple(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test apply_bucket_policy function with simple policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create simple policy
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

        # Test apply_bucket_policy function
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify using get_existing_bucket_policy function
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert current_policy["Version"] == "2012-10-17"
        assert len(current_policy["Statement"]) == 1
        assert current_policy["Statement"][0]["Sid"] == "AllowPublicRead"
        assert current_policy["Statement"][0]["Effect"] == "Allow"

    def test_apply_bucket_policy_with_conditions(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test apply_bucket_policy function with IP conditions."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create policy with IP conditions
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

        # Test apply_bucket_policy function
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify using get_existing_bucket_policy function
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert "Condition" in current_policy["Statement"][0]
        assert "IpAddress" in current_policy["Statement"][0]["Condition"]
        source_ips = current_policy["Statement"][0]["Condition"]["IpAddress"]["aws:SourceIp"]
        assert "192.168.1.0/24" in source_ips
        assert "10.0.0.0/8" in source_ips

    def test_get_existing_bucket_policy_none(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test get_existing_bucket_policy function returns None for bucket without policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket without policy
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Test get_existing_bucket_policy function
        policy = get_existing_bucket_policy(test_bucket_name)

        assert policy is None

    def test_delete_existing_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test delete_existing_bucket_policy function."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with policy
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "TempPolicy",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        # Apply policy first
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify policy exists
        current_policy = get_existing_bucket_policy(test_bucket_name)
        assert current_policy is not None

        # Test delete_existing_bucket_policy function
        delete_existing_bucket_policy(test_bucket_name)

        # Verify policy is removed
        removed_policy = get_existing_bucket_policy(test_bucket_name)
        assert removed_policy is None

    def test_handle_bucket_policy_from_file(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function with file-based policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create policy file
        policy_content = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowReadAccess",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(policy_content, f)
            temp_policy_path = f.name

        try:
            # Test handle_bucket_policy function
            bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=temp_policy_path)
            handle_bucket_policy(bucket_policy)

            # Verify policy was applied
            current_policy = get_existing_bucket_policy(test_bucket_name)

            assert current_policy["Version"] == "2012-10-17"
            assert current_policy["Statement"][0]["Sid"] == "AllowReadAccess"
            assert current_policy["Statement"][0]["Action"] == ["s3:GetObject"]

        finally:
            Path(temp_policy_path).unlink(missing_ok=True)

    def test_handle_bucket_policy_no_file(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function with non-existent file."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Test handle_bucket_policy function with non-existent file
        bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file="/nonexistent/policy.json")

        # This should handle the error gracefully (specific behavior depends on implementation)
        with pytest.raises((FileNotFoundError, OSError)):
            handle_bucket_policy(bucket_policy)

    def test_handle_bucket_policy_update_existing(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test handle_bucket_policy function updating existing policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create initial policy file
        initial_policy_content = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "InitialPolicy",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(initial_policy_content, f)
            initial_policy_path = f.name

        # Create updated policy file
        updated_policy_content = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "UpdatedPolicy",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(updated_policy_content, f)
            updated_policy_path = f.name

        try:
            # Apply initial policy
            initial_bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=initial_policy_path)
            handle_bucket_policy(initial_bucket_policy)

            # Verify initial policy
            current_policy = get_existing_bucket_policy(test_bucket_name)
            assert current_policy["Statement"][0]["Sid"] == "InitialPolicy"

            # Update policy using handle_bucket_policy function
            updated_bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=updated_policy_path)
            handle_bucket_policy(updated_bucket_policy)

            # Verify updated policy
            current_policy = get_existing_bucket_policy(test_bucket_name)
            assert current_policy["Statement"][0]["Sid"] == "UpdatedPolicy"
            actions = current_policy["Statement"][0]["Action"]
            assert "s3:GetObject" in actions
            assert "s3:PutObject" in actions

        finally:
            Path(initial_policy_path).unlink(missing_ok=True)
            Path(updated_policy_path).unlink(missing_ok=True)


@requires_minio
class TestBucketPolicyClass:
    """Unit tests for the BucketPolicy class."""

    def test_bucket_policy_initialization_basic(self, temp_policy_file: Path):
        """Test BucketPolicy class basic initialization."""
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file=str(temp_policy_file))

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file == str(temp_policy_file)

    def test_bucket_policy_initialization_with_nonexistent_file(self):
        """Test BucketPolicy class initialization with non-existent file."""
        # This should not raise an error during initialization
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file="/nonexistent/path/policy.json")

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file == "/nonexistent/path/policy.json"

    def test_bucket_policy_attributes(self, temp_policy_file: Path):
        """Test BucketPolicy class attributes are properly set."""
        bucket_name = "my-test-bucket"
        policy_file_path = str(temp_policy_file)

        bucket_policy = BucketPolicy(bucket=bucket_name, policy_file=policy_file_path)

        # Test that attributes are accessible and correct
        assert hasattr(bucket_policy, "bucket")
        assert hasattr(bucket_policy, "policy_file")
        assert bucket_policy.bucket == bucket_name
        assert bucket_policy.policy_file == policy_file_path


@requires_minio
class TestBucketPolicyComplexScenarios:
    """Unit tests for complex bucket policy scenarios."""

    def test_policy_with_multiple_statements(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test applying policy with multiple statements using minio_manager functions."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create complex policy with multiple statements
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                },
                {
                    "Sid": "AllowListFromSpecificIP",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}"],
                    "Condition": {"IpAddress": {"aws:SourceIp": ["192.168.1.0/24"]}},
                },
                {
                    "Sid": "DenyDeleteFromInternet",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": ["s3:DeleteObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                    "Condition": {"NotIpAddress": {"aws:SourceIp": ["10.0.0.0/8", "192.168.0.0/16"]}},
                },
            ],
        }

        # Test apply_bucket_policy function with complex policy
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify complex policy using get_existing_bucket_policy function
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert len(current_policy["Statement"]) == 3

        # Check each statement exists
        sids = [stmt["Sid"] for stmt in current_policy["Statement"]]
        assert "AllowRead" in sids
        assert "AllowListFromSpecificIP" in sids
        assert "DenyDeleteFromInternet" in sids

        # Check specific statement details
        for stmt in current_policy["Statement"]:
            if stmt["Sid"] == "AllowRead":
                assert stmt["Effect"] == "Allow"
                assert "s3:GetObject" in stmt["Action"]
            elif stmt["Sid"] == "DenyDeleteFromInternet":
                assert stmt["Effect"] == "Deny"
                assert "s3:DeleteObject" in stmt["Action"]
                assert "NotIpAddress" in stmt["Condition"]

    def test_policy_deny_effect(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test applying policy with Deny effect using minio_manager functions."""
        cleanup_bucket(test_bucket_name)

        # Create bucket first
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create policy with Deny effect
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyDeleteFromEveryone",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": ["s3:DeleteObject", "s3:DeleteBucket"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}", f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }

        # Test apply_bucket_policy function with Deny effect
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify Deny policy using get_existing_bucket_policy function
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert current_policy["Statement"][0]["Effect"] == "Deny"
        actions = current_policy["Statement"][0]["Action"]
        assert "s3:DeleteObject" in actions
        assert "s3:DeleteBucket" in actions
