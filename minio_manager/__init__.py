# Initialise settings and logging
# ruff: noqa: I001
from pathlib import Path

from minio_manager.classes.settings import settings as settings
from minio_manager.classes.logging_config import logger as logger
from minio_manager.utilities import start_time as start_time

logger.info("Starting MinIO Manager...")
if not settings.s3_endpoint_secure:
    logger.warning("Using an insecure connection to MinIO. This is not recommended for production environments.")
sapbf = settings.service_account_policy_base_file
if sapbf and not Path(settings.service_account_policy_base_file).is_file():
    logger.critical(f"Provided base policy file '{settings.service_account_policy_base_file}' not found.")
    logger.critical("Either provide a valid base policy file, or leave this option empty.")
