from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass
class Config:
    def __init__(self):
        self.log_level = self._get_env_var("MINIO_MANAGER_LOG_LEVEL", "INFO")
        self.cluster_name = self._get_env_var("MINIO_MANAGER_CLUSTER_NAME")
        self.endpoint = self._get_env_var("MINIO_MANAGER_S3_ENDPOINT")
        self.secure = self._get_env_var("MINIO_MANAGER_S3_ENDPOINT_SECURE", True)
        self.controller_user = self._get_env_var("MINIO_MANAGER_MINIO_CONTROLLER_USER")
        self.cluster_resources_file = self._get_env_var("MINIO_MANAGER_CLUSTER_RESOURCES_FILE", "resources.yaml")
        self.secret_backend_type = self._get_env_var("MINIO_MANAGER_SECRET_BACKEND_TYPE")
        self.secret_s3_bucket = self._get_env_var("MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET", "minio-manager-secrets")
        self.default_bucket_versioning = self._get_env_var("MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING", "Suspended")
        self.default_bucket_lifecycle_policy = self._get_env_var("MINIO_MANAGER_DEFAULT_LIFECYCLE_POLICY", "")
        self.default_bucket_create_service_account = self._get_env_var(
            "MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT", "True"
        )
        self.default_bucket_allowed_prefixes = self._get_env_var("MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES", "")
        self.service_account_policy_base_file = self.set_service_account_policy_base_file()

    @staticmethod
    def _get_env_var(name: str, default=None) -> str:
        """
        Get an environment variable and strip any leading and trailing single and double quotes.
        This is because Python literally loads them.

        Args:
            name: str, the name of the environment variable
            default: str, default if not set

        Returns: str stripped
        """
        try:
            variable = os.environ[name]
            strip_double_quotes = variable.strip('"')
            return strip_double_quotes.strip("'")
        except KeyError:
            if default is None:
                # Use logger? How do we do that here without a circular import?
                print(f"Required environment variable {name} not found!")
                sys.exit(1)

        return default

    def set_service_account_policy_base_file(self):
        module_directory = os.path.dirname(__file__)
        sa_policy_embedded = f"../{module_directory}/resources/service-account-policy-base.json"
        return self._get_env_var("MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_BASE_FILE", sa_policy_embedded)
