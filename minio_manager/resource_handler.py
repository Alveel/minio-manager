from minio_manager.bucket_handler import handle_bucket
from minio_manager.classes.config import ClusterResources, parse_resources  # noqa: F401
from minio_manager.policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from minio_manager.service_account_handler import handle_service_account
from minio_manager.utilities import logger


def handle_resources(resources: tuple):
    """
    Set up MinIO S3 and MinIO Admin clients for the specified cluster,
    then handle buckets, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        resources: tuple of all resources to be handled
    """
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = resources

    logger.info("Handling buckets...")
    for bucket in buckets:
        if bucket.create_sa:
            handle_bucket(bucket, True)
        else:
            handle_bucket(bucket)

    logger.info("Handling service accounts...")
    for service_account in service_accounts:
        handle_service_account(service_account)

    logger.info("Handling bucket policies...")
    for bucket_policy in bucket_policies:
        handle_bucket_policy(bucket_policy)

    logger.info("Handling IAM policies...")
    for iam_policy in iam_policies:
        handle_iam_policy(iam_policy)

    logger.info("Handling IAM policy attachments...")
    for iam_policy_attachment in iam_policy_attachments:
        handle_iam_policy_attachments(iam_policy_attachment)
