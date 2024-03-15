import time

from minio_manager.classes.logging_config import logger
from minio_manager.classes.resource_parser import ClusterResources
from minio_manager.clients import get_mc_wrapper, get_minio_config, get_secret_manager
from minio_manager.resource_handler import handle_resources


def main():
    start_time = time.time()
    logger.info("Starting MinIO Manager...")

    config = get_minio_config()

    logger.info("Loading and parsing resources...")
    cluster_resources = ClusterResources()
    cluster_resources.parse_resources(config.cluster_resources)

    logger.info("Loading secret backend...")
    secrets = get_secret_manager()
    run_user_credentials = secrets.get_credentials(config.controller_user, required=True)
    config.access_key = run_user_credentials.access_key
    config.secret_key = run_user_credentials.secret_key

    try:
        logger.info("Handling cluster resources...")
        handle_resources(cluster_resources)
    finally:
        secrets.cleanup()
        get_mc_wrapper().cleanup()
        end_time = time.time()
        logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
