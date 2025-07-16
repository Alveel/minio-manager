import json

from minio import S3Error
from minio.error import MinioAdminException

from minio_manager.classes.client_manager import client_manager
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import BucketPolicy, IamPolicy, IamPolicyAttachment
from minio_manager.classes.settings import settings
from minio_manager.utilities import compare_objects, increment_error_count, read_json


def handle_bucket_policy(bucket_policy: BucketPolicy, is_explicit: bool = False):
    """
    Manage policies for buckets.
    If the policy doesn't exist, create it.
    If the policy exists, compare the desired policy with the current policy, and update if needed.
    If no policy file is specified, use the default bucket policy from settings if available.
    If neither explicit nor default policy applies, remove the existing bucket policy.
    """
    policy_file = resolve_bucket_policy_file(bucket_policy)

    if is_explicit:
        logger.debug(
            f"Using explicitly configured policy file '{bucket_policy.policy_file}' for bucket '{bucket_policy.bucket}'"
        )

    if not policy_file:
        delete_existing_bucket_policy(bucket_policy.bucket)
        return

    desired_policy = read_json(policy_file)
    desired_policy_json = json.dumps(desired_policy)

    current_policy = get_existing_bucket_policy(bucket_policy.bucket)

    if current_policy is not None:
        if compare_objects(current_policy, desired_policy):
            logger.debug(f"Bucket policy for '{bucket_policy.bucket}' is up to date.")
            return
        else:
            logger.info(f"Updating bucket policy for '{bucket_policy.bucket}'")
    else:
        logger.info(f"Creating bucket policy for '{bucket_policy.bucket}'")

    apply_bucket_policy(bucket_policy.bucket, desired_policy_json)


def resolve_bucket_policy_file(bucket_policy: BucketPolicy):
    policy_file = bucket_policy.policy_file
    if not policy_file and settings.default_bucket_policy_file:
        policy_file = settings.default_bucket_policy_file
    return policy_file


def delete_existing_bucket_policy(bucket: str):
    logger.info(f"No policy specified for bucket '{bucket}'. Removing existing bucket policy if any.")
    try:
        client_manager.s3.delete_bucket_policy(bucket)
    except S3Error as e:
        if e.code == "NoSuchBucketPolicy":
            logger.debug(f"No existing bucket policy to delete for bucket '{bucket}'")
        else:
            logger.error(f"Failed to delete bucket policy for bucket '{bucket}': {e}")


def get_existing_bucket_policy(bucket: str) -> dict | None:
    try:
        current_policy_str = client_manager.s3.get_bucket_policy(bucket)
        return json.loads(current_policy_str)
    except S3Error as s3e:
        if s3e.code == "NoSuchBucketPolicy":
            return None
        logger.error(f"Failed to fetch current bucket policy for '{bucket}': {s3e}")
        return None


def apply_bucket_policy(bucket: str, policy_json: str):
    try:
        logger.debug(f"Applying bucket policy to '{bucket}'")
        client_manager.s3.set_bucket_policy(bucket, policy_json)
    except S3Error as e:
        if e.code == "MalformedPolicy":
            logger.error(
                "Unable to apply policy: do the resources in the policy file match the bucket name? Is it valid JSON?"
            )
        else:
            logger.error(f"Failed to update bucket policy for '{bucket}': {e.code}")


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
