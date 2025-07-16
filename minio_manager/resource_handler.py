from minio_manager.bucket_handler import handle_bucket
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import BucketPolicy
from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from minio_manager.service_account_handler import handle_service_account


def handle_resources(resources: ClusterResources):
    """Handle the provided bucket, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        resources: ClusterResources object with all resources
    """
    logger.info(f"Handling {len(resources.buckets)} buckets...")
    for bucket in resources.buckets:
        handle_bucket(bucket)

    if resources.buckets:
        logger.info(f"Applying bucket policies for {len(resources.buckets)} buckets...")

        # Build a lookup from bucket name to explicitly defined policy
        explicit_policies = {bp.bucket: bp.policy_file for bp in resources.bucket_policies or []}

        # Iterate over all buckets, apply policy if defined, else fall back to default
        for bucket in resources.buckets:
            bucket_name = bucket.name
            policy_file = explicit_policies.get(bucket_name)  # None if not explicitly defined
            handle_bucket_policy(BucketPolicy(bucket=bucket_name, policy_file=policy_file))

    if resources.service_accounts:
        logger.info(f"Handling {len(resources.service_accounts)} service accounts...")
        for service_account in resources.service_accounts:
            handle_service_account(service_account)

    if resources.iam_policies:
        logger.info(f"Handling {len(resources.iam_policies)} IAM policies...")
        for iam_policy in resources.iam_policies:
            handle_iam_policy(iam_policy)

    if resources.iam_policy_attachments:
        logger.info(f"Handling {len(resources.iam_policy_attachments)} IAM policy attachments...")
        for iam_policy_attachment in resources.iam_policy_attachments:
            handle_iam_policy_attachments(iam_policy_attachment)
