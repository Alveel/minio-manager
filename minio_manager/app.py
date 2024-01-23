import logging

from .classes.config import parse_resources
from .classes.minio_resources import MinioConfig
from .classes.secrets import SecretManager
from .resource_handler import handle_resources
from .utilities import read_yaml, setup_logging

logger = logging.getLogger("root")


def main():
    setup_logging()
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
    secrets.__del__()
