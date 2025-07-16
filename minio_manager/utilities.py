import json
import time
from pathlib import Path

import yaml

error_count = 0
start_time = time.time()


def read_yaml(file: str | Path) -> dict:
    with open(file) as f:
        return yaml.safe_load(f)


def read_json(file) -> dict:
    with open(file) as f:
        return json.load(f)


def normalize_policy(obj: dict) -> dict:
    """
    Normalize a policy by dumping and loading it with sorted keys
    to ensure consistent comparison.
    """
    return json.loads(json.dumps(obj, sort_keys=True))


def compare_objects(current: dict, desired: dict) -> bool:
    """
    Compare two JSON-compatible objects after normalizing.
    """
    return normalize_policy(current) == normalize_policy(desired)


def increment_error_count():
    global error_count
    error_count += 1


def get_error_count():
    return error_count
