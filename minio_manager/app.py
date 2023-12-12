import os

from cluster_handler import handle_cluster
from secret_manager import SecretManager
from utilities import read_yaml, setup_logging


def main():
    setup_logging()
    config_file = os.getenv("MINIO_MANAGER_CONFIG_FILE", "config.yaml")
    config = read_yaml(config_file)
    secrets = SecretManager(config.name, config.secret_backend)
    handle_cluster(config, secrets)


if __name__ == "__main__":  # pragma: no cover
    main()
