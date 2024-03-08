import json
import logging
import os
from pathlib import Path

import yaml
from deepdiff import DeepDiff

from minio_manager.classes.logging_config import MinioManagerLogger

logger = logging.getLogger("root")
logger_setup = False  # whether the logger is already configured or not
module_directory = os.path.dirname(__file__)


def read_yaml(file: str | Path) -> dict:
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def setup_logging():
    global logger
    log_level = get_env_var("MINIO_MANAGER_LOG_LEVEL", "INFO")
    log_name = "root" if log_level == "DEBUG" else "minio-manager"
    logger = MinioManagerLogger(log_name, log_level)
    logger.debug(f"Configured log level: {log_level}")


def compare_objects(a: dict, b: dict, ignore_order: bool = True) -> bool | dict:
    """Compare two dicts and return False if they match, the differences if they don't"""
    result = DeepDiff(a, b, ignore_order=ignore_order)
    if result:
        return result
    return False


def get_env_var(name: str, default=None) -> str:
    """
    Get an environment variable and strip any leading and trailing single and double quotes.
    This is because Python literally loads them.

    Args:
        name: str, the name of the environment variable
        default: str, default if not set

    Returns: str stripped
    """
    try:
        variable = os.environ[name]
        strip_double_quotes = variable.strip('"')
        return strip_double_quotes.strip("'")
    except KeyError:
        if default is None:
            logger.critical(f"Required environment variable {name} not found!")
            exit(1)

    return default


if not logger_setup:
    setup_logging()
    logger_setup = True


def init_debug():
    logger.debug("Current working directory: " + os.getcwd())
    logger.debug("Configured environment variables:")

    for env in os.environ:
        if env.startswith("MINIO_MANAGER_"):
            logger.debug(f"{env}: {os.environ[env]}")
