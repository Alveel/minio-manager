from __future__ import annotations

from minio import Minio, MinioAdmin, credentials

from minio_manager.classes.controller_user import controller_user
from minio_manager.classes.mc_wrapper import mc_wrapper
from minio_manager.classes.settings import settings

s3_client = Minio(
    endpoint=settings.s3_endpoint,
    access_key=controller_user.access_key,
    secret_key=controller_user.secret_key,
    secure=settings.s3_endpoint_secure,
)
admin_provider = credentials.StaticProvider(controller_user.access_key, controller_user.secret_key)
admin_client = MinioAdmin(endpoint=settings.s3_endpoint, credentials=admin_provider, secure=settings.s3_endpoint_secure)
controller_user_policy = mc_wrapper.service_account_info(controller_user.access_key)["policy"]
