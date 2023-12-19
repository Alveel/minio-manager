import logging

from minio import Minio, MinioAdmin, credentials

from .bucket_handler import handle_bucket
from .classes.minio import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, MinioConfig, ServiceAccount
from .classes.secrets import SecretManager
from .mc_wrapper import McWrapper
from .policy_handler import handle_bucket_policy, handle_iam_policy, handle_iam_policy_attachments
from .user_handler import handle_service_account
from .utilities import read_yaml

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
    mc = McWrapper(minio.name, minio.endpoint, minio.access_key, minio.secret_key, minio.secure)
    cluster_config = read_yaml(minio.config)

    logger.info("Handling service accounts...")
    for service_account in cluster_config.service_accounts:
        sa = ServiceAccount(service_account["name"])
        handle_service_account(mc, secrets, sa)

    logger.info("Handling buckets...")
    for bucket in cluster_config.buckets:
        b = Bucket(bucket["name"], bucket["versioning"])
        handle_bucket(s3_client, b)

    logger.info("Handling bucket policies...")
    for bucket_policy in cluster_config.bucket_policies:
        bp = BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"])
        handle_bucket_policy(s3_client, bp)

    logger.info("Handling IAM policies...")
    for iam_policy in cluster_config.iam_policies:
        ip = IamPolicy(iam_policy["name"], iam_policy["policy_file"])
        handle_iam_policy(admin_client, ip)

    logger.info("Handling IAM policy attachments...")
    for user in cluster_config.iam_policy_attachments:
        ipa = IamPolicyAttachment(user["name"], user["policies"])
        handle_iam_policy_attachments(admin_client, ipa)
