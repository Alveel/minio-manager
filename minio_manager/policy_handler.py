import json

from minio import S3Error
from minio.error import MinioAdminException

from minio_manager.classes.client_manager import client_manager
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import BucketPolicy, IamPolicy, IamPolicyAttachment
from minio_manager.utilities import compare_objects, increment_error_count, read_json


def handle_bucket_policy(bucket_policy: BucketPolicy):
    """
    Manage policies for buckets.

    If the policy doesn't exist, create it.
    If the policy exists, compare the desired policy with the current policy, and update if needed.

    Args:
        bucket_policy: BucketPolicy
    """
    current_policy = {}
    desired_policy = read_json(bucket_policy.policy_file)
    desired_policy_json = json.dumps(desired_policy)

    try:
        current_policy_str = client_manager.s3.get_bucket_policy(bucket_policy.bucket)
        current_policy = json.loads(current_policy_str)
    except S3Error as s3e:
        if s3e.code == "NoSuchBucketPolicy":
            logger.info(f"Creating bucket policy for {bucket_policy.bucket}")
            try:
                client_manager.s3.set_bucket_policy(bucket_policy.bucket, desired_policy_json)
                current_policy = client_manager.s3.get_bucket_policy(bucket_policy.bucket)
            except S3Error as sbe:
                if sbe.code == "MalformedPolicy":
                    logger.error(
                        "Unable to apply policy: do the resources in the policy file match the bucket name? Is it valid JSON?"
                    )
                    return

    policies_diff = compare_objects(current_policy, desired_policy)
    if not policies_diff:
        return

    logger.info(f"Desired bucket policy for '{bucket_policy.bucket}' does not match current policy. Updating.")
    try:
        client_manager.s3.set_bucket_policy(bucket_policy.bucket, desired_policy_json)
    except S3Error as s3e:
        logger.error(f"Failed to update bucket policy: {s3e.code}")


def handle_iam_policy(iam_policy: IamPolicy):
    """
    Manage IAM policies for users.
    If the policy doesn't exist, create it.
    If the policy exists, compare the desired policy with the current policy, and update if needed.

    Args:
        iam_policy: IamPolicy
    """
    current_policy = None
    desired_policy = read_json(iam_policy.policy_file)

    try:
        current_policy_str = client_manager.s3.policy_info(iam_policy.name)
        current_policy = json.loads(current_policy_str)
    except MinioAdminException as mae:
        # noinspection PyProtectedMember
        mae_obj = json.loads(mae._body)
        if mae_obj["Code"] == "XMinioAdminNoSuchPolicy":
            logger.info(f"IAM policy {iam_policy.name} does not exist, creating.")
            client_manager.admin.policy_add(iam_policy.name, iam_policy.policy_file)
            current_policy = client_manager.admin.policy_info(iam_policy.name)
        else:
            logger.exception("An unknown exception occurred")
            increment_error_count()

    if not compare_objects(current_policy, desired_policy):
        return

    logger.info(f"Desired IAM policy '{iam_policy.name}' does not match current policy. Updating IAM policy.")
    client_manager.admin.policy_add(iam_policy.name, iam_policy.policy_file)


def handle_iam_policy_attachments(user: IamPolicyAttachment):
    """
    Manage user policy attachments.

    Args:
        user: IamPolicyAttachment
    """
    logger.debug(f"Handling user policy attachments for '{user.username}'")
    for policy_name in user.policies:
        logger.debug(f"Attaching policy '{policy_name}' to access key '{user.username}'")
        client_manager.admin.policy_set(policy_name, user.username)

    # TODO: don't set the attachments if they're already attached
