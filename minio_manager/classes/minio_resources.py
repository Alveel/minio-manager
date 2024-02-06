from __future__ import annotations

from minio.lifecycleconfig import LifecycleConfig
from minio.versioningconfig import VersioningConfig


class Bucket:
    def __init__(
        self,
        name: str,
        create_service_account: bool = True,
        versioning: VersioningConfig | None = None,
        lifecycle_config: LifecycleConfig | None = None,
    ):
        self.name = name
        self.create_sa = create_service_account
        self.versioning = versioning
        self.lifecycle_config = lifecycle_config


class BucketPolicy:
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    def __init__(
        self, name: str, access_key: str | None = None, secret_key: str | None = None, policy_file: str | None = None
    ):
        self.name = name
        self.access_key = access_key
        self.secret_key = secret_key
        self.policy_file = policy_file


class IamPolicy:
    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
