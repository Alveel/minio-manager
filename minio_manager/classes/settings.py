from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import ValidationError
from pydantic.fields import Field, FieldInfo
from pydantic_settings import (
    BaseSettings,
    CliImplicitFlag,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def parse_bucket_prefixes(value: str) -> str:
    value_tuple = tuple(value.split(","))
    # Complex types like list, set, dict, and sub-models are populated from the environment by treating the
    # environment variable's value as a JSON-encoded string.
    # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values
    return json.dumps(value_tuple)


class CustomEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        # allow comma-separated list parsing
        if field_name == "allowed_bucket_prefixes" and value:
            value = parse_bucket_prefixes(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class CustomDotEnvSettingsSource(DotEnvSettingsSource):
    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        # allow comma-separated list parsing
        if field_name == "allowed_bucket_prefixes" and value:
            value = parse_bucket_prefixes(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    """
    The Settings class is responsible for loading the settings from environment variables and the dotenv file, and
    making them available to the rest of the application.
    """

    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_kebab_case=True,
        env_prefix="MINIO_MANAGER_",
        env_file="config.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", description="The log level to use. Only INFO and DEBUG supported")
    dry_run: CliImplicitFlag[bool] = Field(default=False, description="Run in dry-run mode, making no changes")

    cluster_name: str = Field(description="The name of the cluster, determines path to credentials in secret backends")
    s3_endpoint: str = Field(description="The endpoint for the S3-compatible storage")
    s3_endpoint_secure: bool = Field(default=True, description="Whether to use HTTPS for the S3 endpoint")

    minio_controller_user: str = Field(description="The username for the MinIO controller")
    cluster_resources_file: str = Field(default="resources.yaml", description="The path to the cluster resources file")

    secret_backend_type: str = Field(description="The type of secret backend to use, [keepass|yaml]")
    secret_backend_s3_bucket: str = "minio-manager-secrets"  # noqa: S105, not a secret
    secret_backend_s3_access_key: str
    secret_backend_s3_secret_key: str

    # Required for KeePass and YAML secret backends
    secret_backend_path: str = "secrets.yaml"  # noqa: S105, not a secret
    # Required for KeePass secret backend
    keepass_password: str | None = None

    auto_create_service_account: bool = Field(
        default=True, description="Automatically create service accounts for managed buckets"
    )
    allowed_bucket_prefixes: tuple[str, ...] = Field(default=(), description="Comma-separated allowed bucket prefixes")
    default_bucket_versioning: str = Field(
        default="Suspended", description="The default bucket versioning state [Enabled|Suspended]"
    )
    default_lifecycle_policy_file: str | None = Field(default=None, description="The default lifecycle policy file")
    service_account_policy_base_file: str = Field(
        default="", description="The service account policy file to use as a template"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: CustomEnvSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            CustomEnvSettingsSource(settings_cls),
            CustomDotEnvSettingsSource(settings_cls),
            init_settings,
        )


try:
    settings = Settings()
except ValidationError as e:
    print(f"Error loading settings: {e}")
    sys.exit(1)
