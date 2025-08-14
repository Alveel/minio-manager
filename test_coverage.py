#!/usr/bin/env python3
"""Simple script to test coverage improvements."""

import subprocess
import sys
import os

# Change to the project directory
project_dir = "/Users/ewelder/Git_NA/minio-manager/minio-manager-python"
os.chdir(project_dir)

# Set up environment
venv_python = os.path.join(project_dir, ".venv", "bin", "python")

print("🧪 Testing new handler tests...")

# Test the new test files
test_files = [
    "tests/test_bucket_handler.py",
    "tests/test_policy_handler.py", 
    "tests/test_service_account_handler.py"
]

print(f"Testing files: {test_files}")

try:
    # Run coverage on the new tests
    result = subprocess.run([
        venv_python, "-m", "pytest", 
        *test_files,
        "--cov=minio_manager.bucket_handler",
        "--cov=minio_manager.policy_handler", 
        "--cov=minio_manager.service_account_handler",
        "--cov-report=term-missing",
        "--tb=short",
        "-x"  # Stop on first failure
    ], capture_output=True, text=True, timeout=120)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")

except subprocess.TimeoutExpired:
    print("Test execution timed out")
except Exception as e:
    print(f"Error running tests: {e}")
