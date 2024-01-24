from __future__ import annotations

from ..utilities import retrieve_environment_variable


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


class Bucket:
    def __init__(self, name: str, versioning: bool):
        self.name = name
        self.versioning = versioning


class BucketPolicy:
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    def __init__(self, name: str, bucket: str | None = None):
        self.name = name
        self.bucket = bucket


class IamPolicy:
    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
