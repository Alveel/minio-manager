from cluster_handler import handle_cluster
from utilities import read_yaml, setup_logging


def main():
    setup_logging()
    config = read_yaml("config.yaml")
    for cluster in config["minio"]:
        handle_cluster(cluster)


if __name__ == "__main__":  # pragma: no cover
    main()
