from .classes.minio_resources import MinioConfig
from .classes.secrets import SecretManager
from .cluster_handler import handle_cluster
from .utilities import setup_logging


def main():
    setup_logging()
    config = MinioConfig()
    secrets = SecretManager(config)
    run_user_credentials = secrets.get_credentials(config.controller_user)
    config.access_key = run_user_credentials.access_key
    config.secret_key = run_user_credentials.secret_key
    handle_cluster(config, secrets)
