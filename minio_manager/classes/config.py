from __future__ import annotations

import yaml

from minio_manager.classes.minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount
from minio_manager.utilities import logger, retrieve_environment_variable


class ClusterResources(yaml.YAMLObject):
    """MinIO Cluster configuration object, aka the cluster contents: buckets, policies, etc."""

    yaml_tag = "!ClusterResources"
    yaml_loader = yaml.SafeLoader

    def __init__(
        self,
        buckets: list,
        bucket_policies: list,
        service_accounts: list,
        iam_policies: list,
        iam_policy_attachments: list,
    ):
        self.buckets = buckets
        self.bucket_policies = bucket_policies
        self.service_accounts = service_accounts
        self.iam_policies = iam_policies
        self.iam_policy_attachments = iam_policy_attachments


def parse_resources(resources: ClusterResources) -> tuple:  # noqa: C901
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = [], [], [], [], []

    try:
        for service_account in resources.service_accounts:
            bucket = service_account.get("bucket", None)
            service_accounts.append(ServiceAccount(service_account["name"], bucket))
    except AttributeError:
        logger.info("No service accounts configured, skipping.")

    try:
        for bucket in resources.buckets:
            versioning = bucket.get("versioning", None)
            create_sa = bucket.get("create_service_account", True)
            buckets.append(Bucket(bucket["name"], create_sa, versioning))
    except AttributeError:
        logger.info("No buckets configured, skipping.")

    try:
        for bucket_policy in resources.bucket_policies:
            bucket_policies.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))
    except AttributeError:
        logger.info("No bucket policies configured, skipping.")

    try:
        for iam_policy in resources.iam_policies:
            iam_policies.append(IamPolicy(iam_policy["name"], iam_policy["policy_file"]))
    except AttributeError:
        logger.info("No IAM policies configured, skipping.")

    try:
        for user in resources.iam_policy_attachments:
            iam_policy_attachments.append(IamPolicyAttachment(user["username"], user["policies"]))
    except AttributeError:
        logger.info("No IAM policy attachments configured, skipping.")

    return service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments


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
