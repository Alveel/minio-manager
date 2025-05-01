from minio_manager.classes.logging_config import logger
from minio_manager.classes.resource_parser import cluster_resources
from minio_manager.classes.settings import settings
from minio_manager.resource_handler import handle_resources


def main():
    try:
        logger.info(f"Running MinIO Manager against cluster '{settings.s3_endpoint}'")
        cluster_resources.parse_resources(settings.cluster_resources_file)
        if settings.dry_run:
            logger.info("Dry run mode enabled. No changes will be made.")
            return

        logger.info("Applying cluster resources...")
        handle_resources(cluster_resources)
    finally:
        from minio_manager.classes.secrets import secrets

        # Cleanup functions must be idempotent.
        secrets.cleanup()
