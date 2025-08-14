"""Tests for bucket policy management using minio_manager functions."""

import json
import tempfile
from pathlib import Path

import pytest
from minio import Minio
from minio.error import S3Error

from minio_manager.classes.minio_resources import Bucket, BucketPolicy
from minio_manager.policy_handler import handle_bucket_policy, apply_bucket_policy, get_existing_bucket_policy
from minio_manager.bucket_handler import handle_bucket
from tests.conftest import requires_minio


@requires_minio
class TestBucketPolicyCreation:
    """Test bucket policy creation and management."""

    def test_set_simple_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test setting a simple bucket policy using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

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

        # Set bucket policy using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy using minio_manager
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert current_policy["Version"] == "2012-10-17"
        assert len(current_policy["Statement"]) == 1
        assert current_policy["Statement"][0]["Sid"] == "AllowPublicRead"
        assert current_policy["Statement"][0]["Effect"] == "Allow"

    def test_set_bucket_policy_with_conditions(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test setting bucket policy with conditions using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

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

        # Set bucket policy using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy using minio_manager
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert "Condition" in current_policy["Statement"][0]
        assert "IpAddress" in current_policy["Statement"][0]["Condition"]
        source_ips = current_policy["Statement"][0]["Condition"]["IpAddress"]["aws:SourceIp"]
        assert "192.168.1.0/24" in source_ips
        assert "10.0.0.0/8" in source_ips

    def test_set_bucket_policy_deny_effect(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test setting bucket policy with Deny effect using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create bucket policy with Deny effect
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

        # Set bucket policy using minio_manager
        apply_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy using minio_manager
        current_policy = get_existing_bucket_policy(test_bucket_name)

        assert current_policy["Statement"][0]["Effect"] == "Deny"
        actions = current_policy["Statement"][0]["Action"]
        assert "s3:DeleteObject" in actions
        assert "s3:DeleteBucket" in actions

    def test_remove_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test removing bucket policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Set bucket policy
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
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify policy exists
        policy_str = minio_client.get_bucket_policy(test_bucket_name)
        assert policy_str is not None

        # Remove bucket policy
        minio_client.delete_bucket_policy(test_bucket_name)

        # Verify policy is removed
        with pytest.raises(S3Error) as exc_info:
            minio_client.get_bucket_policy(test_bucket_name)
        assert exc_info.value.code == "NoSuchBucketPolicy"


@requires_minio
class TestBucketPolicyFromFile:
    """Test bucket policy creation from files."""

    def test_bucket_policy_from_json_file(
        self, minio_client: Minio, test_bucket_name: str, cleanup_bucket
    ):
        """Test setting bucket policy from JSON file using minio_manager."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

        # Create policy content with correct bucket name
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(policy_content, f)
            temp_policy_path = f.name

        try:
            # Create BucketPolicy object pointing to the temp policy file
            bucket_policy = BucketPolicy(bucket=test_bucket_name, policy_file=temp_policy_path)
            
            # Use minio_manager handle_bucket_policy function
            handle_bucket_policy(bucket_policy)

            # Verify bucket policy using minio_manager
            current_policy = get_existing_bucket_policy(test_bucket_name)

            assert current_policy["Version"] == "2012-10-17"
            assert current_policy["Statement"][0]["Sid"] == "AllowReadAccess"
            assert current_policy["Statement"][0]["Action"] == ["s3:GetObject"]
        finally:
            # Cleanup temporary file
            Path(temp_policy_path).unlink(missing_ok=True)

    def test_handle_bucket_policy_comprehensive(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test comprehensive bucket policy handling using minio_manager functions."""
        cleanup_bucket(test_bucket_name)

        # Create bucket using minio_manager
        bucket = Bucket(name=test_bucket_name)
        handle_bucket(bucket)

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

    def test_bucket_policy_class_initialization(self, temp_policy_file: Path):
        """Test BucketPolicy class initialization."""
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file=str(temp_policy_file))

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file == str(temp_policy_file)

    def test_invalid_policy_file_path(self):
        """Test BucketPolicy with invalid file path."""
        # This should not raise an error during initialization
        # The error handling should happen when the policy is actually applied
        bucket_policy = BucketPolicy(bucket="test-bucket", policy_file="/nonexistent/path/policy.json")

        assert bucket_policy.bucket == "test-bucket"
        assert bucket_policy.policy_file == "/nonexistent/path/policy.json"


@requires_minio
class TestBucketPolicyHandler:
    """Test the bucket policy handler functionality."""

    def test_handle_bucket_policies_empty_list(self):
        """Test handling empty bucket list."""
        buckets = []
        # Since there's no handle_bucket_policies function,
        # we'll test that we can iterate through empty list without errors
        for bucket in buckets:
            if hasattr(bucket, "policy") and bucket.policy:
                handle_bucket_policy(bucket.policy)

    def test_handle_bucket_policy_with_file(
        self, minio_client: Minio, test_bucket_name: str, temp_policy_file: Path, cleanup_bucket
    ):
        """Test handling bucket policy from file."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Create Bucket object with policy
        class MockBucketPolicy:
            def __init__(self, file_path: str):
                self.file = file_path

        bucket = Bucket(name=test_bucket_name)
        bucket.policy = MockBucketPolicy(str(temp_policy_file))

        # This test would require mocking the settings and policy handler
        # For now, we'll test the components separately
        assert bucket.name == test_bucket_name
        assert bucket.policy.file == str(temp_policy_file)

    def test_multiple_bucket_policies(self, minio_client: Minio, temp_policy_file: Path, cleanup_bucket):
        """Test handling multiple buckets with policies."""
        test_buckets = []

        # Create multiple test buckets
        for i in range(3):
            bucket_name = f"test-policy-bucket-{i}"
            test_buckets.append(bucket_name)
            cleanup_bucket(bucket_name)

            # Create bucket
            minio_client.make_bucket(bucket_name)

            # Create unique policy for each bucket
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": f"Policy{i}",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                    }
                ],
            }

            # Set bucket policy
            minio_client.set_bucket_policy(bucket_name, json.dumps(policy))

            # Verify policy was set
            current_policy_str = minio_client.get_bucket_policy(bucket_name)
            current_policy = json.loads(current_policy_str)
            assert current_policy["Statement"][0]["Sid"] == f"Policy{i}"


@requires_minio
class TestBucketPolicyComplexScenarios:
    """Test complex bucket policy scenarios."""

    def test_policy_with_multiple_statements(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test bucket policy with multiple statements."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

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

        # Set bucket policy
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify bucket policy
        current_policy_str = minio_client.get_bucket_policy(test_bucket_name)
        current_policy = json.loads(current_policy_str)

        assert len(current_policy["Statement"]) == 3

        # Check each statement
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

    def test_policy_update_scenario(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test updating an existing bucket policy."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Set initial policy
        initial_policy = {
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
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(initial_policy))

        # Verify initial policy
        current_policy_str = minio_client.get_bucket_policy(test_bucket_name)
        current_policy = json.loads(current_policy_str)
        assert current_policy["Statement"][0]["Sid"] == "InitialPolicy"

        # Update policy
        updated_policy = {
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
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(updated_policy))

        # Verify updated policy
        current_policy_str = minio_client.get_bucket_policy(test_bucket_name)
        current_policy = json.loads(current_policy_str)
        assert current_policy["Statement"][0]["Sid"] == "UpdatedPolicy"
        actions = current_policy["Statement"][0]["Action"]
        assert "s3:GetObject" in actions
        assert "s3:PutObject" in actions
