from __future__ import annotations

import json

from minio import Minio, MinioAdmin, credentials

from minio_manager import logger
from minio_manager.classes.controller_user import controller_user
from minio_manager.classes.settings import settings

s3_client = Minio(
    endpoint=settings.s3_endpoint,
    access_key=controller_user.access_key,
    secret_key=controller_user.secret_key,
    secure=settings.s3_endpoint_secure,
)
# The admin client allows executing administrative tasks on the MinIO server, such as creating and managing service accounts.
# The MinIO Admin client is exclusive to MinIO and not part of the S3 API.
# Also see: https://min.io/docs/minio/linux/reference/minio-mc-admin.html
admin_client = None  # type: MinioAdmin | None
controller_user_policy = {}


def get_admin_client() -> MinioAdmin:
    """Get the S3 client."""
    global admin_client

    if admin_client:
        logger.debug("Reusing existing admin client.")
        return admin_client

    logger.debug("Initialising admin client.")
    admin_provider = credentials.StaticProvider(controller_user.access_key, controller_user.secret_key)
    admin_client = MinioAdmin(
        endpoint=settings.s3_endpoint, credentials=admin_provider, secure=settings.s3_endpoint_secure
    )
    logger.debug("Admin client initialised.")
    return admin_client


def get_controller_user_policy() -> dict:
    """Get the S3 client."""
    global admin_client, controller_user_policy

    if admin_client and controller_user_policy:
        logger.debug("Retrieving controller user policy from cache.")
        return controller_user_policy

    logger.debug("Retrieving controller user policy from MinIO.")
    controller_user_info_raw = admin_client.get_service_account(controller_user.access_key)
    controller_user_dict = json.loads(controller_user_info_raw)
    controller_user_policy = json.loads(controller_user_dict["policy"])
    logger.debug("Retrieved controller user policy from MinIO.")
    return controller_user_policy
