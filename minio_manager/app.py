import time

from dotenv import find_dotenv, load_dotenv

from minio_manager.classes.config import ClusterResources
from minio_manager.clients import get_minio_config, get_secret_manager
from minio_manager.resource_handler import handle_resources
from minio_manager.utilities import logger


def main():
    # Load environment variables from .env file from the current working directory.
    load_dotenv(find_dotenv(filename="config.env", usecwd=True), override=True, verbose=True)
    logger.info("Starting MinIO Manager...")
    start_time = time.time()
    config = get_minio_config()

    logger.info("Loading and parsing resources...")
    cluster_resources = ClusterResources()
    cluster_resources.parse_resources(config.cluster_resources)

    logger.info("Loading secret backend...")
    s = get_secret_manager(config)
    run_user_credentials = s.get_credentials(config.controller_user, required=True)
    config.access_key = run_user_credentials.access_key
    config.secret_key = run_user_credentials.secret_key

    try:
        logger.info("Handling cluster resources...")
        handle_resources(cluster_resources)
    finally:
        s.cleanup()
        end_time = time.time()
        logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
