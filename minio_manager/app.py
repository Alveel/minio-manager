from minio_manager.classes.logging_config import logger
from minio_manager.classes.resource_parser import cluster_resources
from minio_manager.resource_handler import handle_resources


def main():
    try:
        logger.info("Handling cluster resources...")
        handle_resources(cluster_resources)
    finally:
        from minio_manager.classes.mc_wrapper import mc_wrapper
        from minio_manager.classes.secrets import secrets

        secrets.cleanup()
        mc_wrapper.cleanup()
