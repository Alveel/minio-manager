import logging
import os

import yaml


def read_yaml(file):
    with open(file) as f:
        return yaml.safe_load(f)


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
