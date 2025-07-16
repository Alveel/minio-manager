from minio_manager.bucket_handler import handle_bucket
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import BucketPolicy
from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.classes.settings import settings
from minio_manager.policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from minio_manager.service_account_handler import handle_service_account


def handle_resources(resources: ClusterResources):
    """Top-level dispatcher for handling resources."""
    handle_all_buckets(resources)
    handle_all_bucket_policies(resources)
    handle_all_service_accounts(resources)
    handle_all_iam_policies(resources)
    handle_all_policy_attachments(resources)


def handle_all_buckets(resources: ClusterResources):
    if resources.buckets:
        logger.info(f"Handling {len(resources.buckets)} buckets...")
        for bucket in resources.buckets:
            handle_bucket(bucket)


def handle_all_bucket_policies(resources: ClusterResources):
    if not resources.buckets:
        return

    total_buckets = len(resources.buckets)
    logger.info(f"Handling bucket policies for {total_buckets} buckets...")

    explicit_policies = {bp.bucket: bp.policy_file for bp in resources.bucket_policies or []}
    explicit_count = 0
    default_count = 0
    default_policy_file = getattr(settings, "default_bucket_policy_file", None)

    for bucket in resources.buckets:
        bucket_name = bucket.name
        policy_file = explicit_policies.get(bucket_name)
        is_explicit = policy_file is not None

        if is_explicit:
            logger.debug(f"Using explicitly defined policy for bucket '{bucket_name}'")
            explicit_count += 1
        else:
            default_count += 1

        handle_bucket_policy(BucketPolicy(bucket=bucket_name, policy_file=policy_file), is_explicit=is_explicit)

    default_policy_msg = f"'{default_policy_file}'" if default_policy_file else "None (no default policy configured)"
    logger.info(f"Applied explicit policies to {explicit_count} bucket(s).")
    logger.info(f"Applied default policy {default_policy_msg} to {default_count} bucket(s).")


def handle_all_service_accounts(resources: ClusterResources):
    if resources.service_accounts:
        logger.info(f"Handling {len(resources.service_accounts)} service accounts...")
        for service_account in resources.service_accounts:
            handle_service_account(service_account)


def handle_all_iam_policies(resources: ClusterResources):
    if resources.iam_policies:
        logger.info(f"Handling {len(resources.iam_policies)} IAM policies...")
        for iam_policy in resources.iam_policies:
            handle_iam_policy(iam_policy)


def handle_all_policy_attachments(resources: ClusterResources):
    if resources.iam_policy_attachments:
        logger.info(f"Handling {len(resources.iam_policy_attachments)} IAM policy attachments...")
        for iam_policy_attachment in resources.iam_policy_attachments:
            handle_iam_policy_attachments(iam_policy_attachment)
