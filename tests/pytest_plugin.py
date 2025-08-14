"""Pytest plugin to handle minio_manager imports without CLI conflicts."""

import os
import sys


def pytest_configure(config):
    """Configure pytest to prevent CLI parsing conflicts."""
    # Set environment variables for tests
    os.environ.setdefault("MINIO_MANAGER_CLUSTER_NAME", "test-cluster")
    os.environ.setdefault("MINIO_MANAGER_S3_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_MANAGER_S3_ENDPOINT_SECURE", "false")
    os.environ.setdefault("MINIO_MANAGER_MINIO_CONTROLLER_USER", "minioadmin")
    os.environ.setdefault("MINIO_MANAGER_SECRET_BACKEND_TYPE", "yaml")
    os.environ.setdefault("MINIO_MANAGER_SECRET_BACKEND_PATH", "secrets.yaml")
    os.environ.setdefault("MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY", "minioadmin")
    os.environ.setdefault("MINIO_MANAGER_AUTO_CREATE_SERVICE_ACCOUNT", "true")

    # Prevent CLI parsing by patching pydantic-settings
    original_cli_settings_source = None
    try:
        from pydantic_settings.sources import CliSettingsSource

        original_cli_settings_source = CliSettingsSource

        # Create a mock CLI settings source that doesn't parse args
        class MockCliSettingsSource:
            def __init__(self, *args, **kwargs):
                pass

            def prepare_field_value(self, *args, **kwargs):
                return None, "", False

            def _load_env_vars(self, *args, **kwargs):
                return {}

        # Monkey patch the CliSettingsSource
        import pydantic_settings.sources

        pydantic_settings.sources.CliSettingsSource = MockCliSettingsSource

    except ImportError:
        pass


def pytest_sessionstart(session):
    """Prevent CLI parsing at session start."""
    # Store original argv
    original_argv = sys.argv.copy()

    # Mock the settings module before any imports
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class TestSettings(BaseSettings):
        """Mock settings for tests."""

        model_config = SettingsConfigDict(
            env_prefix="MINIO_MANAGER_",
            cli_parse_args=False,
            extra="ignore",
        )

        cluster_name: str = "test-cluster"
        s3_endpoint: str = "localhost:9000"
        s3_endpoint_secure: bool = False
        minio_controller_user: str = "minioadmin"
        secret_backend_type: str = "yaml"
        secret_backend_path: str = "secrets.yaml"
        secret_backend_s3_access_key: str = "minioadmin"
        secret_backend_s3_secret_key: str = "minioadmin"
        auto_create_service_account: bool = True
        cluster_resources_file: str = "resources.yaml"
        secret_backend_s3_bucket: str = "minio-manager-secrets"
        keepass_password: str | None = None
        allowed_bucket_prefixes: tuple[str, ...] = ()
        default_bucket_versioning: str = "Suspended"
        default_lifecycle_policy_file: str | None = None
        default_bucket_policy_file: str | None = None
        service_account_policy_base_file: str = ""
        log_level: str = "INFO"
        dry_run: bool = False
        _get_on_lifecycle_supported: bool = True

    # Create test settings instance
    test_settings = TestSettings()

    # Store in session for access by tests
    session.test_settings = test_settings


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker("integration")
        # Add unit marker to other tests
        else:
            item.add_marker("unit")
