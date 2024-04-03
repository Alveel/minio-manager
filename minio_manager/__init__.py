# Initialise settings and logging
# ruff: noqa: I001
from minio_manager.classes.settings import settings as settings
from minio_manager.classes.logging_config import logger as logger
from minio_manager.utilities import start_time as start_time

logger.info("Starting MinIO Manager...")
