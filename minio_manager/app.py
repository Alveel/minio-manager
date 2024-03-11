import sys
import time
from logging import DEBUG

from dotenv import find_dotenv, load_dotenv

from minio_manager.classes.config import ClusterResources
from minio_manager.clients import get_mc_wrapper, get_minio_config, get_secret_manager
from minio_manager.resource_handler import handle_resources
from minio_manager.utilities import init_debug, logger


def main():
    start_time = time.time()
    logger.info("Starting MinIO Manager...")

    # Load environment variables from .env file from the current working directory.
    logger.debug("Loading config.env file from current working directory...")
    de_loaded = load_dotenv(find_dotenv(filename="config.env", usecwd=True), override=True, verbose=True)

    if not de_loaded:
        logger.critical("Failed to load config.env file from current working directory!")
        sys.exit(1)
    if logger.level == DEBUG:
        init_debug()

    config = get_minio_config()

    logger.info("Loading and parsing resources...")
    cluster_resources = ClusterResources()
    cluster_resources.parse_resources(config.cluster_resources)

    logger.info("Loading secret backend...")
    secrets = get_secret_manager(config)
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
