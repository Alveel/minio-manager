import json
import time
from pathlib import Path

import yaml
from deepdiff import DeepDiff

error_count = 0
start_time = time.time()


def read_yaml(file: str | Path) -> dict:
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def compare_objects(a: dict, b: dict, ignore_order: bool = True) -> bool | dict:
    """Compare two dicts and return False if they match, the differences if they don't"""
    result = DeepDiff(a, b, ignore_order=ignore_order)
    if result:
        return result
    return False


def increment_error_count():
    global error_count
    error_count += 1


def get_error_count():
    return error_count
