from bucket_handler import handle_bucket
from minio import Minio
from policy_handler import handle_bucket_policy
from utilities import read_yaml


def setup_client(minio):
    return Minio(
        minio["endpoint"], access_key=minio["access_key"], secret_key=minio["secret_key"], secure=minio["secure"]
    )


def handle_cluster(minio):
    client = setup_client(minio)
    cluster_config = read_yaml(minio["config"])
    buckets = cluster_config["buckets"]
    bucket_policies = cluster_config["bucket_policies"]

    for bucket in buckets:
        handle_bucket(bucket, client)
    for bucket_policy in bucket_policies:
        handle_bucket_policy(bucket_policy, client)
