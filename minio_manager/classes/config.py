from __future__ import annotations

import json

from minio.lifecycleconfig import LifecycleConfig

from minio_manager.classes.minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount
from minio_manager.utilities import logger, read_yaml, retrieve_environment_variable


class ClusterResources:
    """MinIO Cluster configuration object, aka the cluster contents: buckets, policies, etc."""

    buckets: list[Bucket]
    bucket_policies: list[BucketPolicy]
    bucket_lifecycle_config: LifecycleConfig | None
    service_accounts: list[ServiceAccount]
    iam_policies: list[IamPolicy]
    iam_policy_attachments: list[IamPolicyAttachment]

    def __init__(self):
        self.buckets = []
        self.bucket_policies = []
        self.bucket_lifecycle_config = None
        self.service_accounts = []
        self.iam_policies = []
        self.iam_policy_attachments = []


def parse_buckets(buckets):
    if not buckets:
        logger.info("No buckets configured, skipping.")
        return

    bucket_objects = []
    try:
        for bucket in buckets:
            versioning = bucket.get("versioning", None)
            create_sa = bucket.get("create_service_account", True)
            bucket_objects.append(Bucket(bucket["name"], create_sa, versioning))
    except AttributeError:
        logger.info("No buckets configured, skipping.")

    return bucket_objects


def parse_bucket_policies(bucket_policies):
    if not bucket_policies:
        logger.info("No bucket policies configured, skipping.")
        return

    bucket_policy_objects = []
    for bucket_policy in bucket_policies:
        bucket_policy_objects.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))

    return bucket_policy_objects


def parse_bucket_lifecycle_config(lifecycle_configs):
    if not lifecycle_configs:
        logger.info("No bucket lifecycle configs configured, skipping.")
        return

    rules: list = []
    for policy_file in lifecycle_configs:
        config_data = json.loads(policy_file["policy_file"])
        print(config_data)

    return LifecycleConfig(rules)


def parse_service_accounts(service_accounts):
    if not service_accounts:
        logger.info("No service accounts configured, skipping.")
        return

    service_account_objects = []
    for service_account in service_accounts:
        bucket = service_account.get("bucket", None)
        service_account_objects.append(ServiceAccount(service_account["name"], bucket))

    return service_account_objects


def parse_iam_policy_attachments(iam_policy_attachments):
    if not iam_policy_attachments:
        logger.info("No IAM policy attachments configured, skipping.")
        return

    iam_policy_attachment_objects = []
    for user in iam_policy_attachments:
        iam_policy_attachments.append(IamPolicyAttachment(user["username"], user["policies"]))

    return iam_policy_attachment_objects


def parse_iam_policies(iam_policies):
    if not iam_policies:
        logger.info("No IAM policies configured, skipping.")
        return

    iam_policy_objects = []
    for iam_policy in iam_policies:
        iam_policy_objects.append(IamPolicy(iam_policy["name"], iam_policy["policy_file"]))

    return iam_policy_objects


def parse_resources(raw_resources: dict) -> ClusterResources:
    raw_resources = read_yaml(raw_resources)
    cluster_resources = ClusterResources()

    buckets = raw_resources.get("buckets", [])
    cluster_resources.buckets = parse_buckets(buckets)

    bucket_policies = raw_resources.get("bucket_policies", [])
    cluster_resources.bucket_policies = parse_bucket_policies(bucket_policies)

    bucket_lifecycle_configs = raw_resources.get("bucket_lifecycle_configs", [])
    cluster_resources.bucket_lifecycle_config = parse_bucket_lifecycle_config(bucket_lifecycle_configs)

    service_accounts = raw_resources.get("service_accounts", [])
    cluster_resources.service_accounts = parse_service_accounts(service_accounts)

    iam_policies = raw_resources.get("iam_policies", [])
    cluster_resources.iam_policies = parse_iam_policies(iam_policies)

    iam_policy_attachments = raw_resources.get("iam_policy_attachments", [])
    cluster_resources.iam_policy_attachments = parse_iam_policy_attachments(iam_policy_attachments)

    return cluster_resources


class MinioConfig:
    """MinIO server configuration object, the connection details."""

    def __init__(self):
        self.name = retrieve_environment_variable("MINIO_MANAGER_CLUSTER_NAME")
        self.endpoint = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT")
        self.secure = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT_SECURE", True)
        self.controller_user = retrieve_environment_variable("MINIO_MANAGER_MINIO_CONTROLLER_USER")
        self.access_key = None
        self.secret_key = None
        self.cluster_resources = retrieve_environment_variable("MINIO_MANAGER_CLUSTER_RESOURCES_FILE")
        self.secret_backend_type = retrieve_environment_variable("MINIO_MANAGER_SECRET_BACKEND_TYPE")
        self.secret_s3_bucket = retrieve_environment_variable("MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET")
