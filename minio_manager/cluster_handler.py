import logging

from .bucket_handler import handle_bucket
from .classes.config import ClusterConfig, parse_resources  # noqa: F401
from .classes.mc_wrapper import McWrapper
from .classes.minio_resources import MinioConfig
from .classes.secrets import SecretManager
from .policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from .user_handler import handle_service_account
from .utilities import read_yaml, setup_minio_admin_client, setup_s3_client

logger = logging.getLogger("root")


def handle_cluster(minio: MinioConfig, secrets: SecretManager):
    """
    Set up MinIO S3 and MinIO Admin clients for the specified cluster,
    then handle buckets, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        minio: MinioConfig
        secrets: SecretManager
    """
    s3_client = setup_s3_client(minio.endpoint, minio.access_key, minio.secret_key, minio.secure)
    admin_client = setup_minio_admin_client(minio.endpoint, minio.access_key, minio.secret_key, minio.secure)
    mc = McWrapper(minio.name, minio.endpoint, minio.access_key, minio.secret_key, minio.secure)
    cluster_config = read_yaml(minio.config)  # type: ClusterConfig

    logger.info("Loading resources...")
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = parse_resources(cluster_config)

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
