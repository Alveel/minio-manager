from .classes.secrets import SecretManager
from .cluster_handler import handle_cluster
from .utilities import read_yaml, retrieve_environment_variable, setup_logging


def main():
    setup_logging()
    config_file = retrieve_environment_variable("MINIO_MANAGER_CONFIG_FILE", "config.yaml")
    config = read_yaml(config_file)  # type: MinioConfig
    secrets = SecretManager(config.name, config.secret_backend)
    run_user_credentials = secrets.get_credentials(retrieve_environment_variable("MINIO_MANAGER_USER_NAME"))
    config.access_key = run_user_credentials.access_key
    config.secret_key = run_user_credentials.secret_key
    handle_cluster(config, secrets)


if __name__ == "__main__":  # pragma: no cover
    main()
