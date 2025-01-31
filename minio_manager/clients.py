from __future__ import annotations

import json

from minio import Minio, MinioAdmin, credentials

from minio_manager.classes.controller_user import controller_user
from minio_manager.classes.settings import settings

s3_client = Minio(
    endpoint=settings.s3_endpoint,
    access_key=controller_user.access_key,
    secret_key=controller_user.secret_key,
    secure=settings.s3_endpoint_secure,
)
admin_provider = credentials.StaticProvider(controller_user.access_key, controller_user.secret_key)
admin_client = MinioAdmin(endpoint=settings.s3_endpoint, credentials=admin_provider, secure=settings.s3_endpoint_secure)
controller_user_info_raw = admin_client.get_service_account(controller_user.access_key)
controller_user = json.loads(controller_user_info_raw)
controller_user_policy = json.loads(controller_user["policy"])
