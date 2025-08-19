"""Simple test to verify test environment works."""

import json
import tempfile
from pathlib import Path


def test_simple_json_operation():
    """Test basic JSON operations without importing minio_manager."""
    test_data = {"key": "value", "number": 42}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        temp_path = Path(f.name)

    try:
        with open(temp_path) as f:
            result = json.load(f)

        assert result == test_data
        assert result["key"] == "value"
        assert result["number"] == 42
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_basic_import():
    """Test that we can import basic Python modules."""
    import json
    import tempfile
    from pathlib import Path

    assert json is not None
    assert tempfile is not None
    assert Path is not None


if __name__ == "__main__":
    test_simple_json_operation()
    test_basic_import()
    print("All basic tests passed!")
