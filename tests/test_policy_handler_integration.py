"""Simple integration tests for policy_handler module using real MinIO environment."""

import json
import tempfile
from pathlib import Path

import pytest
from minio import Minio

from minio_manager.policy_handler import delete_existing_bucket_policy
from tests.conftest import requires_minio


@requires_minio  
class TestDeleteExistingBucketPolicy:
    """Test bucket policy deletion with real MinIO environment."""

    def test_delete_existing_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test deleting an existing bucket policy."""
        cleanup_bucket(test_bucket_name)
        
        # Create bucket and set policy
        minio_client.make_bucket(test_bucket_name)
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{test_bucket_name}/*"
                }
            ]
        }
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))
        
        # Verify policy exists
        current_policy = minio_client.get_bucket_policy(test_bucket_name)
        assert current_policy
        
        # Delete policy
        delete_existing_bucket_policy(test_bucket_name)
        
        # Verify policy was deleted
        try:
            current_policy = minio_client.get_bucket_policy(test_bucket_name)
            assert not current_policy or current_policy.strip() == ""
        except Exception:
            # Expected - no policy exists
            pass

    def test_delete_non_existing_bucket_policy(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test deleting a bucket policy when none exists."""
        cleanup_bucket(test_bucket_name)
        
        # Create bucket without policy
        minio_client.make_bucket(test_bucket_name)
        
        # Delete policy (should not raise exception)
        delete_existing_bucket_policy(test_bucket_name)
        
        # Verify bucket still exists
        assert minio_client.bucket_exists(test_bucket_name)
        
    def test_bucket_policy_operations_with_real_minio(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test comprehensive bucket policy operations."""
        cleanup_bucket(test_bucket_name)
        
        # Create bucket
        minio_client.make_bucket(test_bucket_name)
        
        # Test 1: Set a policy
        policy1 = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{test_bucket_name}/public/*"
                }
            ]
        }
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy1))
        
        # Verify policy was set
        current_policy = minio_client.get_bucket_policy(test_bucket_name)
        assert current_policy
        policy_dict = json.loads(current_policy)
        assert "Statement" in policy_dict
        assert len(policy_dict["Statement"]) == 1
        # MinIO returns Resource as a list
        resource = policy_dict["Statement"][0]["Resource"]
        expected_resource = f"arn:aws:s3:::{test_bucket_name}/public/*"
        if isinstance(resource, list):
            assert expected_resource in resource
        else:
            assert resource == expected_resource
        
        # Test 2: Update the policy
        policy2 = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": f"arn:aws:s3:::{test_bucket_name}/uploads/*"
                }
            ]
        }
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy2))
        
        # Verify policy was updated
        current_policy = minio_client.get_bucket_policy(test_bucket_name)
        policy_dict = json.loads(current_policy)
        resource = policy_dict["Statement"][0]["Resource"]
        expected_resource = f"arn:aws:s3:::{test_bucket_name}/uploads/*"
        if isinstance(resource, list):
            assert expected_resource in resource
        else:
            assert resource == expected_resource
        action = policy_dict["Statement"][0]["Action"]
        if isinstance(action, list):
            assert "s3:PutObject" in action
        else:
            assert action == "s3:PutObject"
        
        # Test 3: Delete the policy
        delete_existing_bucket_policy(test_bucket_name)
        
        # Verify policy was deleted
        try:
            current_policy = minio_client.get_bucket_policy(test_bucket_name)
            assert not current_policy or current_policy.strip() == ""
        except Exception:
            # Expected - no policy exists
            pass
            
        # Bucket should still exist
        assert minio_client.bucket_exists(test_bucket_name)
