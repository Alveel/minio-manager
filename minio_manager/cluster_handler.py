from bucket_handler import handle_bucket
from minio import Minio, MinioAdmin, credentials
from policy_handler import handle_bucket_policy, handle_iam_policy, handle_user_policy_attachments
from secret_manager import SecretManager
from user_handler import handle_service_account
from utilities import read_yaml


def setup_client(minio: dict) -> Minio:
    return Minio(
        minio["endpoint"], access_key=minio["access_key"], secret_key=minio["secret_key"], secure=minio["secure"]
    )


def setup_admin_client(minio: dict) -> MinioAdmin:
    provider = credentials.StaticProvider(minio["access_key"], minio["secret_key"])
    return MinioAdmin(minio["endpoint"], provider, secure=minio["secure"])


def handle_cluster(minio: dict):
    """
    Set up MinIO S3 and MinIO Admin clients for the specified cluster,
    then handle buckets, bucket policies, IAM policies, and user policy attachments, in that order.

    Args:
        minio: list of clusters with the keys
            name: str
            endpoint: str
            access_key: str
            secret_key: str
            secure: bool
            config: str
    """
    secrets = SecretManager(minio["name"], minio["secret_backend"])
    s3_client = setup_client(minio)
    admin_client = setup_admin_client(minio)
    # mc = McWrapper(minio["name"], minio["endpoint"], minio["access_key"], minio["secret_key"], minio["secure"])
    cluster_config = read_yaml(minio["config"])

    for service_account in cluster_config["service_accounts"]:
        handle_service_account(admin_client, secrets, service_account)

    for bucket in cluster_config["buckets"]:
        handle_bucket(s3_client, bucket)

    for bucket_policy in cluster_config["bucket_policies"]:
        handle_bucket_policy(s3_client, bucket_policy)

    for iam_policy in cluster_config["iam_policies"]:
        handle_iam_policy(admin_client, iam_policy)

    for user in cluster_config["user_policy_attachments"]:
        handle_user_policy_attachments(admin_client, user)
