from bucket_handler import handle_bucket
from minio import Minio, MinioAdmin, credentials
from policy_handler import handle_bucket_policy, handle_iam_policy, handle_user_policy_attachments
from utilities import read_yaml


def setup_client(minio) -> Minio:
    return Minio(
        minio["endpoint"], access_key=minio["access_key"], secret_key=minio["secret_key"], secure=minio["secure"]
    )


def setup_admin_client(minio) -> MinioAdmin:
    provider = credentials.StaticProvider(minio["access_key"], minio["secret_key"])
    return MinioAdmin(minio["endpoint"], provider, secure=minio["secure"])


def handle_cluster(minio):
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
    s3_client = setup_client(minio)
    admin_client = setup_admin_client(minio)
    cluster_config = read_yaml(minio["config"])

    for bucket in cluster_config["buckets"]:
        handle_bucket(s3_client, bucket)

    for bucket_policy in cluster_config["bucket_policies"]:
        handle_bucket_policy(s3_client, bucket_policy)

    for iam_policy in cluster_config["iam_policies"]:
        handle_iam_policy(admin_client, iam_policy)

    for user in cluster_config["user_policy_attachments"]:
        handle_user_policy_attachments(admin_client, user)
