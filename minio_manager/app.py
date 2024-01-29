import time

from dotenv import load_dotenv

from minio_manager.classes.config import parse_resources
from minio_manager.clients import get_minio_config
from minio_manager.resource_handler import handle_resources
from minio_manager.utilities import logger, read_yaml


def main():
    load_dotenv()
    logger.info("Starting MinIO Manager...")
    start_time = time.time()
    config = get_minio_config()
    cluster_config = read_yaml(config.cluster_resources)  # type: ClusterResources
    logger.info("Loading resources...")
    resources = parse_resources(cluster_config)
    logger.info("Handling cluster resources...")
    handle_resources(resources)
    end_time = time.time()
    logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
