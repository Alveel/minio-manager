import json
import logging
import os
from typing import Union

import yaml
from minio import Minio, MinioAdmin, credentials

logger = logging.getLogger("root")


def read_yaml(file):
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def setup_logging():
    log_debug = os.environ.get("MINIO_MANAGER_LOG_LEVEL", "INFO")
    if log_debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(format="[%(asctime)s [%(filename)s:%(lineno)d	- %(funcName)24s() ] %(message)s")
    else:
        logger.setLevel(logging.INFO)
        logging.basicConfig(format="%(message)s")

    logger.debug("Initialising")


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


def retrieve_environment_variable(name: str, default=None) -> Union[str, bool]:
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
