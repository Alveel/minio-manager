from __future__ import annotations

import json
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
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
        env_prefix="MINIO_MANAGER_", env_file="config.env", env_file_encoding="utf-8", extra="ignore"
    )

    log_level: str = "INFO"

    cluster_name: str
    s3_endpoint: str
    s3_endpoint_secure: bool = True

    minio_controller_user: str
    cluster_resources_file: str = "resources.yaml"

    secret_backend_type: str
    secret_backend_s3_bucket: str = "minio-manager-secrets"
    secret_backend_s3_access_key: str
    secret_backend_s3_secret_key: str

    keepass_filename: str = "secrets.kdbx"
    keepass_password: str | None = None

    auto_create_service_account: bool = True
    allowed_bucket_prefixes: tuple[str, ...] = ()
    default_bucket_versioning: str = "Suspended"
    default_lifecycle_policy_file: str | None = None
    service_account_policy_base_file: str = ""

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


settings = Settings()
