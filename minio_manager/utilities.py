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


def normalize_policy(obj):
    """
    Recursively sort all dictionaries and lists in a JSON-compatible object.
    This ensures consistent structure for accurate comparisons.
    """
    if isinstance(obj, dict):
        return {k: normalize_policy(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        # Sort list items but handle mixed types gracefully
        try:
            return sorted((normalize_policy(item) for item in obj), key=lambda x: json.dumps(x, sort_keys=True))
        except TypeError:
            # If items aren't comparable, just normalize them without sorting
            return [normalize_policy(item) for item in obj]
    else:
        return obj


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
