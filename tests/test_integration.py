"""Integration tests for MinIO Manager functionality."""

import json
from pathlib import Path

from minio import Minio
from minio.lifecycleconfig import Expiration, Filter, LifecycleConfig, NoncurrentVersionExpiration, Rule
from minio.versioningconfig import VersioningConfig

from tests.conftest import requires_minio


@requires_minio
class TestIntegrationScenarios:
    """Test full integration scenarios combining buckets, policies, and lifecycle configurations."""

    def test_complete_bucket_setup(
        self, minio_client: Minio, test_bucket_name: str, temp_policy_file: Path, cleanup_bucket
    ):
        """Test complete bucket setup with versioning, lifecycle, and policy."""
        cleanup_bucket(test_bucket_name)

        # Step 1: Create bucket
        minio_client.make_bucket(test_bucket_name)
        assert minio_client.bucket_exists(test_bucket_name)

        # Step 2: Enable versioning
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        current_versioning = minio_client.get_bucket_versioning(test_bucket_name)
        assert current_versioning.status == "Enabled"

        # Step 3: Set lifecycle configuration
        rule = Rule(
            rule_id="CompleteSetupRule",
            rule_filter=Filter(prefix=""),
            status="Enabled",
            expiration=Expiration(days=365),
            noncurrent_version_expiration=NoncurrentVersionExpiration(noncurrent_days=30),
        )
        lifecycle_config = LifecycleConfig([rule])
        minio_client.set_bucket_lifecycle(test_bucket_name, lifecycle_config)

        current_lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(current_lifecycle.rules) == 1
        assert current_lifecycle.rules[0].rule_id == "CompleteSetupRule"

        # Step 4: Set bucket policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowPublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))

        current_policy_str = minio_client.get_bucket_policy(test_bucket_name)
        current_policy = json.loads(current_policy_str)
        assert current_policy["Statement"][0]["Sid"] == "AllowPublicRead"

        # Verify everything is still configured correctly
        assert minio_client.bucket_exists(test_bucket_name)
        assert minio_client.get_bucket_versioning(test_bucket_name).status == "Enabled"
        assert len(minio_client.get_bucket_lifecycle(test_bucket_name).rules) == 1
        assert json.loads(minio_client.get_bucket_policy(test_bucket_name))["Version"] == "2012-10-17"

    def test_bucket_with_object_operations(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test bucket operations with actual objects."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning
        minio_client.make_bucket(test_bucket_name)
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Upload test objects
        test_objects = [
            ("test1.txt", b"Hello World 1"),
            ("test2.txt", b"Hello World 2"),
            ("folder/test3.txt", b"Hello World 3"),
        ]

        for obj_name, obj_data in test_objects:
            from io import BytesIO

            minio_client.put_object(test_bucket_name, obj_name, BytesIO(obj_data), len(obj_data))

        # Verify objects exist
        objects = list(minio_client.list_objects(test_bucket_name, recursive=True))
        object_names = [obj.object_name for obj in objects]

        assert "test1.txt" in object_names
        assert "test2.txt" in object_names
        assert "folder/test3.txt" in object_names

        # Test object retrieval
        response = minio_client.get_object(test_bucket_name, "test1.txt")
        data = response.read()
        assert data == b"Hello World 1"
        response.close()
        response.release_conn()

        # Upload new version of same object
        minio_client.put_object(
            test_bucket_name, "test1.txt", BytesIO(b"Hello World 1 - Updated"), len(b"Hello World 1 - Updated")
        )

        # Verify we can still get the object (latest version)
        response = minio_client.get_object(test_bucket_name, "test1.txt")
        data = response.read()
        assert data == b"Hello World 1 - Updated"
        response.close()
        response.release_conn()

    def test_lifecycle_policy_interaction(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test interaction between lifecycle policies and bucket operations."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with versioning (required for some lifecycle rules)
        minio_client.make_bucket(test_bucket_name)
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Set up lifecycle policy for different prefixes
        rules = [
            Rule(
                rule_id="ArchiveLogs",
                rule_filter=Filter(prefix="logs/"),
                status="Enabled",
                expiration=Expiration(days=30),
            ),
            Rule(
                rule_id="ArchiveTemp",
                rule_filter=Filter(prefix="temp/"),
                status="Enabled",
                expiration=Expiration(days=7),
            ),
            Rule(
                rule_id="ArchiveGeneral",
                rule_filter=Filter(prefix=""),
                status="Enabled",
                expiration=Expiration(days=365),
                noncurrent_version_expiration=NoncurrentVersionExpiration(noncurrent_days=90),
            ),
        ]
        lifecycle_config = LifecycleConfig(rules)
        minio_client.set_bucket_lifecycle(test_bucket_name, lifecycle_config)

        # Upload objects with different prefixes
        test_objects = [
            ("logs/app.log", b"Log data"),
            ("temp/scratch.txt", b"Temporary data"),
            ("data/important.txt", b"Important data"),
        ]

        for obj_name, obj_data in test_objects:
            from io import BytesIO

            minio_client.put_object(test_bucket_name, obj_name, BytesIO(obj_data), len(obj_data))

        # Verify all objects are present
        objects = list(minio_client.list_objects(test_bucket_name, recursive=True))
        object_names = [obj.object_name for obj in objects]

        assert "logs/app.log" in object_names
        assert "temp/scratch.txt" in object_names
        assert "data/important.txt" in object_names

        # Verify lifecycle configuration is still active
        current_lifecycle = minio_client.get_bucket_lifecycle(test_bucket_name)
        assert len(current_lifecycle.rules) == 3

        rule_ids = [rule.rule_id for rule in current_lifecycle.rules]
        assert "ArchiveLogs" in rule_ids
        assert "ArchiveTemp" in rule_ids
        assert "ArchiveGeneral" in rule_ids

    def test_policy_and_access_control(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test bucket policy and access control scenarios."""
        cleanup_bucket(test_bucket_name)

        # Create bucket
        minio_client.make_bucket(test_bucket_name)

        # Set restrictive policy (deny by default, allow only specific actions)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowReadOnly",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}", f"arn:aws:s3:::{test_bucket_name}/*"],
                },
                {
                    "Sid": "DenyWrite",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": ["s3:PutObject", "s3:DeleteObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                    "Condition": {"StringNotEquals": {"aws:userid": "minio"}},
                },
            ],
        }

        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))

        # Verify policy is set
        current_policy_str = minio_client.get_bucket_policy(test_bucket_name)
        current_policy = json.loads(current_policy_str)

        assert len(current_policy["Statement"]) == 2

        # Find the statements by Sid
        allow_stmt = None
        deny_stmt = None
        for stmt in current_policy["Statement"]:
            if stmt["Sid"] == "AllowReadOnly":
                allow_stmt = stmt
            elif stmt["Sid"] == "DenyWrite":
                deny_stmt = stmt

        assert allow_stmt is not None
        assert deny_stmt is not None

        # Verify allow statement
        assert allow_stmt["Effect"] == "Allow"
        assert "s3:GetObject" in allow_stmt["Action"]
        assert "s3:ListBucket" in allow_stmt["Action"]

        # Verify deny statement
        assert deny_stmt["Effect"] == "Deny"
        assert "s3:PutObject" in deny_stmt["Action"]
        assert "s3:DeleteObject" in deny_stmt["Action"]

    def test_bucket_cleanup_and_teardown(self, minio_client: Minio, test_bucket_name: str, cleanup_bucket):
        """Test complete cleanup of bucket with all configurations."""
        cleanup_bucket(test_bucket_name)

        # Create bucket with full configuration
        minio_client.make_bucket(test_bucket_name)

        # Set versioning
        versioning_config = VersioningConfig("Enabled")
        minio_client.set_bucket_versioning(test_bucket_name, versioning_config)

        # Set lifecycle
        rule = Rule(
            rule_id="TestCleanup", rule_filter=Filter(prefix=""), status="Enabled", expiration=Expiration(days=30)
        )
        lifecycle_config = LifecycleConfig([rule])
        minio_client.set_bucket_lifecycle(test_bucket_name, lifecycle_config)

        # Set policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "TestPolicy",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{test_bucket_name}/*"],
                }
            ],
        }
        minio_client.set_bucket_policy(test_bucket_name, json.dumps(policy))

        # Add some objects
        from io import BytesIO

        for i in range(3):
            minio_client.put_object(
                test_bucket_name,
                f"test-object-{i}.txt",
                BytesIO(f"Test data {i}".encode()),
                len(f"Test data {i}".encode()),
            )

        # Verify everything is configured
        assert minio_client.bucket_exists(test_bucket_name)
        assert minio_client.get_bucket_versioning(test_bucket_name).status == "Enabled"
        assert len(minio_client.get_bucket_lifecycle(test_bucket_name).rules) == 1
        assert minio_client.get_bucket_policy(test_bucket_name) is not None

        objects = list(minio_client.list_objects(test_bucket_name))
        assert len(objects) == 3

        # Test the cleanup process (this will be done by the fixture)
        # But let's verify we can clean up manually too

        # Remove objects and all versions
        for obj in minio_client.list_objects(test_bucket_name, recursive=True):
            minio_client.remove_object(test_bucket_name, obj.object_name)

        # Also remove any object versions if versioning was enabled
        try:
            for obj in minio_client.list_objects(test_bucket_name, recursive=True, include_version=True):
                minio_client.remove_object(test_bucket_name, obj.object_name, version_id=obj.version_id)
        except Exception:
            pass  # May not have versions or versioning support

        # Remove configurations (optional - bucket deletion will clean these up)
        try:
            minio_client.delete_bucket_policy(test_bucket_name)
            minio_client.delete_bucket_lifecycle(test_bucket_name)
        except Exception:
            pass  # These might not exist or might be cleaned up automatically

        # Remove bucket
        minio_client.remove_bucket(test_bucket_name)

        # Verify bucket is gone
        assert not minio_client.bucket_exists(test_bucket_name)
