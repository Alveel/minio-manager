"""Tests for bucket lifecycle policy management using minio_manager functions."""

import json
from unittest.mock import Mock, patch

from minio.lifecycleconfig import Expiration, Filter, LifecycleConfig, NoncurrentVersionExpiration, Rule

from minio_manager.bucket_handler import check_bucket_lifecycle, configure_lifecycle, lifecycle_status_to_dict
from minio_manager.classes.minio_resources import Bucket


class TestLifecycleFunctions:
    """Test minio_manager lifecycle functions."""

    def test_lifecycle_status_to_dict(self):
        """Test conversion of lifecycle config to dictionary."""
        # Create a simple lifecycle configuration
        rule = Rule(
            rule_id="test-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        lifecycle_config = LifecycleConfig([rule])

        # Convert to dictionary
        result = lifecycle_status_to_dict(lifecycle_config)

        # Verify structure (uses _rules instead of rules in minio library)
        assert isinstance(result, dict)
        assert "_rules" in result
        assert len(result["_rules"]) == 1
        assert result["_rules"][0]["_rule_id"] == "test-rule"
        assert result["_rules"][0]["_status"] == "Enabled"

    def test_lifecycle_status_to_dict_with_noncurrent_version(self):
        """Test conversion with non-current version expiration."""
        rule = Rule(
            rule_id="test-noncurrent-rule",
            rule_filter=Filter(prefix=""),
            status="Enabled",
            expiration=Expiration(days=90),
            noncurrent_version_expiration=NoncurrentVersionExpiration(noncurrent_days=30),
        )
        lifecycle_config = LifecycleConfig([rule])

        result = lifecycle_status_to_dict(lifecycle_config)

        assert isinstance(result, dict)
        assert "_rules" in result
        assert len(result["_rules"]) == 1
        rule_dict = result["_rules"][0]
        assert rule_dict["_rule_id"] == "test-noncurrent-rule"
        assert rule_dict["_status"] == "Enabled"

    @patch("minio_manager.bucket_handler.client_manager")
    def test_configure_lifecycle_success(self, mock_client_manager):
        """Test successful lifecycle configuration."""
        # Setup
        mock_s3 = Mock()
        mock_client_manager.s3 = mock_s3
        mock_s3.get_bucket_lifecycle.side_effect = Exception("No lifecycle")

        bucket = Bucket(name="test-bucket")
        rule = Rule(
            rule_id="test-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        bucket.lifecycle_config = LifecycleConfig([rule])

        # Execute
        configure_lifecycle(bucket)

        # Verify
        mock_s3.delete_bucket_lifecycle.assert_called_once_with("test-bucket")
        mock_s3.set_bucket_lifecycle.assert_called_once_with("test-bucket", bucket.lifecycle_config)

    @patch("minio_manager.bucket_handler.compare_objects")
    @patch("minio_manager.bucket_handler.client_manager")
    def test_check_bucket_lifecycle_no_difference(self, mock_client_manager, mock_compare_objects):
        """Test check_bucket_lifecycle when no changes needed."""
        # Setup
        mock_s3 = Mock()
        mock_client_manager.s3 = mock_s3
        mock_compare_objects.return_value = True  # No difference

        rule = Rule(
            rule_id="test-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        lifecycle_config = LifecycleConfig([rule])

        bucket = Bucket(name="test-bucket")
        bucket.lifecycle_config = lifecycle_config

        # Mock the current lifecycle
        mock_s3.get_bucket_lifecycle.return_value = lifecycle_config

        # Execute
        result = check_bucket_lifecycle(bucket)

        # The logic is: if not lifecycle_diff means if not True, so it skips return True
        # and returns None implicitly when configurations actually match
        assert result is None

    @patch("minio_manager.bucket_handler.compare_objects")
    @patch("minio_manager.bucket_handler.client_manager")
    def test_check_bucket_lifecycle_with_difference(self, mock_client_manager, mock_compare_objects):
        """Test check_bucket_lifecycle when configurations differ."""
        # Setup
        mock_s3 = Mock()
        mock_client_manager.s3 = mock_s3
        mock_compare_objects.return_value = False  # Difference found

        # Current lifecycle
        current_rule = Rule(
            rule_id="old-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=60)
        )
        current_lifecycle = LifecycleConfig([current_rule])

        # Desired lifecycle
        desired_rule = Rule(
            rule_id="new-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        desired_lifecycle = LifecycleConfig([desired_rule])

        bucket = Bucket(name="test-bucket")
        bucket.lifecycle_config = desired_lifecycle

        mock_s3.get_bucket_lifecycle.return_value = current_lifecycle

        # Execute
        result = check_bucket_lifecycle(bucket)

        # The logic is: if not lifecycle_diff means if not False (True), so it returns True
        # when configurations differ
        assert result is True


class TestLifecycleClass:
    """Test lifecycle functionality with Bucket class."""

    def test_bucket_with_lifecycle_from_file(self, temp_lifecycle_file):
        """Test creating bucket with lifecycle from JSON file."""
        # Read lifecycle configuration from file
        with open(temp_lifecycle_file) as f:
            lifecycle_data = json.load(f)

        # Create bucket with lifecycle
        bucket = Bucket(name="test-bucket")

        # Convert JSON to LifecycleConfig object
        rules = []
        for rule_data in lifecycle_data["Rules"]:
            rule = Rule(
                rule_id=rule_data["ID"],
                rule_filter=Filter(prefix=""),
                status=rule_data["Status"],
                expiration=Expiration(days=rule_data["Expiration"]["Days"]),
                noncurrent_version_expiration=NoncurrentVersionExpiration(
                    noncurrent_days=rule_data["NoncurrentVersionExpiration"]["NoncurrentDays"]
                ),
            )
            rules.append(rule)

        bucket.lifecycle_config = LifecycleConfig(rules)

        # Verify the bucket has the lifecycle configuration
        assert bucket.lifecycle_config is not None
        assert len(bucket.lifecycle_config.rules) == 1
        rule = bucket.lifecycle_config.rules[0]
        assert rule.rule_id == "TestLifecycleRule"
        assert rule.status == "Enabled"
        assert rule.expiration.days == 30
        assert rule.noncurrent_version_expiration.noncurrent_days == 7

    def test_bucket_with_multiple_lifecycle_rules(self):
        """Test Bucket class with multiple lifecycle rules."""
        bucket = Bucket(name="test-multi-bucket")

        # Create multiple rules
        rule1 = Rule(
            rule_id="rule-1", rule_filter=Filter(prefix="logs/"), status="Enabled", expiration=Expiration(days=30)
        )
        rule2 = Rule(
            rule_id="rule-2", rule_filter=Filter(prefix="archive/"), status="Enabled", expiration=Expiration(days=365)
        )

        bucket.lifecycle_config = LifecycleConfig([rule1, rule2])

        # Verify multiple rules
        assert bucket.lifecycle_config is not None
        assert len(bucket.lifecycle_config.rules) == 2

        rule_ids = [rule.rule_id for rule in bucket.lifecycle_config.rules]
        assert "rule-1" in rule_ids
        assert "rule-2" in rule_ids


class TestLifecycleComplexScenarios:
    """Test complex lifecycle scenarios using minio_manager functions."""

    @patch("minio_manager.bucket_handler.client_manager")
    def test_lifecycle_with_error_handling(self, mock_client_manager):
        """Test lifecycle configuration with error handling."""
        # Setup
        mock_s3 = Mock()
        mock_client_manager.s3 = mock_s3
        mock_s3.get_bucket_lifecycle.side_effect = Exception("Connection error")

        bucket = Bucket(name="test-bucket")
        rule = Rule(
            rule_id="test-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        bucket.lifecycle_config = LifecycleConfig([rule])

        # Execute - should handle the error gracefully and still proceed
        configure_lifecycle(bucket)

        # Verify that despite get error, delete and set were still called
        mock_s3.delete_bucket_lifecycle.assert_called_once_with("test-bucket")
        mock_s3.set_bucket_lifecycle.assert_called_once_with("test-bucket", bucket.lifecycle_config)

    @patch("minio_manager.bucket_handler.client_manager")
    def test_lifecycle_comparison_with_different_rule_count(self, mock_client_manager):
        """Test lifecycle comparison when rule counts differ."""
        # Setup
        mock_s3 = Mock()
        mock_client_manager.s3 = mock_s3

        # Current has 1 rule
        current_rule = Rule(
            rule_id="current-rule", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        current_lifecycle = LifecycleConfig([current_rule])

        # Desired has 2 rules
        desired_rule1 = Rule(
            rule_id="rule-1", rule_filter=Filter(prefix="logs/"), status="Enabled", expiration=Expiration(days=30)
        )
        desired_rule2 = Rule(
            rule_id="rule-2", rule_filter=Filter(prefix="archive/"), status="Enabled", expiration=Expiration(days=365)
        )
        desired_lifecycle = LifecycleConfig([desired_rule1, desired_rule2])

        bucket = Bucket(name="test-bucket")
        bucket.lifecycle_config = desired_lifecycle

        mock_s3.get_bucket_lifecycle.return_value = current_lifecycle

        # Execute check_bucket_lifecycle (which only checks, doesn't update)
        result = check_bucket_lifecycle(bucket)

        # The logic is: if not lifecycle_diff means if not False (True), so it returns True
        # when configurations differ
        assert result is True
