from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ClassVar

from minio.lifecycleconfig import LifecycleConfig
from minio.versioningconfig import VersioningConfig

from minio_manager.utilities import get_env_var, logger, module_directory, read_json

sa_policy_embedded = f"{module_directory}/resources/service-account-policy-base.json"
sa_policy_base_file = get_env_var("MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_BASE_FILE", sa_policy_embedded)


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
    # TODO: try loading the policy file in order to validate its contents
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    policy = ClassVar[dict]

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
        with Path(sa_policy_base_file).open() as base:
            base_policy = base.read()

        temp_file = NamedTemporaryFile(prefix=self.name, suffix=".json", delete=False)
        with temp_file as out:
            new_content = base_policy.replace("BUCKET_NAME_REPLACE_ME", self.name)
            out.write(new_content.encode("utf-8"))

        self.policy = json.loads(new_content)
        self.policy_file = Path(temp_file.name)


class IamPolicy:
    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
