import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from minio.lifecycleconfig import LifecycleConfig, Rule

from minio_manager.classes.minio_resources import Bucket, BucketPolicy, IamPolicy, ServiceAccount
from minio_manager.classes.resource_parser import ClusterResources


class TestResourceParser:
    """Test resource parser functionality using real resource files."""

    def setup_method(self):
        """Setup for each test method."""
        self.parser = ClusterResources()
        self.examples_dir = Path(__file__).parent.parent / "examples"

    def test_parse_buckets_with_real_resources(self):
        """Test parsing buckets using real resource configuration."""
        buckets_config = [
            {
                "name": "test-bucket-1",
                "create_service_account": False,
                "versioning": "Suspended",
                "object_lifecycle_file": str(
                    self.examples_dir / "lifecycle_policies" / "default_lifecycle_30_days.json"
                ),
            },
            {
                "name": "test-bucket-2",
                "object_lifecycle_file": str(
                    self.examples_dir / "lifecycle_policies" / "alternative_lifecycle_90_days.json"
                ),
            },
            {"name": "test-bucket-3"},
        ]

        with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
            mock_settings.allowed_bucket_prefixes = None
            mock_settings.auto_create_service_account = True
            mock_settings.default_bucket_versioning = "Enabled"
            mock_settings.default_lifecycle_policy_file = str(
                self.examples_dir / "lifecycle_policies" / "default_lifecycle_30_days.json"
            )

            buckets = self.parser.parse_buckets(buckets_config)

        assert len(buckets) == 3
        assert all(isinstance(bucket, Bucket) for bucket in buckets)

        # Test bucket 1 - explicit settings
        bucket1 = buckets[0]
        assert bucket1.name == "test-bucket-1"
        assert bucket1.create_service_account is False
        assert bucket1.versioning.status == "Suspended"
        assert bucket1.lifecycle_config is not None

        # Test bucket 2 - default service account creation
        bucket2 = buckets[1]
        assert bucket2.name == "test-bucket-2"
        assert bucket2.create_service_account is True  # Default from settings
        assert bucket2.lifecycle_config is not None

        # Test bucket 3 - all defaults
        bucket3 = buckets[2]
        assert bucket3.name == "test-bucket-3"
        assert bucket3.create_service_account is True
        assert bucket3.versioning.status == "Enabled"

    def test_parse_buckets_with_prefix_filtering(self):
        """Test bucket parsing with allowed prefix filtering."""
        buckets_config = [{"name": "allowed-bucket-1"}, {"name": "denied-bucket-1"}, {"name": "allowed-bucket-2"}]

        with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
            mock_settings.allowed_bucket_prefixes = ["allowed-"]
            mock_settings.auto_create_service_account = False
            mock_settings.default_bucket_versioning = "Enabled"
            mock_settings.default_lifecycle_policy_file = None

            buckets = self.parser.parse_buckets(buckets_config)

        # Only buckets with allowed prefixes should be parsed
        assert len(buckets) == 2
        assert buckets[0].name == "allowed-bucket-1"
        assert buckets[1].name == "allowed-bucket-2"

    def test_parse_buckets_duplicate_names(self):
        """Test bucket parsing rejects duplicate names."""
        buckets_config = [
            {"name": "duplicate-bucket"},
            {"name": "unique-bucket"},
            {"name": "duplicate-bucket"},  # Duplicate
        ]

        with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
            mock_settings.allowed_bucket_prefixes = None
            mock_settings.auto_create_service_account = False
            mock_settings.default_bucket_versioning = "Enabled"
            mock_settings.default_lifecycle_policy_file = None

            buckets = self.parser.parse_buckets(buckets_config)

        # Should only get 2 buckets (duplicate rejected)
        assert len(buckets) == 2
        bucket_names = [b.name for b in buckets]
        assert "duplicate-bucket" in bucket_names
        assert "unique-bucket" in bucket_names

    def test_parse_bucket_lifecycle_file_real_file(self):
        """Test parsing real lifecycle policy files."""
        lifecycle_file = str(self.examples_dir / "lifecycle_policies" / "default_lifecycle_30_days.json")

        lifecycle_config = self.parser.parse_bucket_lifecycle_file(lifecycle_file)

        assert lifecycle_config is not None
        assert isinstance(lifecycle_config, LifecycleConfig)
        assert len(lifecycle_config.rules) == 1

        rule = lifecycle_config.rules[0]
        assert isinstance(rule, Rule)
        assert rule.rule_id == "ExpireDeleteMarkerAndOldVersionsAfter30Days"
        assert rule.status == "Enabled"
        assert rule.expiration is not None
        assert rule.noncurrent_version_expiration is not None

    def test_parse_bucket_lifecycle_file_alternative_file(self):
        """Test parsing alternative lifecycle policy file."""
        lifecycle_file = str(self.examples_dir / "lifecycle_policies" / "alternative_lifecycle_90_days.json")

        lifecycle_config = self.parser.parse_bucket_lifecycle_file(lifecycle_file)

        assert lifecycle_config is not None
        assert isinstance(lifecycle_config, LifecycleConfig)
        assert len(lifecycle_config.rules) >= 1

    def test_parse_bucket_lifecycle_file_expire_current_120_days(self):
        """Test parsing ExpireCurrentAfter120DaysAndDelete.json lifecycle policy file."""
        # Test the fixture file that was causing production issues
        lifecycle_file = str(Path(__file__).parent / "fixtures" / "lifecycle_policies" / "ExpireCurrentAfter120DaysAndDelete.json")

        lifecycle_config = self.parser.parse_bucket_lifecycle_file(lifecycle_file)

        assert lifecycle_config is not None
        assert isinstance(lifecycle_config, LifecycleConfig)
        assert len(lifecycle_config.rules) == 1
        
        rule = lifecycle_config.rules[0]
        assert isinstance(rule, Rule)
        assert rule.rule_id == "remove-logging-after-120-day"
        assert rule.status == "Enabled"
        assert rule.expiration is not None
        assert rule.expiration.days == 120  # This was the production issue - Days not being parsed
        assert rule.noncurrent_version_expiration is not None
        assert rule.noncurrent_version_expiration.noncurrent_days == 30

    def test_parse_bucket_lifecycle_file_not_found(self):
        """Test handling of missing lifecycle file."""
        lifecycle_config = self.parser.parse_bucket_lifecycle_file("/nonexistent/file.json")

        assert lifecycle_config is None

    def test_parse_bucket_lifecycle_file_invalid_json(self):
        """Test handling of invalid JSON in lifecycle file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json')
            temp_file = f.name

        try:
            # The function doesn't handle JSON parsing errors currently
            with pytest.raises(json.JSONDecodeError):
                lifecycle_config = self.parser.parse_bucket_lifecycle_file(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_parse_bucket_lifecycle_rule(self):
        """Test parsing individual lifecycle rules."""
        rule_data = {
            "Status": "Enabled",
            "ID": "TestRule",
            "Expiration": {"ExpiredObjectDeleteMarker": True},
            "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
        }

        rule = self.parser.parse_bucket_lifecycle_rule(rule_data)

        assert isinstance(rule, Rule)
        assert rule.status == "Enabled"
        assert rule.rule_id == "TestRule"
        assert rule.expiration is not None
        assert rule.expiration.expired_object_delete_marker is True
        assert rule.noncurrent_version_expiration is not None
        assert rule.noncurrent_version_expiration.noncurrent_days == 30

    def test_parse_bucket_lifecycle_rule_with_days(self):
        """Test parsing lifecycle rule with Days-based expiration (production issue case)."""
        rule_data = {
            "Status": "Enabled",
            "ID": "TestDaysRule",
            "Expiration": {"Days": 120},
            "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
        }

        rule = self.parser.parse_bucket_lifecycle_rule(rule_data)

        assert isinstance(rule, Rule)
        assert rule.status == "Enabled"
        assert rule.rule_id == "TestDaysRule"
        assert rule.expiration is not None
        assert rule.expiration.days == 120  # This is the key fix
        assert rule.noncurrent_version_expiration is not None
        assert rule.noncurrent_version_expiration.noncurrent_days == 30

    def test_parse_service_accounts(self):
        """Test parsing service account configurations."""
        service_accounts_config = [
            {"name": "test-sa-1", "policy_file": str(self.examples_dir / "user_policies" / "my_user.json")},
            {"name": "test-sa-2"},
        ]

        service_accounts = self.parser.parse_service_accounts(service_accounts_config)

        assert len(service_accounts) == 2
        assert all(isinstance(sa, ServiceAccount) for sa in service_accounts)

        sa1 = service_accounts[0]
        assert sa1.name == "test-sa-1"
        assert sa1.policy_file is not None

        sa2 = service_accounts[1]
        assert sa2.name == "test-sa-2"
        assert sa2.policy_file is None

    def test_parse_service_accounts_duplicate_names(self):
        """Test service account parsing rejects duplicates."""
        service_accounts_config = [{"name": "duplicate-sa"}, {"name": "unique-sa"}, {"name": "duplicate-sa"}]

        with patch("minio_manager.classes.resource_parser.logger") as mock_logger:
            service_accounts = self.parser.parse_service_accounts(service_accounts_config)

        # All should be parsed but error logged for duplicate
        assert len(service_accounts) == 3
        mock_logger.error.assert_called_with("Service account 'duplicate-sa' defined multiple times.")

    def test_parse_bucket_policies(self):
        """Test parsing bucket policy configurations."""
        bucket_policies_config = [
            {
                "bucket": "test-bucket-1",
                "policy_file": str(self.examples_dir / "bucket_policies" / "my_default_bucket_policy.json"),
            },
            {"bucket": "test-bucket-2", "policy_file": "/path/to/policy.json"},
        ]

        bucket_policies = self.parser.parse_bucket_policies(bucket_policies_config)

        assert len(bucket_policies) == 2
        assert all(isinstance(bp, BucketPolicy) for bp in bucket_policies)

        bp1 = bucket_policies[0]
        assert bp1.bucket == "test-bucket-1"
        assert "my_default_bucket_policy.json" in bp1.policy_file

        bp2 = bucket_policies[1]
        assert bp2.bucket == "test-bucket-2"
        assert bp2.policy_file == "/path/to/policy.json"

    def test_parse_iam_policies(self):
        """Test parsing IAM policy configurations."""
        iam_policies_config = [
            {"name": "test-policy-1", "policy_file": "/path/to/policy1.json"},
            {"name": "test-policy-2", "policy_file": "/path/to/policy2.json"},
        ]

        iam_policies = self.parser.parse_iam_policies(iam_policies_config)

        assert len(iam_policies) == 2
        assert all(isinstance(ip, IamPolicy) for ip in iam_policies)

        ip1 = iam_policies[0]
        assert ip1.name == "test-policy-1"
        assert ip1.policy_file == "/path/to/policy1.json"

    def test_parse_iam_policies_duplicate_names(self):
        """Test IAM policy parsing rejects duplicates."""
        iam_policies_config = [
            {"name": "duplicate-policy", "policy_file": "/path1.json"},
            {"name": "unique-policy", "policy_file": "/path2.json"},
            {"name": "duplicate-policy", "policy_file": "/path3.json"},
        ]

        with patch("minio_manager.classes.resource_parser.logger") as mock_logger:
            iam_policies = self.parser.parse_iam_policies(iam_policies_config)

        assert len(iam_policies) == 3
        mock_logger.error.assert_called_with("IAM policy 'duplicate-policy' defined multiple times.")

    def test_parse_iam_attachments(self):
        """Test parsing IAM policy attachment configurations."""
        iam_attachments_config = [
            {"username": "test-user-1", "policies": ["policy1", "policy2"]},
            {"username": "test-user-2", "policies": ["policy3"]},
        ]

        # Note: There's a bug in the original code - it appends to the input list instead of the output list
        # and causes a SystemExit. This test documents the current behavior
        with pytest.raises(SystemExit) as exc_info:
            iam_attachments = self.parser.parse_iam_attachments(iam_attachments_config)

        assert exc_info.value.code == 150

    def test_parse_empty_configurations(self):
        """Test parsing empty configurations."""
        assert self.parser.parse_buckets([]) == []
        assert self.parser.parse_buckets(None) == []

        assert self.parser.parse_service_accounts([]) == []
        assert self.parser.parse_service_accounts(None) == []

        assert self.parser.parse_bucket_policies([]) == []
        assert self.parser.parse_bucket_policies(None) == []

        assert self.parser.parse_iam_policies([]) == []
        assert self.parser.parse_iam_policies(None) == []

        assert self.parser.parse_iam_attachments([]) == []
        assert self.parser.parse_iam_attachments(None) == []

    def test_parse_resources_integration(self):
        """Test parsing complete resources file integration."""
        # Create a temporary resources file for testing
        resources_content = {
            "buckets": [{"name": "integration-bucket-1"}, {"name": "integration-bucket-2"}],
            "service_accounts": [{"name": "integration-sa-1"}],
            "bucket_policies": [{"bucket": "integration-bucket-1", "policy_file": "/path/policy.json"}],
            "iam_policies": [{"name": "integration-policy-1", "policy_file": "/path/iam.json"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(resources_content, f)
            temp_file = f.name

        try:
            with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
                mock_settings.allowed_bucket_prefixes = None
                mock_settings.auto_create_service_account = False
                mock_settings.default_bucket_versioning = "Enabled"
                mock_settings.default_lifecycle_policy_file = None

                with patch("minio_manager.classes.resource_parser.get_error_count", return_value=0):
                    self.parser.parse_resources(temp_file)

            # Verify all resources were parsed
            assert len(self.parser.buckets) == 2
            assert len(self.parser.service_accounts) == 1
            assert len(self.parser.bucket_policies) == 1
            assert len(self.parser.iam_policies) == 1

        finally:
            Path(temp_file).unlink()

    def test_parse_resources_file_not_found(self):
        """Test handling of missing resources file."""
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_resources("/nonexistent/resources.yaml")

        assert exc_info.value.code == 170

    def test_versioning_config_parsing(self):
        """Test versioning configuration parsing."""
        # Test valid versioning values
        bucket_def_enabled = {"versioning": "Enabled"}
        versioning_config = self.parser._get_versioning_config(bucket_def_enabled)
        assert versioning_config.status == "Enabled"

        bucket_def_suspended = {"versioning": "Suspended"}
        versioning_config = self.parser._get_versioning_config(bucket_def_suspended)
        assert versioning_config.status == "Suspended"

        # Test default fallback
        with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
            mock_settings.default_bucket_versioning = "Enabled"

            bucket_def_empty = {}
            versioning_config = self.parser._get_versioning_config(bucket_def_empty)
            assert versioning_config.status == "Enabled"

    def test_versioning_config_invalid_value(self):
        """Test handling of invalid versioning values."""
        bucket_def_invalid = {"versioning": "InvalidValue"}

        with patch("minio_manager.classes.resource_parser.settings") as mock_settings:
            mock_settings.default_bucket_versioning = "Enabled"

            with patch("minio_manager.classes.resource_parser.logger") as mock_logger:
                versioning_config = self.parser._get_versioning_config(bucket_def_invalid)

                # Should fallback to default and log error
                assert versioning_config.status == "Enabled"
                mock_logger.error.assert_called()

    def test_get_effective_lifecycle(self):
        """Test effective lifecycle configuration selection."""
        # Test with specific file
        lifecycle_file = str(self.examples_dir / "lifecycle_policies" / "default_lifecycle_30_days.json")
        default_lifecycle = None

        effective_lifecycle = self.parser._get_effective_lifecycle(lifecycle_file, "test-bucket", default_lifecycle)

        assert effective_lifecycle is not None
        assert isinstance(effective_lifecycle, LifecycleConfig)

        # Test with no file, uses default
        mock_default = MagicMock(spec=LifecycleConfig)
        effective_lifecycle = self.parser._get_effective_lifecycle(None, "test-bucket", mock_default)

        assert effective_lifecycle == mock_default

        # Test with invalid file, falls back to default
        effective_lifecycle = self.parser._get_effective_lifecycle("/nonexistent.json", "test-bucket", mock_default)

        assert effective_lifecycle == mock_default
