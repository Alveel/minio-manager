from __future__ import annotations

import os
import sys

from dotenv import find_dotenv, load_dotenv

"""Load environment variables from .env file from the current working directory."""
dotenv_path = find_dotenv(filename="config.env", usecwd=True)
load_dotenv(dotenv_path, override=True, verbose=True)


class Config:
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

    def __init__(self):
        self._required_vars = ("MINIO_MANAGER_CLUSTER_NAME",)  # Define required variables

    def _get_env_var(self, name: str, default=None) -> str:
        """Retrieves an environment variable, handling errors and logging."""
        try:
            return os.environ[name].strip("\"'")  # Strip quotes concisely
        except KeyError as ke:
            if default is None and name in self._required_vars:
                raise ValueError(f"Required environment variable {name} not found!") from ke
            return default

    def get_log_level(self):
        return self._get_env_var("MINIO_MANAGER_LOG_LEVEL", "INFO")

    def get_cluster_name(self):
        return self._get_env_var("MINIO_MANAGER_CLUSTER_NAME")

    endpoint = _get_env_var("MINIO_MANAGER_S3_ENDPOINT")
    secure = _get_env_var("MINIO_MANAGER_S3_ENDPOINT_SECURE", True)
    controller_user = _get_env_var("MINIO_MANAGER_MINIO_CONTROLLER_USER")
    access_key = None
    secret_key = None
    cluster_resources = _get_env_var("MINIO_MANAGER_CLUSTER_RESOURCES_FILE", "resources.yaml")
    secret_backend_type = _get_env_var("MINIO_MANAGER_SECRET_BACKEND_TYPE")
    secret_s3_bucket = _get_env_var("MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET", "minio-manager-secrets")

    @property
    def default_bucket_versioning(self):
        return self._get_env_var("MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING", "Suspended")

    @property
    def default_bucket_lifecycle_policy(self):
        return self._get_env_var("MINIO_MANAGER_DEFAULT_LIFECYCLE_POLICY", "")

    @property
    def default_bucket_create_service_account(self):
        return self._get_env_var("MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT", "True")

    @property
    def default_bucket_allowed_prefixes(self):
        return self._get_env_var("MINIO_MANAGER_ALLOWED_BUCKET_PREFIXES", "")

    @property
    def service_account_policy_base_file(self):
        module_directory = os.path.dirname(__file__)
        sa_policy_embedded = f"../{module_directory}/resources/service-account-policy-base.json"
        return self._get_env_var("MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_BASE_FILE", sa_policy_embedded)
