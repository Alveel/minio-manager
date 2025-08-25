"""End-to-end integration tests for MinIO Manager functionality using real config files."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from minio import Minio
from minio.error import S3Error

from minio_manager.classes.minio_resources import Bucket, BucketPolicy
from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.policy_handler import get_existing_bucket_policy
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
            "MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_FILE": "examples/my_service_account_policy.json",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

    def parse_resources_safely(self, resources_file: str):
        """Parse resources while handling sys.exit gracefully."""
        cluster_resources = ClusterResources()

        # Patch sys.exit to raise an exception instead
        with patch("sys.exit") as mock_exit:
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
            "integration-test-minimal-bucket",
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
        cluster_resources = self.parse_resources_safely(resources_file)  # Apply resources using minio_manager
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

        # Should have default bucket policy applied since no explicit policy is configured
        policy_str = minio_client.get_bucket_policy("integration-test-minimal-bucket")
        policy = json.loads(policy_str)
        # Verify it contains the expected elements from our default policy
        assert "Statement" in policy
        assert len(policy["Statement"]) > 0
        # The default policy should allow basic operations for authenticated users
        actions = set()
        for stmt in policy["Statement"]:
            if stmt.get("Effect") == "Allow":
                actions.update(stmt.get("Action", []))
        assert "s3:GetObject" in actions or "s3:*" in actions

    def test_resource_updates_and_idempotency(self, minio_client: Minio):
        """Test updating resources and verifying idempotent behavior."""
        # Ensure initial state exists (run first deployment)
        self.test_initial_resource_deployment(minio_client)

        # Apply the updated resources configuration
        updated_resources_file = (
            "tests/fixtures/test_resources_updated.yaml"  # Use the existing updated file in fixtures
        )
        cluster_resources = self.parse_resources_safely(
            updated_resources_file
        )  # Apply updated resources using minio_manager
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
        assert default_lifecycle_before.rules[0].rule_id == default_lifecycle_after.rules[0].rule_id
        assert (
            default_lifecycle_before.rules[0].noncurrent_version_expiration.noncurrent_days
            == default_lifecycle_after.rules[0].noncurrent_version_expiration.noncurrent_days
        )

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
            "updated_lifecycle_60_days.json",
        ]

        for lifecycle_file in lifecycle_files:
            lifecycle_path = Path(__file__).parent / "fixtures" / "lifecycle_policies" / lifecycle_file
            assert lifecycle_path.exists(), f"Lifecycle file not found: {lifecycle_path}"

        # Verify required bucket policy files exist
        policy_files = ["read_only_policy.json", "full_access_policy.json"]

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
            "integration-test-minimal-bucket",
        ]

        for bucket_name in bucket_names:
            assert not minio_client.bucket_exists(bucket_name), f"Bucket {bucket_name} should not exist after cleanup"

    def test_default_bucket_policy_application(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test that default bucket policies are applied when no explicit policy is specified."""
        # Create a single bucket without any explicit policy
        bucket = Bucket(name=test_bucket_name)
        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []  # No explicit policies
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        handle_resources(resources)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify default policy was applied
        bucket_policy = get_existing_bucket_policy(test_bucket_name)
        assert bucket_policy is not None, "Default bucket policy should be applied"

        # Verify policy structure
        assert "Statement" in bucket_policy
        assert len(bucket_policy["Statement"]) > 0

        # Verify it allows basic authenticated operations (from our test default policy)
        actions = set()
        for stmt in bucket_policy["Statement"]:
            if stmt.get("Effect") == "Allow":
                actions.update(stmt.get("Action", []))
        assert any(action in actions for action in ["s3:GetObject", "s3:PutObject", "s3:ListBucket"])

    def test_explicit_policy_overrides_default(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test that explicit bucket policies override the default policy."""
        # Create bucket with explicit policy
        bucket = Bucket(name=test_bucket_name)
        explicit_policy = BucketPolicy(
            bucket=test_bucket_name, policy_file="examples/bucket_policies/my_default_bucket_policy.json"
        )

        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = [explicit_policy]
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        handle_resources(resources)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify explicit policy was applied (not default)
        policy_str = minio_client.get_bucket_policy(test_bucket_name)
        policy = json.loads(policy_str)

        # The explicit policy should have IP-based restrictions
        statements = policy.get("Statement", [])
        ip_conditions_found = any(
            "Condition" in stmt and "NotIpAddress" in stmt.get("Condition", {}) for stmt in statements
        )
        assert (
            ip_conditions_found
        ), "Explicit policy should contain IP-based conditions, proving it overrode the default"

    def test_no_default_bucket_policy_configured(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test that when no default bucket policy is configured, buckets without explicit policies remain policy-free."""
        # Create bucket without explicit policy, but with no default policy configured
        bucket = Bucket(name=test_bucket_name)
        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []  # No explicit policies
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        # Mock settings in both modules to have no default bucket policy
        with (
            patch("minio_manager.resource_handler.settings") as mock_settings_resource,
            patch("minio_manager.policy_handler.settings") as mock_settings_policy,
        ):

            mock_settings_resource.default_bucket_policy_file = None  # No default policy
            mock_settings_policy.default_bucket_policy_file = None  # No default policy

            handle_resources(resources)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify no bucket policy was applied
        try:
            minio_client.get_bucket_policy(test_bucket_name)
            assert False, "Expected no bucket policy when no default is configured"
        except S3Error as e:
            assert e.code == "NoSuchBucketPolicy", f"Expected NoSuchBucketPolicy, got {e.code}"

    def test_service_account_auto_creation(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test that service accounts are automatically created for buckets when enabled."""
        # Create bucket which should trigger service account creation
        bucket = Bucket(name=test_bucket_name)
        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        handle_resources(resources)

        # Force secrets backend to save changes to file
        from minio_manager.classes.secrets import secrets

        if secrets.backend_dirty and secrets.backend_type == "yaml":
            from pathlib import Path

            import yaml

            with Path(secrets.backend_path).open("w") as f:
                yaml.safe_dump(secrets.backend, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify service account was created by checking credentials in secret backend
        from pathlib import Path

        import yaml

        secrets_file = Path("tests/fixtures/testsecrets-insecure.yaml")
        assert secrets_file.exists(), "Secret backend file should exist"

        with open(secrets_file) as f:
            secrets_data = yaml.safe_load(f) or {}

        # Service account should be stored with bucket name
        assert test_bucket_name in secrets_data, f"Service account '{test_bucket_name}' should be created and stored"

        service_account_data = secrets_data[test_bucket_name]
        assert "access_key" in service_account_data, "Access key should be stored"
        assert "secret_key" in service_account_data, "Secret key should be stored"
        assert len(service_account_data["access_key"]) > 0, "Access key should not be empty"

    def test_service_account_credentials_in_secret_backend(
        self, minio_client: Minio, test_bucket_name: str, cleanup_bucket
    ):
        """Test that service account credentials are properly stored in the secret backend."""
        from pathlib import Path

        import yaml

        # Create bucket which should trigger service account creation and credential storage
        bucket = Bucket(name=test_bucket_name)
        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        handle_resources(resources)

        # Force secrets backend to save changes to file
        from minio_manager.classes.secrets import secrets

        if secrets.backend_dirty and secrets.backend_type == "yaml":
            with Path(secrets.backend_path).open("w") as f:
                yaml.safe_dump(secrets.backend, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Check that credentials were written to secret backend
        secrets_file = Path("tests/fixtures/testsecrets-insecure.yaml")
        assert secrets_file.exists(), "Secret backend file should exist"

        with open(secrets_file) as f:
            secrets_data = yaml.safe_load(f) or {}

        # Verify service account credentials are stored
        assert (
            test_bucket_name in secrets_data
        ), f"Service account '{test_bucket_name}' credentials should be in secrets backend"

        service_account_data = secrets_data[test_bucket_name]
        assert "access_key" in service_account_data, "Access key should be stored"
        assert "secret_key" in service_account_data, "Secret key should be stored"

        # Verify the stored data makes sense
        assert len(service_account_data["access_key"]) > 0, "Access key should not be empty"
        assert len(service_account_data["secret_key"]) > 0, "Secret key should not be empty"

        # Verify credentials are actually functional by testing with MinIO client
        test_client = Minio(
            "localhost:9000",
            access_key=service_account_data["access_key"],
            secret_key=service_account_data["secret_key"],
            secure=False,
        )

        # Service account should be able to access its bucket
        assert test_client.bucket_exists(test_bucket_name), "Service account should be able to access its bucket"

    def test_explicit_service_account_creation(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creation of explicitly configured service accounts."""
        from minio_manager.classes.minio_resources import ServiceAccount

        # Create bucket and explicit service account
        bucket = Bucket(name=test_bucket_name)
        service_account = ServiceAccount(name=f"{test_bucket_name}-explicit")

        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []
        resources.service_accounts = [service_account]
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        handle_resources(resources)

        # Force secrets backend to save changes to file
        from minio_manager.classes.secrets import secrets

        if secrets.backend_dirty and secrets.backend_type == "yaml":
            from pathlib import Path

            import yaml

            with Path(secrets.backend_path).open("w") as f:
                yaml.safe_dump(secrets.backend, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Verify bucket exists
        assert minio_client.bucket_exists(test_bucket_name)

        # Verify both auto-created and explicit service accounts by checking secret backend
        from pathlib import Path

        import yaml

        secrets_file = Path("tests/fixtures/testsecrets-insecure.yaml")
        assert secrets_file.exists(), "Secret backend file should exist"

        with open(secrets_file) as f:
            secrets_data = yaml.safe_load(f) or {}

        # Auto-created account (same name as bucket)
        assert test_bucket_name in secrets_data, f"Auto-created service account '{test_bucket_name}' should exist"

        # Explicitly created account
        explicit_name = f"{test_bucket_name}-explicit"
        assert explicit_name in secrets_data, f"Explicit service account '{explicit_name}' should exist"

    def test_lifecycle_policy_120_days_expire_integration(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test end-to-end integration with ExpireCurrentAfter120DaysAndDelete.json lifecycle policy."""
        # Verify MinIO connectivity first
        try:
            buckets = minio_client.list_buckets()
            print(f"MinIO accessible, found {len(buckets)} existing buckets")
        except Exception as e:
            pytest.fail(f"MinIO server not accessible: {e}")
        
        # Create bucket with the specific lifecycle policy that's causing production issues
        bucket = Bucket(name=test_bucket_name)
        bucket.create_service_account = False  # Disable service account creation for focused testing
        
        # Use the problematic lifecycle policy from fixtures
        from pathlib import Path
        from minio_manager.classes.resource_parser import ClusterResources
        
        parser = ClusterResources()
        lifecycle_file = str(Path(__file__).parent / "fixtures" / "lifecycle_policies" / "ExpireCurrentAfter120DaysAndDelete.json")
        lifecycle_config = parser.parse_bucket_lifecycle_file(lifecycle_file)
        
        assert lifecycle_config is not None, "Should be able to parse the lifecycle policy file"
        bucket.lifecycle_config = lifecycle_config
        
        # Debug: Print the parsed lifecycle config
        print(f"Parsed lifecycle config with {len(lifecycle_config.rules)} rules")
        rule = lifecycle_config.rules[0]
        print(f"Rule: {rule.rule_id}, Status: {rule.status}, Days: {rule.expiration.days if rule.expiration else 'None'}")
        
        resources = ClusterResources()
        resources.buckets = [bucket]
        resources.bucket_policies = []
        resources.service_accounts = []
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        # Debug: Check bucket name format
        print(f"Attempting to create bucket: {test_bucket_name}")
        
        # Deploy the resources - this will test end-to-end functionality
        try:
            handle_resources(resources)
            print("handle_resources completed")
        except Exception as e:
            pytest.fail(f"handle_resources failed: {e}")

        # Debug: Check if bucket exists immediately after creation
        bucket_exists_immediate = minio_client.bucket_exists(test_bucket_name)
        print(f"Bucket exists immediately after handle_resources: {bucket_exists_immediate}")
        
        # Verify bucket was created - with better error reporting
        if not minio_client.bucket_exists(test_bucket_name):
            # List all buckets to see what was actually created
            all_buckets = [b.name for b in minio_client.list_buckets()]
            pytest.fail(f"Bucket {test_bucket_name} should exist. Existing buckets: {all_buckets}")

        # Verify lifecycle policy was applied correctly
        try:
            lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
            assert len(lifecycle.rules) == 1, "Should have exactly one lifecycle rule"
            
            rule = lifecycle.rules[0]
            assert rule.rule_id == "remove-logging-after-120-day", f"Rule ID should match, got: {rule.rule_id}"
            assert rule.status == "Enabled", f"Rule should be enabled, got: {rule.status}"
            
            # Test the expiration configuration that might be causing production issues
            assert rule.expiration is not None, "Rule should have expiration configuration"
            assert rule.expiration.days == 120, f"Expiration should be 120 days, got: {rule.expiration.days}"
            
            # Test non-current version expiration
            assert rule.noncurrent_version_expiration is not None, "Rule should have non-current version expiration"
            assert rule.noncurrent_version_expiration.noncurrent_days == 30, f"Non-current expiration should be 30 days, got: {rule.noncurrent_version_expiration.noncurrent_days}"
            
        except Exception as e:
            pytest.fail(f"Failed to retrieve or validate lifecycle policy: {e}")

        # Test idempotency - apply the same configuration again
        handle_resources(resources)
        
        # Verify lifecycle policy is still correct after reapplication
        lifecycle_after_reapply = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(lifecycle_after_reapply.rules) == 1, "Should still have exactly one lifecycle rule after reapplication"
        assert lifecycle_after_reapply.rules[0].rule_id == "remove-logging-after-120-day", "Rule ID should be unchanged after reapplication"

        # Finally, register cleanup AFTER all tests are done
        cleanup_bucket(test_bucket_name)

        # Finally, register cleanup AFTER all tests are done
        cleanup_bucket(test_bucket_name)

    def test_service_account_from_resources_integration(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test creating service account from resources.yaml service_accounts section with policy verification."""
        # Verify MinIO connectivity first
        try:
            buckets = minio_client.list_buckets()
            print(f"MinIO accessible, found {len(buckets)} existing buckets")
        except Exception as e:
            pytest.fail(f"MinIO server not accessible: {e}")
        
        # Create explicit service account from service_accounts section (no bucket needed)
        from minio_manager.classes.minio_resources import ServiceAccount
        from minio_manager.classes.resource_parser import ClusterResources
        from pathlib import Path
        
        service_account_name = f"{test_bucket_name}-sa"
        user_policy_file = str(Path(__file__).parent / "fixtures" / "user_policies" / "test_service_account_policy.json")
        
        # Debug: Check if policy file exists
        policy_path = Path(user_policy_file)
        print(f"Service account policy file path: {user_policy_file}")
        print(f"Policy file exists: {policy_path.exists()}")
        if policy_path.exists():
            print(f"Policy file size: {policy_path.stat().st_size} bytes")
        
        service_account = ServiceAccount(name=service_account_name, policy_file=user_policy_file)
        
        # Set up minimal resources configuration - just the service account
        resources = ClusterResources()
        resources.buckets = []  # No buckets needed for service account creation
        resources.bucket_policies = []
        resources.service_accounts = [service_account]  # Explicit service account from resources
        resources.iam_policies = []
        resources.iam_policy_attachments = []

        print(f"Setting up integration test for service account: {service_account_name}")
        
        # Deploy the resources - this will test service account creation from resources section
        try:
            print(f"About to call handle_resources with {len(resources.service_accounts)} service accounts")
            for sa in resources.service_accounts:
                print(f"  - Service account: {sa.name}, policy_file: {sa.policy_file}")
            handle_resources(resources)
            print("Service account integration test completed successfully")
        except Exception as e:
            pytest.fail(f"handle_resources failed: {e}")

        # Force secrets backend to save changes to file
        from minio_manager.classes.secrets import secrets
        secrets.cleanup()  # This will save the backend if it's dirty

        # Verify explicit service account was created and credentials stored
        try:
            import yaml
            
            # Check secrets backend file for the service account credentials
            secrets_file = Path("tests/fixtures/testsecrets-insecure.yaml")
            assert secrets_file.exists(), "Secrets backend file should exist"
            
            with open(secrets_file) as f:
                secrets_data = yaml.safe_load(f) or {}
            
            # Service account should exist with the explicit name
            assert service_account_name in secrets_data, f"Service account '{service_account_name}' should exist in secrets"
            
            service_account_creds = secrets_data[service_account_name]
            assert "access_key" in service_account_creds, "Service account should have access_key"
            assert "secret_key" in service_account_creds, "Service account should have secret_key"
            assert len(service_account_creds["access_key"]) > 0, "Access key should not be empty"
            assert len(service_account_creds["secret_key"]) > 0, "Secret key should not be empty"
            
            print(f"✅ Service account '{service_account_name}' credentials stored: access_key={service_account_creds['access_key'][:8]}...")
            
        except Exception as e:
            pytest.fail(f"Failed to verify service account credentials: {e}")

        # Verify the service account exists in MinIO and has the correct policy
        try:
            from minio_manager.classes.client_manager import client_manager
            import json
            
            # Get the service account details from MinIO
            access_key = service_account_creds["access_key"]
            sa_info_raw = client_manager.admin.get_service_account(access_key)
            sa_info = json.loads(sa_info_raw)
            
            print(f"✅ Service account '{service_account_name}' exists in MinIO")
            print(f"  - Access Key: {access_key}")
            print(f"  - Name: {sa_info.get('name', 'Not set')}")
            print(f"  - Description: {sa_info.get('description', 'Not set')}")
            
            # Verify the policy was applied correctly
            if 'policy' in sa_info:
                applied_policy = json.loads(sa_info['policy'])
                
                # Load the expected policy from file
                with open(user_policy_file) as f:
                    expected_policy = json.load(f)
                
                print(f"✅ Service account has policy attached")
                
                # Instead of exact comparison, verify key policy components
                applied_statements = applied_policy.get('Statement', [])
                expected_statements = expected_policy.get('Statement', [])
                
                assert len(applied_statements) == len(expected_statements), f"Should have {len(expected_statements)} policy statements"
                print(f"✅ Service account policy has correct number of statements: {len(applied_statements)}")
                
                # Check that all expected actions and resources are present
                all_applied_actions = set()
                all_applied_resources = set()
                
                for stmt in applied_statements:
                    actions = stmt.get('Action', [])
                    resources = stmt.get('Resource', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    if isinstance(resources, str):
                        resources = [resources]
                    all_applied_actions.update(actions)
                    all_applied_resources.update(resources)
                
                all_expected_actions = set()
                all_expected_resources = set()
                
                for stmt in expected_statements:
                    actions = stmt.get('Action', [])
                    resources = stmt.get('Resource', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    if isinstance(resources, str):
                        resources = [resources]
                    all_expected_actions.update(actions)
                    all_expected_resources.update(resources)
                
                # Verify all expected actions are present
                missing_actions = all_expected_actions - all_applied_actions
                assert not missing_actions, f"Missing expected actions: {missing_actions}"
                print(f"✅ Service account policy contains all expected actions: {sorted(all_applied_actions)}")
                
                # For resources, be more flexible since MinIO may modify them
                print(f"Applied resources: {sorted(all_applied_resources)}")
                print(f"Expected resources: {sorted(all_expected_resources)}")
                
                # Check for the specific resources we care about (not all, since MinIO may modify "*")
                important_resources = {
                    "arn:aws:s3:::test-bucket-*",
                    "arn:aws:s3:::test-bucket-*/*"
                }
                
                missing_important_resources = important_resources - all_applied_resources
                assert not missing_important_resources, f"Missing important resources: {missing_important_resources}"
                print(f"✅ Service account policy contains all important resources")
                
                # Verify specific key permissions
                assert "s3:ListBucket" in all_applied_actions, "Should have ListBucket permission"
                assert "s3:CreateBucket" in all_applied_actions, "Should have CreateBucket permission"
                assert "s3:GetObject" in all_applied_actions, "Should have GetObject permission"
                assert "s3:PutObject" in all_applied_actions, "Should have PutObject permission"
                assert "s3:ListAllMyBuckets" in all_applied_actions, "Should have ListAllMyBuckets permission"
                
                # Verify specific resource patterns
                assert "arn:aws:s3:::test-bucket-*" in all_applied_resources, "Should have test-bucket-* bucket permissions"
                assert "arn:aws:s3:::test-bucket-*/*" in all_applied_resources, "Should have test-bucket-*/* object permissions"
                
                print(f"✅ Service account policy contains all expected permissions and resources")
                
            else:
                pytest.fail("Service account should have a policy attached")
            
        except Exception as e:
            pytest.fail(f"Failed to verify service account policy: {e}")

        # Test basic authentication with the service account
        try:
            from minio import Minio
            
            # Create a new MinIO client using the service account credentials
            sa_client = Minio(
                endpoint="localhost:9000",
                access_key=service_account_creds["access_key"],
                secret_key=service_account_creds["secret_key"],
                secure=False,
            )
            
            # Test basic operation - list buckets
            sa_buckets = sa_client.list_buckets()
            print(f"✅ Service account can authenticate and list {len(sa_buckets)} buckets")
            
        except Exception as e:
            pytest.fail(f"Service account authentication failed: {e}")

        print(f"✅ Service account integration test completed successfully")
        print(f"   - Service account '{service_account_name}' created from resources configuration")
        print(f"   - Credentials stored in secrets backend")
        print(f"   - Policy correctly applied and verified")
        print(f"   - Authentication successful")
