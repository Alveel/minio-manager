import json
import logging
import os

import yaml

logger = logging.getLogger("root")


def read_yaml(file):
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def setup_logging():
    log_debug = os.environ.get("LOG_LEVEL", "DEBUG")
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


def retrieve_environment_variable(name: str) -> str:
    """
    Get an environment variable and strip any leading and trailing single and double quotes.
    This is because Python apparently literally loads them.
    Args:
        name: str, the name of the environment variable

    Returns: str stripped
    """
    variable = os.environ[name]
    strip_double_quotes = variable.strip('"')
    strip_single_quotes = strip_double_quotes.strip("'")
    return strip_single_quotes
