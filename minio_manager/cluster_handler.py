import logging

from bucket_handler import handle_bucket
from config import MinioConfig
from mc_wrapper import McWrapper
from minio import Minio, MinioAdmin, credentials
from policy_handler import handle_bucket_policy, handle_iam_policy, handle_user_policy_attachments
from secret_manager import SecretManager
from user_handler import handle_service_account
from utilities import read_yaml

logger = logging.getLogger("root")


def setup_client(minio: MinioConfig) -> Minio:
    return Minio(minio.endpoint, access_key=minio.access_key, secret_key=minio.secret_key, secure=minio.secure)


def setup_admin_client(minio: MinioConfig) -> MinioAdmin:
    provider = credentials.StaticProvider(minio.access_key, minio.secret_key)
    return MinioAdmin(minio.endpoint, provider, secure=minio.secure)


def handle_cluster(minio: MinioConfig, secrets: SecretManager):
    """
    Set up MinIO S3 and MinIO Admin clients for the specified cluster,
    then handle buckets, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        minio: MinioConfig
        secrets: SecretManager
    """
    s3_client = setup_client(minio)
    admin_client = setup_admin_client(minio)
    mc = McWrapper(minio.name, minio.endpoint, minio.access_key, minio.secret_key, secrets, minio.secure)
    cluster_config = read_yaml(minio.config)  # type: ClusterConfig

    for service_account in cluster_config.service_accounts:
        logger.info("Handling service accounts...")
        handle_service_account(mc, secrets, service_account)

    for bucket in cluster_config.buckets:
        logger.info("Handling buckets...")
        handle_bucket(s3_client, bucket)

    for bucket_policy in cluster_config.bucket_policies:
        logger.info("Handling bucket policies...")
        handle_bucket_policy(s3_client, bucket_policy)

    for iam_policy in cluster_config.iam_policies:
        logger.info("Handling IAM policies...")
        handle_iam_policy(admin_client, iam_policy)

    for user in cluster_config.user_policy_attachments:
        logger.info("Handling IAM policy attachments...")
        access_key = secrets.get_credentials(user["name"]).access_key
        user["access_key"] = access_key
        handle_user_policy_attachments(admin_client, user)
