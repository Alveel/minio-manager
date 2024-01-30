from __future__ import annotations

from typing import ClassVar

from minio_manager.utilities import retrieve_environment_variable

default_bucket_versioning = retrieve_environment_variable("MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING", "Disabled")


class Bucket:
    allowed_versioning: ClassVar[list[str]] = [
        "Enabled",
        "Suspended",
        "Disabled",
    ]

    def __init__(self, name: str, create_service_account: bool = True, versioning: str | None = None):
        self.name = name
        self.create_sa = create_service_account
        if versioning:
            if versioning.capitalize() not in self.allowed_versioning:
                raise ValueError(f"versioning must be one of {self.allowed_versioning}")
            self.versioning = versioning.capitalize()
        else:
            self.versioning = default_bucket_versioning
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
