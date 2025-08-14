"""Test utility functions and helper classes."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from minio_manager.classes.minio_resources import Bucket, BucketPolicy, ServiceAccount
from minio_manager.utilities import normalize_policy, read_json


class TestUtilities:
    """Test utility functions."""

    def test_read_json_valid_file(self, tmp_path: Path):
        """Test reading valid JSON file."""
        test_data = {"key": "value", "number": 42}
        test_file = tmp_path / "test.json"

        with open(test_file, "w") as f:
            json.dump(test_data, f)

        result = read_json(test_file)
        assert result == test_data

    def test_read_json_nonexistent_file(self):
        """Test reading non-existent JSON file."""
        with pytest.raises(FileNotFoundError):
            read_json(Path("/nonexistent/file.json"))

    def test_read_json_invalid_json(self, tmp_path: Path):
        """Test reading invalid JSON file."""
        test_file = tmp_path / "invalid.json"

        with open(test_file, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            read_json(test_file)

    def test_normalize_policy_dict(self):
        """Test normalizing policy dictionary."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": ["arn:aws:s3:::bucket/*"]}
            ],
        }

        normalized = normalize_policy(policy)

        # Should maintain structure but ensure lists are sorted
        assert normalized["Version"] == "2012-10-17"
        assert len(normalized["Statement"]) == 1
        assert normalized["Statement"][0]["Effect"] == "Allow"
        assert normalized["Statement"][0]["Action"] == ["s3:GetObject", "s3:PutObject"]

    def test_normalize_policy_with_nested_lists(self):
        """Test normalizing policy with nested lists."""
        policy = {
            "Statement": [
                {
                    "Action": ["s3:PutObject", "s3:GetObject"],  # Unsorted
                    "Resource": ["arn:aws:s3:::bucket2/*", "arn:aws:s3:::bucket1/*"],  # Unsorted
                    "Condition": {"IpAddress": {"aws:SourceIp": ["10.0.0.0/8", "192.168.1.0/24"]}},  # Unsorted
                }
            ]
        }

        normalized = normalize_policy(policy)

        # Lists should be sorted
        assert normalized["Statement"][0]["Action"] == ["s3:GetObject", "s3:PutObject"]
        assert normalized["Statement"][0]["Resource"] == ["arn:aws:s3:::bucket1/*", "arn:aws:s3:::bucket2/*"]
        assert normalized["Statement"][0]["Condition"]["IpAddress"]["aws:SourceIp"] == ["10.0.0.0/8", "192.168.1.0/24"]

    def test_normalize_policy_with_non_comparable_items(self):
        """Test normalizing policy with non-comparable items."""
        policy = {"Statement": [{"Mixed": [{"key": "value"}, "string", 42]}]}  # Mixed types

        # Should not raise error, even with non-comparable items
        normalized = normalize_policy(policy)
        assert "Statement" in normalized
        assert len(normalized["Statement"]) == 1


class TestMinioResourceClasses:
    """Test MinIO resource classes."""

    def test_bucket_initialization_valid_name(self):
        """Test Bucket initialization with valid name."""
        bucket = Bucket(name="valid-bucket-name")

        assert bucket.name == "valid-bucket-name"
        assert bucket.create_service_account is True  # Default from settings
        assert bucket.versioning is None
        assert bucket.lifecycle_config is None

    def test_bucket_initialization_with_options(self):
        """Test Bucket initialization with all options."""
        from minio.lifecycleconfig import Expiration, Filter, LifecycleConfig, Rule
        from minio.versioningconfig import VersioningConfig

        versioning = VersioningConfig("Enabled")
        rule = Rule(
            rule_id="test",
            rule_filter=Filter(prefix=""),
            status="Enabled",
            expiration=Expiration(days=30),
        )
        lifecycle = LifecycleConfig([rule])

        bucket = Bucket(
            name="test-bucket", create_service_account=False, versioning=versioning, lifecycle_config=lifecycle
        )

        assert bucket.name == "test-bucket"
        assert bucket.create_service_account is False
        assert bucket.versioning.status == "Enabled"
        assert bucket.lifecycle_config.rules[0].rule_id == "test"

    def test_bucket_policy_initialization(self):
        """Test BucketPolicy initialization."""
        policy = BucketPolicy(bucket="test-bucket", policy_file="/path/to/policy.json")

        assert policy.bucket == "test-bucket"
        assert policy.policy_file == "/path/to/policy.json"

    def test_service_account_initialization_basic(self):
        """Test ServiceAccount initialization with basic parameters."""
        sa = ServiceAccount(name="test-service-account", description="Test SA")

        assert sa.name == "test-service-account"
        assert sa.description == "test-service-account - Test SA"
        assert sa.full_name == "test-service-account"
        assert sa.access_key is None
        assert sa.secret_key is None
        assert sa.policy is None
        assert sa.policy_file is None

    def test_service_account_initialization_with_credentials(self):
        """Test ServiceAccount initialization with credentials."""
        sa = ServiceAccount(name="test-sa", description="Test", access_key="TESTKEY123", secret_key="testsecret456")

        assert sa.access_key == "TESTKEY123"
        assert sa.secret_key == "testsecret456"

    def test_service_account_initialization_with_policy_dict(self):
        """Test ServiceAccount initialization with policy dictionary."""
        policy_dict = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::bucket/*"]}],
        }

        sa = ServiceAccount(name="test-sa", description="Test", policy=policy_dict)

        assert sa.policy == policy_dict

    def test_service_account_name_truncation(self):
        """Test ServiceAccount name truncation to 32 characters."""
        long_name = "a" * 50  # 50 characters
        sa = ServiceAccount(name=long_name, description="Test")

        assert len(sa.name) == 32
        assert sa.name == "a" * 32
        assert sa.full_name == long_name

    def test_service_account_with_policy_file(self, tmp_path: Path):
        """Test ServiceAccount initialization with policy file."""
        policy_dict = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::bucket/*"]}],
        }

        policy_file = tmp_path / "sa_policy.json"
        with open(policy_file, "w") as f:
            json.dump(policy_dict, f)

        sa = ServiceAccount(name="test-sa", description="Test", policy_file=policy_file)

        assert sa.policy_file == policy_file
        assert sa.policy == policy_dict

    def test_service_account_with_nonexistent_policy_file(self, caplog):
        """Test ServiceAccount initialization with non-existent policy file."""
        with patch("minio_manager.classes.minio_resources.logger") as mock_logger:
            sa = ServiceAccount(name="test-sa", description="Test", policy_file="/nonexistent/policy.json")

            assert sa.policy_file == Path("/nonexistent/policy.json")
            assert sa.policy is None
            mock_logger.error.assert_called_once()

    def test_service_account_policy_file_as_string(self, tmp_path: Path):
        """Test ServiceAccount with policy file as string path."""
        policy_dict = {"Version": "2012-10-17", "Statement": []}
        policy_file = tmp_path / "policy.json"

        with open(policy_file, "w") as f:
            json.dump(policy_dict, f)

        sa = ServiceAccount(name="test-sa", description="Test", policy_file=str(policy_file))  # Pass as string

        assert sa.policy_file == policy_file  # Should be converted to Path
        assert sa.policy == policy_dict
