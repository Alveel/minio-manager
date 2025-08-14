"""End-to-end integration tests for MinIO Manager functionality using real config files."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from minio import Minio
from minio.error import S3Error

from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.classes.settings import Settings
from minio_manager.resource_handler import handle_resources
from tests.conftest import requires_minio


@requires_minio
class TestMinIOManagerIntegration:
    """End-to-end tests using minio_manager classes with real configuration files."""

    @pytest.fixture(autouse=True)
    def setup_environment(self, monkeypatch):
        """Set up environment variables for integration tests."""
        # Set environment variables directly
        env_vars = {
            "MINIO_MANAGER_CLUSTER_NAME": "local-test-cluster",
            "MINIO_MANAGER_S3_ENDPOINT": "localhost:9000",
            "MINIO_MANAGER_MINIO_CONTROLLER_USER": "local-test-controller",
            "MINIO_MANAGER_SECRET_BACKEND_TYPE": "insecure-env",
            "MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY": "minioadmin",
            "MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY": "minioadmin",
            "MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES": "integration-test-,test-,demo-",
            "MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_FILE": "examples/my_service_account_policy.json"
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
    
    def parse_resources_safely(self, resources_file: str):
        """Parse resources while handling sys.exit gracefully."""
        cluster_resources = ClusterResources()
        
        # Patch sys.exit to raise an exception instead
        with patch('sys.exit') as mock_exit:
            try:
                cluster_resources.parse_resources(resources_file)
                return cluster_resources
            except Exception as e:
                if mock_exit.called:
                    # Get the exit code
                    exit_code = mock_exit.call_args[0][0] if mock_exit.call_args[0] else 1
                    pytest.fail(f"Resource parsing failed with sys.exit({exit_code}): {e}")
                else:
                    raise e

    def cleanup_integration_buckets(self, minio_client: Minio):
        """Clean up all integration test buckets."""
        bucket_names = [
            "integration-test-default-bucket",
            "integration-test-custom-bucket", 
            "integration-test-minimal-bucket"
        ]
        
        for bucket_name in bucket_names:
            try:
                if minio_client.bucket_exists(bucket_name):
                    # Remove all objects and versions
                    try:
                        objects = minio_client.list_objects(bucket_name, recursive=True)
                        for obj in objects:
                            minio_client.remove_object(bucket_name, obj.object_name)
                    except Exception:
                        pass
                    
                    # Remove bucket policies and lifecycle
                    try:
                        minio_client.delete_bucket_policy(bucket_name)
                    except Exception:
                        pass
                    try:
                        minio_client.delete_bucket_lifecycle(bucket_name)
                    except Exception:
                        pass
                    
                    # Remove bucket
                    minio_client.remove_bucket(bucket_name)
            except Exception as e:
                print(f"Error cleaning up bucket {bucket_name}: {e}")

    def test_initial_resource_deployment(self, minio_client: Minio):
        """Test initial deployment of resources using minio_manager."""
        # Clean up any existing test buckets
        self.cleanup_integration_buckets(minio_client)

        # Parse and apply the initial resources
        resources_file = "tests/fixtures/test_resources.yaml"  # Use the existing test file in fixtures
        cluster_resources = self.parse_resources_safely(resources_file)        # Apply resources using minio_manager
        handle_resources(cluster_resources)
        
        # Verify bucket creation and configuration
        # 1. Verify integration-test-default-bucket
        assert minio_client.bucket_exists("integration-test-default-bucket")
        
        # Should have 30-day lifecycle policy
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-default-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkerAndOldVersionsAfter30Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 30
        
        # Should have versioning enabled
        versioning = minio_client.get_bucket_versioning("integration-test-default-bucket")
        assert versioning.status == "Enabled"
        
        # Should have read-only bucket policy
        policy_str = minio_client.get_bucket_policy("integration-test-default-bucket")
        policy = json.loads(policy_str)
        assert any("s3:GetObject" in stmt.get("Action", []) for stmt in policy["Statement"])
        
        # 2. Verify integration-test-custom-bucket
        assert minio_client.bucket_exists("integration-test-custom-bucket")
        
        # Should have 90-day lifecycle policy
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-custom-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkersAfter90Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 90
        
        # Should have versioning suspended
        versioning = minio_client.get_bucket_versioning("integration-test-custom-bucket")
        assert versioning.status == "Suspended"
        
        # Should have full access bucket policy
        policy_str = minio_client.get_bucket_policy("integration-test-custom-bucket")
        policy = json.loads(policy_str)
        # Check for full access actions (PutObject, DeleteObject, etc.)
        actions = set()
        for stmt in policy["Statement"]:
            actions.update(stmt.get("Action", []))
        assert "s3:PutObject" in actions
        assert "s3:DeleteObject" in actions
        
        # 3. Verify integration-test-minimal-bucket
        assert minio_client.bucket_exists("integration-test-minimal-bucket")
        
        # Should have default lifecycle policy (30 days) applied since no explicit policy
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-minimal-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkerAndOldVersionsAfter30Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 30
        
        # Should not have bucket policy initially  
        try:
            minio_client.get_bucket_policy("integration-test-minimal-bucket")
            assert False, "Expected no bucket policy"
        except S3Error as e:
            assert e.code == 'NoSuchBucketPolicy'

    def test_resource_updates_and_idempotency(self, minio_client: Minio):
        """Test updating resources and verifying idempotent behavior."""
        # Ensure initial state exists (run first deployment)
        self.test_initial_resource_deployment(minio_client)

        # Apply the updated resources configuration
        updated_resources_file = "tests/fixtures/test_resources_updated.yaml"  # Use the existing updated file in fixtures
        cluster_resources = self.parse_resources_safely(updated_resources_file)        # Apply updated resources using minio_manager
        handle_resources(cluster_resources)
        
        # Verify changes were applied correctly
        
        # 1. integration-test-default-bucket: lifecycle policy should be updated (30->60 days)
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-default-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkerAndOldVersionsAfter60Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 60
        
        # Bucket policy should change from read-only to full access
        policy_str = minio_client.get_bucket_policy("integration-test-default-bucket")
        policy = json.loads(policy_str)
        # Check for full access actions (PutObject, DeleteObject indicate write permissions)
        actions = set()
        for stmt in policy["Statement"]:
            actions.update(stmt.get("Action", []))
        assert "s3:PutObject" in actions
        assert "s3:DeleteObject" in actions
        
        # 2. integration-test-custom-bucket: lifecycle policy should remain 90 days (no change)
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-custom-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkersAfter90Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 90
        
        # Bucket policy should change from full access to read-only
        policy_str = minio_client.get_bucket_policy("integration-test-custom-bucket")
        policy = json.loads(policy_str)
        # Check for read-only actions (GetObject but not PutObject/DeleteObject)
        actions = set()
        for stmt in policy["Statement"]:
            actions.update(stmt.get("Action", []))
        assert "s3:GetObject" in actions
        assert "s3:PutObject" not in actions
        assert "s3:DeleteObject" not in actions
        
        # 3. integration-test-minimal-bucket: should now have lifecycle policy (new: 30 days)
        lifecycle = minio_client.get_bucket_lifecycle("integration-test-minimal-bucket")
        assert len(lifecycle.rules) == 1
        assert lifecycle.rules[0].rule_id == "ExpireDeleteMarkerAndOldVersionsAfter30Days"
        assert lifecycle.rules[0].noncurrent_version_expiration.noncurrent_days == 30
        
        # Should now have versioning enabled (was not set before)
        versioning = minio_client.get_bucket_versioning("integration-test-minimal-bucket")
        assert versioning.status == "Enabled"
        
        # Should now have a bucket policy (new)
        policy_str = minio_client.get_bucket_policy("integration-test-minimal-bucket")
        policy = json.loads(policy_str)
        assert any("s3:GetObject" in stmt.get("Action", []) for stmt in policy["Statement"])

    def test_idempotent_reapplication(self, minio_client: Minio):
        """Test that applying the same configuration multiple times is idempotent."""
        # Start with updated configuration
        self.test_resource_updates_and_idempotency(minio_client)
        
        # Store current state
        default_lifecycle_before = minio_client.get_bucket_lifecycle("integration-test-default-bucket")
        default_policy_before = minio_client.get_bucket_policy("integration-test-default-bucket")
        minimal_versioning_before = minio_client.get_bucket_versioning("integration-test-minimal-bucket")
        
        # Verify custom bucket has read-only policy 
        custom_policy_before = minio_client.get_bucket_policy("integration-test-custom-bucket")
        
        # Apply the same configuration again
        updated_resources_file = "tests/fixtures/test_resources_updated.yaml"  # Use the existing file in fixtures
        cluster_resources = self.parse_resources_safely(updated_resources_file)
        handle_resources(cluster_resources)
        
        # Verify state is identical (idempotent)
        default_lifecycle_after = minio_client.get_bucket_lifecycle("integration-test-default-bucket")
        default_policy_after = minio_client.get_bucket_policy("integration-test-default-bucket")
        minimal_versioning_after = minio_client.get_bucket_versioning("integration-test-minimal-bucket")
        
        # Verify custom bucket still has read-only policy
        custom_policy_after = minio_client.get_bucket_policy("integration-test-custom-bucket")
        
        # Compare states (should be identical)
        assert len(default_lifecycle_before.rules) == len(default_lifecycle_after.rules)
        assert (default_lifecycle_before.rules[0].rule_id == 
                default_lifecycle_after.rules[0].rule_id)
        assert (default_lifecycle_before.rules[0].noncurrent_version_expiration.noncurrent_days ==
                default_lifecycle_after.rules[0].noncurrent_version_expiration.noncurrent_days)
        
        # Compare policies (content should be functionally identical)
        policy_before = json.loads(default_policy_before)
        policy_after = json.loads(default_policy_after)
        
        # Compare the essential policy elements
        assert policy_before["Version"] == policy_after["Version"]
        assert len(policy_before["Statement"]) == len(policy_after["Statement"])
        assert policy_before["Statement"][0]["Sid"] == policy_after["Statement"][0]["Sid"]
        assert policy_before["Statement"][0]["Effect"] == policy_after["Statement"][0]["Effect"]
        assert set(policy_before["Statement"][0]["Action"]) == set(policy_after["Statement"][0]["Action"])
        assert set(policy_before["Statement"][0]["Resource"]) == set(policy_after["Statement"][0]["Resource"])
        
        # Compare versioning
        assert minimal_versioning_before.status == minimal_versioning_after.status
        
        # Compare custom bucket policies (should be identical)
        policy_before_custom = json.loads(custom_policy_before)
        policy_after_custom = json.loads(custom_policy_after)
        assert policy_before_custom["Statement"][0]["Sid"] == policy_after_custom["Statement"][0]["Sid"]
        assert set(policy_before_custom["Statement"][0]["Action"]) == set(policy_after_custom["Statement"][0]["Action"])

    def test_configuration_validation(self):
        """Test that configuration files are valid and can be parsed."""
        # Test initial configuration parsing
        resources_file = "tests/fixtures/test_resources.yaml"  # Use the existing test file in fixtures
        cluster_resources = self.parse_resources_safely(resources_file)
        
        # Verify buckets were parsed
        assert len(cluster_resources.buckets) == 3
        bucket_names = [bucket.name for bucket in cluster_resources.buckets]
        assert "integration-test-default-bucket" in bucket_names
        assert "integration-test-custom-bucket" in bucket_names
        assert "integration-test-minimal-bucket" in bucket_names
        
        # Verify service accounts were parsed (none in test config)
        assert len(cluster_resources.service_accounts) == 0
        
        # Test updated configuration parsing
        updated_resources_file = "tests/fixtures/test_resources_updated.yaml"  # Use the existing file in fixtures
        cluster_resources_updated = self.parse_resources_safely(updated_resources_file)
        
        # Verify updated buckets
        assert len(cluster_resources_updated.buckets) == 3
        
        # Verify required lifecycle policy files exist
        lifecycle_files = [
            "default_lifecycle_30_days.json",
            "custom_lifecycle_90_days.json", 
            "updated_lifecycle_60_days.json"
        ]
        
        for lifecycle_file in lifecycle_files:
            lifecycle_path = Path(__file__).parent / "fixtures" / "lifecycle_policies" / lifecycle_file
            assert lifecycle_path.exists(), f"Lifecycle file not found: {lifecycle_path}"
        
        # Verify required bucket policy files exist
        policy_files = [
            "read_only_policy.json",
            "full_access_policy.json"
        ]
        
        for policy_file in policy_files:
            policy_path = Path(__file__).parent / "fixtures" / "bucket_policies" / policy_file
            assert policy_path.exists(), f"Policy file not found: {policy_path}"

    def test_cleanup_and_teardown(self, minio_client: Minio):
        """Test complete cleanup of all integration test resources."""
        # Ensure we have resources deployed
        self.test_resource_updates_and_idempotency(minio_client)
        
        # Perform cleanup
        self.cleanup_integration_buckets(minio_client)
        
        # Verify all buckets are removed
        bucket_names = [
            "integration-test-default-bucket",
            "integration-test-custom-bucket",
            "integration-test-minimal-bucket"
        ]
        
        for bucket_name in bucket_names:
            assert not minio_client.bucket_exists(bucket_name), f"Bucket {bucket_name} should not exist after cleanup"
