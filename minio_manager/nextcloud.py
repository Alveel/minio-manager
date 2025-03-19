from pathlib import Path

from nc_py_api import FsNode, Nextcloud, NextcloudException

from minio_manager.classes.logging_config import logger
from minio_manager.classes.settings import settings

target_path: FsNode | None = None

if settings.nextcloud_url and settings.nextcloud_user and settings.nextcloud_pass:
    logger.debug(f"Logging in to Nextcloud instance at {settings.nextcloud_url}")
    try:
        nextcloud = Nextcloud(
            endpoint=settings.nextcloud_url, nc_auth_user=settings.nextcloud_user, nc_auth_pass=settings.nextcloud_pass
        )
        target_path = nextcloud.files.by_path(settings.nextcloud_path)
        if not isinstance(target_path, FsNode):
            logger.critical("Provided Nextcloud path not found")
    except NextcloudException as e:
        logger.critical(f"Error connecting to Nextcloud: {e}")


def nextcloud_upload(file: Path):
    """Upload a file to the Nextcloud instance."""
    with file.open("rb") as f:
        nextcloud.files.upload_stream(target_path, f)
