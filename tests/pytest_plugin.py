"""Pytest plugin for minio-manager tests."""

import os
import sys
import subprocess
from pathlib import Path


def _ensure_test_service_account():
    """Ensure the test service account exists and is properly configured."""
    try:
        # Check if MinIO is accessible
        result = subprocess.run(
            ["mc", "admin", "info", "local-test-admin"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("⚠️  MinIO test environment not accessible. Skipping service account setup.")
            print("💡 Run 'make run-test-environment' to start the test environment.")
            return
            
        # Check if service account already exists
        result = subprocess.run(
            ["mc", "admin", "user", "svcacct", "ls", "local-test-admin", "local-test-controller"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # If service account exists and has our test keys, we're good
        if result.returncode == 0 and "static-for-testing" in result.stdout:
            print("✅ Test service account already configured")
            return
            
        # Run the Makefile target to set up controller
        print("🔧 Setting up test service account via Makefile...")
        result = subprocess.run(
            ["make", "configure-controller"], 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode == 0:
            print("✅ Test service account setup completed")
        else:
            print(f"❌ Service account setup failed: {result.stderr}")
            print("💡 Make sure MinIO is running and 'mc' is installed")
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout while checking MinIO - tests may fail")
    except FileNotFoundError:
        print("⚠️  MinIO client (mc) not found - service account setup skipped")
    except Exception as e:
        print(f"⚠️  Error during service account setup: {e}")


def mock_cli_settings():
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
    """Prevent CLI parsing at session start and ensure test prerequisites."""
    # Store original argv
    original_argv = sys.argv.copy()

    # Check and setup test service account if needed
    _ensure_test_service_account()

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
