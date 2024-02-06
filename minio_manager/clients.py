from __future__ import annotations

from minio import Minio, MinioAdmin, credentials

from minio_manager.classes.config import MinioConfig
from minio_manager.classes.mc_wrapper import McWrapper
from minio_manager.classes.secrets import SecretManager
from minio_manager.utilities import logger

config, s3_client, admin_client, mc_wrapper, secrets = None, None, None, None, None


def get_s3_client() -> Minio:
    """Set up MinIO S3 client for the specified cluster.

    Returns:
        Minio: MinIO S3 client

    """
    global s3_client
    if s3_client:
        return s3_client
    c = get_minio_config()
    s3_client = Minio(endpoint=c.endpoint, access_key=c.access_key, secret_key=c.secret_key, secure=c.secure)
    return s3_client


def get_minio_admin_client() -> MinioAdmin:
    """Set up MinIO Admin client

    Returns:
        MinioAdmin: MinIO Admin client
    """
    global admin_client
    if admin_client:
        return admin_client
    c = get_minio_config()
    provider = credentials.StaticProvider(c.access_key, c.secret_key)
    admin_client = MinioAdmin(endpoint=c.endpoint, credentials=provider, secure=c.secure)
    return admin_client


def get_mc_wrapper() -> McWrapper:
    """Set up 'mc' wrapper

    Returns:
        McWrapper: MinIO CLI client wrapper
    """
    global mc_wrapper
    if mc_wrapper:
        return mc_wrapper
    c = get_minio_config()
    mc_wrapper = McWrapper(config=c)
    return mc_wrapper


def get_secret_manager(c: MinioConfig) -> SecretManager:
    """Set up secret manager

    Args:
        c (MinioConfig): the MinIO server configuration

    Returns:
        SecretManager: the secret manager
    """
    global secrets
    if not secrets:
        secrets = SecretManager(c)
    return secrets


def get_minio_config():
    """Get the MinIO server configuration

    Returns:
        MinioConfig: the MinIO server configuration
    """
    global config
    if not config:
        logger.info("Configuring...")
        config = MinioConfig()
    return config
