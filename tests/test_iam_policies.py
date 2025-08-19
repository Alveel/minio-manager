"""Unit tests for IAM policy management using minio_manager functions."""

import json
from unittest.mock import patch

from minio.error import MinioAdminException

from minio_manager.classes.minio_resources import IamPolicy, IamPolicyAttachment
from minio_manager.policy_handler import handle_iam_policy, handle_iam_policy_attachments
from tests.conftest import requires_minio


@requires_minio
class TestIamPolicyFunctions:
    """Unit tests for minio_manager IAM policy functions."""

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.read_json")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_create_new(self, mock_logger, mock_read_json, mock_client_manager):
        """Test creating a new IAM policy."""
        iam_policy = IamPolicy(name="test-policy", policy_file="policy.json")

        desired_policy = {"Version": "2012-10-17", "Statement": []}
        mock_read_json.return_value = desired_policy

        # Mock policy doesn't exist
        mae_body = json.dumps({"Code": "XMinioAdminNoSuchPolicy", "Message": "Policy not found"})
        mae = MinioAdminException("Policy not found", mae_body)
        mock_client_manager.s3.policy_info.side_effect = mae

        # Mock policy creation
        mock_client_manager.admin.policy_add.return_value = None
        mock_client_manager.admin.policy_info.return_value = json.dumps(desired_policy)

        handle_iam_policy(iam_policy)

        mock_logger.info.assert_called_with("IAM policy test-policy does not exist, creating.")
        mock_client_manager.admin.policy_add.assert_called_with("test-policy", "policy.json")

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.read_json")
    @patch("minio_manager.policy_handler.compare_objects")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_update_needed(self, mock_logger, mock_compare, mock_read_json, mock_client_manager):
        """Test updating an existing IAM policy."""
        iam_policy = IamPolicy(name="test-policy", policy_file="policy.json")

        desired_policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow"}]}
        current_policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Deny"}]}

        mock_read_json.return_value = desired_policy
        mock_client_manager.s3.policy_info.return_value = json.dumps(current_policy)
        mock_compare.return_value = {"Statement": "different"}  # Policies differ

        handle_iam_policy(iam_policy)

        mock_logger.info.assert_called_with(
            "Desired IAM policy 'test-policy' does not match current policy. Updating IAM policy."
        )
        mock_client_manager.admin.policy_add.assert_called_with("test-policy", "policy.json")

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.read_json")
    @patch("minio_manager.policy_handler.compare_objects")
    def test_handle_iam_policy_already_up_to_date(self, mock_compare, mock_read_json, mock_client_manager):
        """Test when IAM policy is already up to date."""
        iam_policy = IamPolicy(name="test-policy", policy_file="policy.json")

        policy_dict = {"Version": "2012-10-17", "Statement": []}
        mock_read_json.return_value = policy_dict
        mock_client_manager.s3.policy_info.return_value = json.dumps(policy_dict)
        mock_compare.return_value = False  # No differences

        handle_iam_policy(iam_policy)

        # Should not call policy_add if policies match
        mock_client_manager.admin.policy_add.assert_not_called()

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.read_json")
    @patch("minio_manager.policy_handler.increment_error_count")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_unknown_admin_exception(
        self, mock_logger, mock_increment_error, mock_read_json, mock_client_manager
    ):
        """Test handling unknown MinioAdminException."""
        iam_policy = IamPolicy(name="test-policy", policy_file="policy.json")

        mock_read_json.return_value = {}

        # Mock unknown admin exception
        mae_body = json.dumps({"Code": "UnknownError", "Message": "Something went wrong"})
        mae = MinioAdminException("Unknown error", mae_body)
        mock_client_manager.s3.policy_info.side_effect = mae

        handle_iam_policy(iam_policy)

        mock_logger.exception.assert_called_with("An unknown exception occurred")
        mock_increment_error.assert_called_once()


@requires_minio
class TestIamPolicyAttachments:
    """Test IAM policy attachment management."""

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_attachments_single_policy(self, mock_logger, mock_client_manager):
        """Test attaching a single policy to a user."""
        user = IamPolicyAttachment(username="test-user", policies=["policy1"])

        handle_iam_policy_attachments(user)

        mock_logger.debug.assert_any_call("Handling user policy attachments for 'test-user'")
        mock_logger.debug.assert_any_call("Attaching policy 'policy1' to access key 'test-user'")
        mock_client_manager.admin.policy_set.assert_called_once_with("policy1", "test-user")

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_attachments_multiple_policies(self, mock_logger, mock_client_manager):
        """Test attaching multiple policies to a user."""
        user = IamPolicyAttachment(username="test-user", policies=["policy1", "policy2", "policy3"])

        handle_iam_policy_attachments(user)

        mock_logger.debug.assert_any_call("Handling user policy attachments for 'test-user'")

        # Check that all policies were attached
        expected_calls = [(("policy1", "test-user"),), (("policy2", "test-user"),), (("policy3", "test-user"),)]
        actual_calls = mock_client_manager.admin.policy_set.call_args_list
        assert len(actual_calls) == 3

        for expected_call in expected_calls:
            assert expected_call in actual_calls

    @patch("minio_manager.policy_handler.client_manager")
    @patch("minio_manager.policy_handler.logger")
    def test_handle_iam_policy_attachments_empty_policies(self, mock_logger, mock_client_manager):
        """Test handling user with no policies to attach."""
        user = IamPolicyAttachment(username="test-user", policies=[])

        handle_iam_policy_attachments(user)

        mock_logger.debug.assert_called_with("Handling user policy attachments for 'test-user'")
        mock_client_manager.admin.policy_set.assert_not_called()
