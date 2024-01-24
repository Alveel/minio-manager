import json
import logging
import os

import yaml
from minio import Minio, MinioAdmin, credentials

global logger


def read_yaml(file):
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def setup_logging():
    if log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(format="[%(asctime)s [%(filename)-26s:%(lineno)-4d - %(funcName)-24s ] %(message)s")
    else:
        logger.setLevel(logging.INFO)
        logging.basicConfig(format="[%(asctime)s] %(message)s")

    logger.debug(f"Initialising with log level: {log_level}")


def sort_policy(policy: dict):
    """

    Args:
        policy: dict
            MinIO policy documents use the same schema as AWS IAM Policy documents.
            https://docs.aws.amazon.com/IAM/latest/UserGuide/access.html

    Returns: dict with sorted Actions and Resources
    """
    for index, statement in enumerate(policy["Statement"]):
        statement["Action"] = sorted(statement["Action"])
        statement["Resource"] = sorted(statement["Resource"])
        # TODO: also sort Principals
        statement = dict(sorted(statement.items()))
        policy["Statement"][index] = statement
    return policy


def retrieve_environment_variable(name: str, default=None) -> str:
    """
    Get an environment variable and strip any leading and trailing single and double quotes.
    This is because Python apparently literally loads them.
    Args:
        default: str, default if not set
        name: str, the name of the environment variable

    Returns: str stripped
    """
    try:
        variable = os.environ[name]
        strip_double_quotes = variable.strip('"')
        return strip_double_quotes.strip("'")
    except KeyError:
        if not default:
            logger.critical(f"Required environment variable {name} not found!")
            exit(1)

    return default


def setup_s3_client(endpoint, access_key, secret_key, secure=True) -> Minio:
    """Set up MinIO S3 client for the specified cluster.

    Args:
        endpoint: str
        access_key: str
        secret_key: str
        secure: bool

    Returns:
        Minio S3 client object

    """
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def setup_minio_admin_client(endpoint, access_key, secret_key, secure=True) -> MinioAdmin:
    provider = credentials.StaticProvider(access_key, secret_key)
    return MinioAdmin(endpoint, provider, secure=secure)


log_level = retrieve_environment_variable("MINIO_MANAGER_LOG_LEVEL", "INFO")
logger = logging.getLogger("minio-manager") if log_level != "DEBUG" else logging.getLogger("root")
