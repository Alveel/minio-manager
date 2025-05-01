from __future__ import annotations

import json

from minio import Minio, MinioAdmin, credentials

from minio_manager import logger
from minio_manager.classes.controller_user import controller_user
from minio_manager.classes.settings import settings


class ClientManager:
    """
    Manages the MinIO S3 and Admin clients.

    This class provides functionality to initialize and manage the MinIO S3 client
    and the MinIO Admin client. It ensures that the clients are properly configured
    and reused when needed, reducing redundant initialization.
    The MinIO admin client allows executing administrative tasks on the MinIO server,
    such as creating and managing service accounts. This librari is exclusive to MinIO
    and not part of the S3 API.
    Also see: https://min.io/docs/minio/linux/reference/minio-mc-admin.html

    Attributes:
        s3 (Minio): The MinIO S3 client for interacting with the S3 API.
        _admin (MinioAdmin): The MinIO Admin client for performing administrative tasks.

    Methods:
        admin:
            A property that initializes and returns the MinIO Admin client if it is not already initialized.
    """

    s3: Minio
    _admin: MinioAdmin = None
    controller_user_policy: dict

    def __init__(self):
        self.s3 = Minio(
            endpoint=settings.s3_endpoint,
            access_key=controller_user.access_key,
            secret_key=controller_user.secret_key,
            secure=settings.s3_endpoint_secure,
        )

    @property
    def admin(self) -> MinioAdmin:
        if self._admin is not None:
            return self._admin

        logger.debug("Initialising admin client.")
        admin_provider = credentials.StaticProvider(controller_user.access_key, controller_user.secret_key)
        self._admin = MinioAdmin(
            endpoint=settings.s3_endpoint, credentials=admin_provider, secure=settings.s3_endpoint_secure
        )
        logger.debug("Admin client initialised.")
        self.controller_user_policy = self._setup_controller_user_policy()
        return self._admin

    def _setup_controller_user_policy(self) -> dict:
        """Get the S3 client."""
        logger.debug("Retrieving controller user policy from MinIO.")
        controller_user_info_raw = self._admin.get_service_account(controller_user.access_key)
        controller_user_dict = json.loads(controller_user_info_raw)
        controller_user_policy = json.loads(controller_user_dict["policy"])
        logger.debug("Retrieved controller user policy from MinIO.")
        return controller_user_policy


client_manager = ClientManager()
