import os

from cluster_handler import handle_cluster
from utilities import read_yaml, setup_logging


def main():
    setup_logging()
    config_file = os.getenv("MINIO_MANAGER_CONFIG_FILE", "config.yaml")
    config = read_yaml(config_file)
    for cluster in config["minio"]:
        handle_cluster(cluster)


if __name__ == "__main__":  # pragma: no cover
    main()
