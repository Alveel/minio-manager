from minio_manager.bucket_handler import handle_bucket
from minio_manager.classes.logging_config import logger
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

    if resources.bucket_policies:
        logger.info(f"Handling {len(resources.bucket_policies)} bucket policies...")
        for bucket_policy in resources.bucket_policies:
            handle_bucket_policy(bucket_policy)

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
