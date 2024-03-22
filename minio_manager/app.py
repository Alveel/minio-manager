import sys
import time

from minio_manager.classes.logging_config import logger
from minio_manager.classes.resource_parser import cluster_resources
from minio_manager.resource_handler import handle_resources
from minio_manager.utilities import error_count


def main():
    start_time = time.time()

    try:
        logger.info("Handling cluster resources...")
        handle_resources(cluster_resources)
        if error_count > 0:
            logger.error(f"Encountered {error_count} errors.")
            sys.exit(1)
    finally:
        from minio_manager.classes.mc_wrapper import mc_wrapper
        from minio_manager.classes.secrets import secrets

        secrets.cleanup()
        mc_wrapper.cleanup()
        end_time = time.time()
        logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
