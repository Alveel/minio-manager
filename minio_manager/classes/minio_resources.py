from __future__ import annotations

from minio.versioningconfig import VersioningConfig

from minio_manager.utilities import retrieve_environment_variable

default_bucket_versioning = retrieve_environment_variable("MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING", "Suspended")


class Bucket:
    allowed_versioning: tuple[str, str, str] = (
        "Enabled",
        "Suspended",
    )

    def __init__(self, name: str, create_service_account: bool = True, versioning: str | None = None):
        self.name = name
        self.create_sa = create_service_account
        if versioning:
            if versioning.capitalize() not in self.allowed_versioning:
                raise ValueError(f"Versioning for bucket {self.name} must be one of {self.allowed_versioning}")
            self.versioning = VersioningConfig(status=versioning.capitalize())
        else:
            self.versioning = VersioningConfig(status=default_bucket_versioning.capitalize())


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
