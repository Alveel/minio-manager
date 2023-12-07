import json
import logging
import os

import yaml


def read_yaml(file):
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file):
    with open(file) as f:
        return json.load(f)


def setup_logging():
    log_debug = os.environ.get("LOG_LEVEL", "DEBUG")
    logger = logging.getLogger("root")
    if log_debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(format="[%(filename)s:%(lineno)d	- %(funcName)20s() ] %(message)s")
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
        policy["Statement"][index] = statement
    return policy
