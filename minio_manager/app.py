import time

from dotenv import load_dotenv

from .classes.config import parse_resources
from .classes.minio_resources import MinioConfig
from .classes.secrets import SecretManager
from .resource_handler import handle_resources
from .utilities import logger, read_yaml, setup_logging


def main():
    load_dotenv()
    setup_logging()
    start_time = time.time()
    config = MinioConfig()
    cluster_config = read_yaml(config.cluster_resources)  # type: ClusterResources

    logger.info("Loading resources...")
    resources = parse_resources(cluster_config)
    logger.info("Loading secret manager...")
    secrets = SecretManager(config)
    logger.info("Retrieving controller user credentials...")
    run_user_credentials = secrets.get_credentials(config.controller_user)
    config.access_key = run_user_credentials.access_key
    config.secret_key = run_user_credentials.secret_key
    logger.info("Handling cluster resources...")
    handle_resources(config, secrets, resources)
    end_time = time.time()
    logger.info(f"Execution took {end_time - start_time:.2f} seconds.")
