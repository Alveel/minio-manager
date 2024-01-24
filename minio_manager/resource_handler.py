from .bucket_handler import handle_bucket
from .classes.config import ClusterResources, parse_resources  # noqa: F401
from .classes.mc_wrapper import McWrapper
from .classes.minio_resources import MinioConfig
from .classes.secrets import SecretManager
from .policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from .service_account_handler import handle_service_account
from .utilities import logger, setup_minio_admin_client, setup_s3_client


def initialise_clients(config: MinioConfig):
    """Configure all required clients: S3, MinioAdmin, and MC wrapper

    Args:
        config: MinioConfig

    Returns: tuple (Minio, MinioAdmin, McWrapper)

    """
    s3_client = setup_s3_client(config.endpoint, config.access_key, config.secret_key, config.secure)
    admin_client = setup_minio_admin_client(config.endpoint, config.access_key, config.secret_key, config.secure)
    mc = McWrapper(config)
    return s3_client, admin_client, mc


def handle_resources(minio: MinioConfig, secrets: SecretManager, resources: tuple):
    """
    Set up MinIO S3 and MinIO Admin clients for the specified cluster,
    then handle buckets, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        minio: MinioConfig
        secrets: SecretManager
        resources: tuple of all resources to be handled
    """
    s3_client, admin_client, mc = initialise_clients(minio)
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = resources

    logger.info("Handling service accounts...")
    for service_account in service_accounts:
        handle_service_account(mc, secrets, service_account)

    logger.info("Handling buckets...")
    for bucket in buckets:
        handle_bucket(s3_client, bucket)

    logger.info("Handling bucket policies...")
    for bucket_policy in bucket_policies:
        handle_bucket_policy(s3_client, bucket_policy)

    logger.info("Handling IAM policies...")
    for iam_policy in iam_policies:
        handle_iam_policy(admin_client, iam_policy)

    logger.info("Handling IAM policy attachments...")
    for iam_policy_attachment in iam_policy_attachments:
        handle_iam_policy_attachments(admin_client, iam_policy_attachment)
