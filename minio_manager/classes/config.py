from __future__ import annotations

import json
from pathlib import Path

from minio.commonconfig import Filter
from minio.lifecycleconfig import Expiration, LifecycleConfig, NoncurrentVersionExpiration, Rule
from minio.versioningconfig import VersioningConfig as VeCo

from minio_manager.classes.minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount
from minio_manager.utilities import get_env_var, logger, read_yaml

default_bucket_versioning = get_env_var("MINIO_MANAGER_DEFAULT_BUCKET_VERSIONING", "Suspended")
default_bucket_lifecycle_policy = get_env_var("MINIO_MANAGER_DEFAULT_LIFECYCLE_POLICY", "")
default_bucket_create_service_account = get_env_var("MINIO_MANAGER_DEFAULT_BUCKET_CREATE_SERVICE_ACCOUNT", "True")
default_bucket_allowed_prefix = get_env_var("MINIO_MANAGER_ALLOWED_BUCKET_PREFIX", "")


class ClusterResources:
    """ClusterResources is the object containing all the cluster resources:

    - buckets
    - bucket_policies
    - service_accounts
    - iam_policies
    - iam_policy_attachments
    """

    buckets: list[Bucket]
    bucket_policies: list[BucketPolicy]
    service_accounts: list[ServiceAccount]
    iam_policies: list[IamPolicy]
    iam_policy_attachments: list[IamPolicyAttachment]

    def parse_buckets(self, buckets: list[dict]) -> list[Bucket]:
        """Parse the provided buckets with the following steps:
        For each provided bucket
            1. check the provided versioning. If versioning is not provided, set the default.
            2. check if an object lifecycle JSON file is provided, use the default_bucket_lifecycle_policy, or skip OLM
            3. parse the file and create a LifecycleConfig object for the bucket
            4. create a Bucket object

        Args:
            buckets: list of buckets to parse

        Returns:
            [Bucket]: list of Bucket objects
        """
        if not buckets:
            logger.info("No buckets configured, skipping.")
            return []

        bucket_objects = []
        try:
            for bucket in buckets:
                name = bucket["name"]
                if not name.startswith(default_bucket_allowed_prefix):
                    logger.error(f"Bucket {name} does not start with required prefix '{default_bucket_allowed_prefix}'")
                    continue

                versioning = bucket.get("versioning")
                versioning_config = VeCo(versioning) if versioning else VeCo(default_bucket_versioning)
                create_sa = bucket.get("create_service_account", bool(default_bucket_create_service_account))
                lifecycle_file = bucket.get("object_lifecycle_file", default_bucket_lifecycle_policy)
                lifecycle_config = self.parse_bucket_lifecycle_file(lifecycle_file)
                bucket_objects.append(Bucket(name, create_sa, versioning_config, lifecycle_config))
        except AttributeError:
            logger.info("No buckets configured, skipping.")

        return bucket_objects

    def parse_bucket_lifecycle_file(self, lifecycle_file: str) -> LifecycleConfig | None:
        """Parse a list of bucket lifecycle config files.
        The config files must be in JSON format and can be best obtained by running the following command:
            mc ilm rule export $cluster/$bucket > $policy_file.json

        Args:
            lifecycle_file: list of lifecycle config files

        Returns:
            LifecycleConfig object
        """
        if not lifecycle_file:
            return

        rules: list = []

        # TODO: E2E 5, catch and log FileNotFoundError and PermissionError
        with Path(lifecycle_file).open() as f:
            config_data = json.load(f)

        for rule_data in config_data["Rules"]:
            parsed_rule = self.parse_bucket_lifecycle_rule(rule_data)
            rules.append(parsed_rule)

        if not rules:
            return

        return LifecycleConfig(rules)

    @staticmethod
    def parse_bucket_lifecycle_rule(rule_data: dict) -> Rule:
        """Parse a single bucket object lifecycle rule
        TODO: implement date and days in Expiration, implement Transition, NoncurrentVersionTransition, Filter, and
          AbortIncompleteMultipartUpload

        Args:
            rule_data: dict with rule data

        Returns:
            Rule
        """
        rule_dict = {"status": rule_data.get("Status"), "rule_id": rule_data.get("ID")}

        expiration = rule_data.get("Expiration")
        if expiration:
            expire_delete_marker = expiration.get("ExpiredObjectDeleteMarker")
            rule_dict["expiration"] = Expiration(expired_object_delete_marker=expire_delete_marker)

        noncurrent_version_expiration = rule_data.get("NoncurrentVersionExpiration")
        if noncurrent_version_expiration:
            noncurrent_expire_days = noncurrent_version_expiration.get("NoncurrentDays")
            rule_dict["noncurrent_version_expiration"] = NoncurrentVersionExpiration(noncurrent_expire_days)

        # An empty filter is required for the rule to be valid
        rule_dict["rule_filter"] = Filter(prefix="")

        rule = Rule(**rule_dict)
        return rule

    @staticmethod
    def parse_bucket_policies(bucket_policies):
        if not bucket_policies:
            logger.info("No bucket policies configured, skipping.")
            return []

        bucket_policy_objects = []
        for bucket_policy in bucket_policies:
            bucket_policy_objects.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))

        return bucket_policy_objects

    @staticmethod
    def parse_service_accounts(service_accounts):
        if not service_accounts:
            logger.info("No service accounts configured, skipping.")
            return []

        service_account_objects = []
        for service_account in service_accounts:
            bucket = service_account.get("bucket")
            service_account_objects.append(ServiceAccount(service_account["name"], bucket))

        return service_account_objects

    @staticmethod
    def parse_iam_policy_attachments(iam_policy_attachments):
        if not iam_policy_attachments:
            logger.info("No IAM policy attachments configured, skipping.")
            return []

        iam_policy_attachment_objects = []
        for user in iam_policy_attachments:
            iam_policy_attachments.append(IamPolicyAttachment(user["username"], user["policies"]))

        return iam_policy_attachment_objects

    @staticmethod
    def parse_iam_policies(iam_policies):
        if not iam_policies:
            logger.info("No IAM policies configured, skipping.")
            return []

        iam_policy_objects = []
        for iam_policy in iam_policies:
            iam_policy_objects.append(IamPolicy(iam_policy["name"], iam_policy["policy_file"]))

        return iam_policy_objects

    def parse_resources(self, resources_file: dict):
        resources_file = read_yaml(resources_file)

        buckets = resources_file.get("buckets")
        self.buckets = self.parse_buckets(buckets)

        bucket_policies = resources_file.get("bucket_policies")
        self.bucket_policies = self.parse_bucket_policies(bucket_policies)

        service_accounts = resources_file.get("service_accounts")
        self.service_accounts = self.parse_service_accounts(service_accounts)

        iam_policies = resources_file.get("iam_policies")
        self.iam_policies = self.parse_iam_policies(iam_policies)

        iam_policy_attachments = resources_file.get("iam_policy_attachments")
        self.iam_policy_attachments = self.parse_iam_policy_attachments(iam_policy_attachments)


class MinioConfig:
    """MinioConfig is the MinIO server configuration object containing the connection details."""

    def __init__(self):
        self.name = get_env_var("MINIO_MANAGER_CLUSTER_NAME")
        self.endpoint = get_env_var("MINIO_MANAGER_S3_ENDPOINT")
        self.secure = get_env_var("MINIO_MANAGER_S3_ENDPOINT_SECURE", True)
        self.controller_user = get_env_var("MINIO_MANAGER_MINIO_CONTROLLER_USER")
        self.access_key = None
        self.secret_key = None
        self.cluster_resources = get_env_var("MINIO_MANAGER_CLUSTER_RESOURCES_FILE", "resources.yaml")
        self.secret_backend_type = get_env_var("MINIO_MANAGER_SECRET_BACKEND_TYPE")
        self.secret_s3_bucket = get_env_var("MINIO_MANAGER_SECRET_BACKEND_S3_BUCKET", "minio-manager-secrets")
