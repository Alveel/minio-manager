#!/bin/bash

# Setup script to create the minio-manager controller service account
# This should be run before running tests to ensure the controller user exists

set -e

# MinIO admin credentials (root user)
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD="minioadmin"
MINIO_ENDPOINT="localhost:9000"

# Controller service account details (from secrets-insecure.yaml)
CONTROLLER_ACCESS_KEY="static-for-testing"
CONTROLLER_SECRET_KEY="static-secret-key-for-testing"

echo "Setting up MinIO controller service account for testing..."

# Check if mc (MinIO Client) is available
if ! command -v mc &> /dev/null; then
    echo "Error: MinIO Client (mc) is not installed or not in PATH"
    echo "Please install mc from https://docs.min.io/docs/minio-client-quickstart-guide.html"
    exit 1
fi

# Configure mc alias for the test instance
echo "Configuring mc alias..."
mc alias set testminio http://${MINIO_ENDPOINT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create controller service account with admin policy
echo "Creating controller service account..."

# Check if service account already exists
if mc admin user svcacct list testminio | grep -q ${CONTROLLER_ACCESS_KEY}; then
    echo "Service account ${CONTROLLER_ACCESS_KEY} already exists, removing it..."
    mc admin user svcacct remove testminio ${CONTROLLER_ACCESS_KEY} || true
fi

# Create the service account with admin policy
echo "Creating new service account with admin privileges..."
mc admin user svcacct add \
    --access-key ${CONTROLLER_ACCESS_KEY} \
    --secret-key ${CONTROLLER_SECRET_KEY} \
    testminio ${MINIO_ROOT_USER}

# Also need to create the controller user as a regular user first
echo "Creating controller user account..."
mc admin user add testminio local-test-controller temp-password-123

# Apply admin policy to the controller user
echo "Applying consoleAdmin policy to controller user..."
mc admin policy attach testminio consoleAdmin --user=local-test-controller

# Now create service account for the controller user
echo "Creating service account for controller user..."
mc admin user svcacct add \
    --access-key controller-sa-key \
    --secret-key controller-sa-secret \
    testminio local-test-controller

# Verify the service account was created
echo "Verifying service account creation..."
mc admin user svcacct list testminio minioadmin

echo "✅ Controller service account setup completed successfully!"
echo "Access Key: ${CONTROLLER_ACCESS_KEY}"
echo "Secret Key: ${CONTROLLER_SECRET_KEY}"
echo ""
echo "The minio-manager tests should now work with proper service account authentication."
