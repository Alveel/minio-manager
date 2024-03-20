from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ClassVar

from minio.lifecycleconfig import LifecycleConfig
from minio.versioningconfig import VersioningConfig

from minio_manager.classes.logging_config import logger
from minio_manager.classes.settings import settings
from minio_manager.utilities import read_json


class Bucket:
    """
    Bucket represents an S3 bucket.

    name: The name of the bucket
    create_service_account: Whether to create a service account for the bucket (True or False)
    versioning: The versioning configuration for the bucket (Enabled or Suspended)
    lifecycle_config: The path to a lifecycle configuration JSON file for the bucket
    """

    def __init__(
        self,
        name: str,
        create_service_account: bool = settings.auto_create_service_account,
        versioning: VersioningConfig | None = None,
        lifecycle_config: LifecycleConfig | None = None,
    ):
        self.name = name
        self.create_sa = create_service_account
        self.versioning = versioning
        self.lifecycle_config = lifecycle_config


class BucketPolicy:
    """
    BucketPolicy represents an S3 bucket policy.

    bucket: The name of the bucket
    policy_file: The path to a JSON policy file
    """

    # TODO: try loading the policy file in order to validate its contents
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    """
    ServiceAccount represents a MinIO service account (or S3 access key).

    name: The name of the service account
    description: The description of the service account
    access_key: The access key of the service account
    secret_key: The secret key of the service account
    policy: Optional custom policy for the service account
    policy_file: The path to a JSON policy file
    """

    policy = ClassVar[dict]
    policy_file: Path | None
    policy_generated = False

    def __init__(
        self,
        name: str,
        description: str = "",
        access_key: str | None = None,
        secret_key: str | None = None,
        policy: dict | None = None,
        policy_file: Path | str | None = None,
    ):
        if len(name) > 32:
            self.name = name[:32]
            self.description = name + " " + description
        else:
            self.name = name
            self.description = description
        self.access_key = access_key
        self.secret_key = secret_key
        if policy_file:
            if isinstance(policy_file, Path):
                self.policy_file = policy_file
            else:
                self.policy_file = Path(policy_file)
        else:
            self.policy_file = None
        if policy:
            self.policy = policy
        elif self.policy_file:
            try:
                self.policy = read_json(self.policy_file)
            except FileNotFoundError:
                logger.critical(f"Policy file '{self.policy_file}' for service account '{name}' not found!")
                sys.exit(1)

    def generate_service_account_policy(self):
        """
        Generate a policy for a service account that gives access to a bucket with the same name as the service account.
        """
        if settings.service_account_policy_base_file:
            with Path(settings.service_account_policy_base_file).open() as base:
                base_policy = base.read()
        else:
            from minio_manager.resources.policies import service_account_policy_base

            base_policy = json.dumps(service_account_policy_base)

        temp_file = NamedTemporaryFile(prefix=self.name, suffix=".json", delete=False)
        with temp_file as out:
            new_content = base_policy.replace("BUCKET_NAME_REPLACE_ME", self.name)
            out.write(new_content.encode("utf-8"))

        self.policy = json.loads(new_content)
        self.policy_file = Path(temp_file.name)
        self.policy_generated = True


class IamPolicy:
    """
    IamPolicy represents an S3 IAM policy.

    name: The name of the policy
    policy_file: The path to a JSON policy file
    """

    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    """
    IamPolicyAttachment represents an S3 IAM policy attachment.

    username: The name of the user to attach the policies to
    policies: A list of policies to attach to the user
    """

    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
