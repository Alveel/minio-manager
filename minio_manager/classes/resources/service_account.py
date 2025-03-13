from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, ClassVar

from pydantic import AfterValidator, BaseModel, Field
from utilities import increment_error_count, read_json

from minio_manager import logger, settings


def validate_name(name: str) -> str:
    if len(name) > 32:
        return name[:32]
    return name


class ServiceAccount(BaseModel):
    """
    ServiceAccount represents a MinIO service account (or S3 access key).

    name: The name of the service account
    description: The description of the service account
    access_key: The access key of the service account
    secret_key: The secret key of the service account
    policy: Optional custom policy for the service account
    policy_file: The path to a JSON policy file
    """

    name: str = Annotated[str, AfterValidator(validate_name)]
    description: str
    access_key: str = Field(default=None, min_length=3, max_length=20)
    secret_key: str = Field(default=None, min_length=20, max_length=40)
    policy: ClassVar[dict] | None
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
        self.name = name[:32]
        self.description = name + " - " + description
        self.full_name = name
        self.access_key = access_key
        self.secret_key = secret_key
        if policy_file:
            if isinstance(policy_file, Path):
                self.policy_file = policy_file
            else:
                self.policy_file = Path(policy_file)
        else:
            self.policy_file = None
        self.policy = policy
        if self.policy_file:
            try:
                self.policy = read_json(self.policy_file)
            except FileNotFoundError:
                logger.error(f"Policy file '{self.policy_file}' for service account '{name}' not found!")
                increment_error_count()

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

        with NamedTemporaryFile(prefix=self.full_name, suffix=".json", delete=False) as out:
            new_content = base_policy.replace("BUCKET_NAME_REPLACE_ME", self.full_name)
            out.write(new_content.encode("utf-8"))
            self.policy = json.loads(new_content)
            self.policy_file = Path(out.name)
            self.policy_generated = True

    @property
    def as_dict(self) -> dict:
        """
        Convert the ServiceAccount object to a dictionary for use with MinioAdmin.
        """
        return_dict = {
            "access_key": self.access_key,
            "name": self.name,
            "description": self.description,
        }
        if self.secret_key:
            return_dict["secret_key"] = self.secret_key
        # Only pass policy OR policy_file, not both
        if self.policy:
            return_dict["policy"] = self.policy
        elif self.policy_file:
            return_dict["policy_file"] = self.policy_file
        return return_dict
