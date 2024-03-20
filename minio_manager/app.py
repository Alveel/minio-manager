import time

from minio_manager.classes.logging_config import logger
from minio_manager.classes.resource_parser import cluster_resources
from minio_manager.resource_handler import handle_resources


def main():
    start_time = time.time()

    try:
        logger.info("Handling cluster resources...")
        handle_resources(cluster_resources)
    finally:
        from minio_manager.classes.mc_wrapper import mc_wrapper
        from minio_manager.classes.secrets import secrets

        secrets.cleanup()
        mc_wrapper.cleanup()
        end_time = time.time()
        logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
