from __future__ import annotations

import json
import sys
from pathlib import Path

from minio.commonconfig import Filter
from minio.lifecycleconfig import Expiration, LifecycleConfig, NoncurrentVersionExpiration, Rule
from minio.versioningconfig import VersioningConfig as VeCo

from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount
from minio_manager.classes.settings import settings
from minio_manager.utilities import read_yaml


class ClusterResources:
    """
    ClusterResources is the object containing all the cluster resources:

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

    def parse_buckets(self, buckets: list) -> list[Bucket]:
        """
        Parse the provided buckets with the following steps:

        For each provided bucket

            1. check the provided versioning. If versioning is not provided, set the default.
            2. check if an object lifecycle JSON file is provided, use the default_bucket_lifecycle_policy, or skip OLM
            3. parse the file and create a LifecycleConfig object for the bucket
            4. create a Bucket object

        Args:
            buckets: list of buckets to parse

        Returns: [Bucket]: list of Bucket objects
        """
        if not buckets:
            logger.debug("No buckets configured, skipping.")
            return []

        bucket_objects = []

        lifecycle_config = self.parse_bucket_lifecycle_file(settings.default_lifecycle_policy_file)
        bucket_names = []

        try:
            logger.debug(f"Parsing {len(buckets)} buckets...")
            if settings.allowed_bucket_prefixes:
                logger.info(f"Only allowing buckets with the following prefixes: {settings.allowed_bucket_prefixes}")
            for bucket in buckets:
                name = bucket["name"]
                if name in bucket_names:
                    logger.error(f"Bucket '{name}' defined multiple times. Stopping.")
                    sys.exit(1)
                logger.debug(f"Parsing bucket {name}")
                allowed_prefixes = settings.allowed_bucket_prefixes
                if allowed_prefixes and not name.startswith(allowed_prefixes):
                    logger.error(
                        f"Bucket '{name}' does not start with one of the required prefixes {allowed_prefixes}!"
                    )
                    sys.exit(1)

                bucket_names.append(name)
                versioning = bucket.get("versioning")
                try:
                    versioning_config = VeCo(versioning) if versioning else VeCo(settings.default_bucket_versioning)
                except ValueError as ve:
                    logger.error(f"Error parsing versioning setting: {' '.join(ve.args)}")
                    sys.exit(1)
                create_sa = bool(bucket.get("create_service_account", settings.default_bucket_versioning))
                lifecycle_file = bucket.get("object_lifecycle_file")
                if lifecycle_file:
                    bucket_lifecycle = self.parse_bucket_lifecycle_file(lifecycle_file)
                    if isinstance(bucket_lifecycle, LifecycleConfig):
                        lifecycle_config = bucket_lifecycle
                bucket_objects.append(Bucket(name, create_sa, versioning_config, lifecycle_config))
        except TypeError:
            logger.error("Buckets must be defined as a list of YAML dictionaries!")
            sys.exit(1)

        return bucket_objects

    def parse_bucket_lifecycle_file(self, lifecycle_file: str) -> LifecycleConfig | None:
        """
        Parse a bucket lifecycle config file.

        The config files must be in JSON format and can be best obtained by running the following command:
            mc ilm rule export $cluster/$bucket > $policy_file.json

        Args:
            lifecycle_file: lifecycle config file

        Returns: LifecycleConfig object
        """
        if not lifecycle_file:
            return

        rules: list = []

        try:
            with Path(lifecycle_file).open() as f:
                config_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Lifecycle file {lifecycle_file} not found, skipping configuration.")
            sys.exit(1)
        except PermissionError:
            logger.error(f"Incorrect file permissions on {lifecycle_file}, skipping configuration.")
            sys.exit(1)

        try:
            rules_dict = config_data["Rules"]
        except KeyError:
            logger.error(f"Lifecycle file {lifecycle_file} is missing the required 'Rules' key.")
            sys.exit(1)

        try:
            for rule_data in rules_dict:
                parsed_rule = self.parse_bucket_lifecycle_rule(rule_data)
                rules.append(parsed_rule)
        except AttributeError:
            logger.error(f"Error parsing lifecycle file {lifecycle_file}. Is the format correct?")
            sys.exit(1)

        if not rules:
            return

        return LifecycleConfig(rules)

    @staticmethod
    def parse_bucket_lifecycle_rule(rule_data: dict) -> Rule:
        """
        Parse a single bucket object lifecycle rule.

        TODO:
          Implement date and days in Expiration, implement Transition, NoncurrentVersionTransition, Filter, and
          AbortIncompleteMultipartUpload

        Args:
            rule_data: dict with rule data

        Returns: Rule object
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
    def parse_bucket_policies(bucket_policies: list):
        """
        Parse a list of bucket policy definitions into BucketPolicy objects.

        Args:
            bucket_policies: list of bucket policies

        Returns: [BucketPolicy]
        """
        if not bucket_policies:
            logger.debug("No bucket policies configured, skipping.")
            return []

        bucket_policy_objects = []
        try:
            logger.debug(f"Parsing {len(bucket_policies)} bucket policies...")
            for bucket_policy in bucket_policies:
                bucket_policy_objects.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))
        except TypeError:
            logger.error("Bucket policies must be defined as a list of YAML dictionaries!")
            sys.exit(1)

        return bucket_policy_objects

    @staticmethod
    def parse_service_accounts(service_accounts: list):
        """
        Parse a list of service account definitions into ServiceAccount objects.

        Args:
            service_accounts: dict of service accounts

        Returns: [ServiceAccount]
        """
        if not service_accounts:
            logger.debug("No service accounts configured, skipping.")
            return []

        service_account_objects, service_account_names = [], []

        try:
            logger.debug(f"Parsing {len(service_accounts)} service accounts...")
            for service_account in service_accounts:
                name = service_account["name"]
                if name in service_account_names:
                    logger.error(f"Service account '{name}' defined multiple times. Stopping.")
                    sys.exit(1)
                service_account_names.append(name)
                policy_file = service_account.get("policy_file")
                sa_obj = ServiceAccount(name=name, policy_file=policy_file)
                service_account_objects.append(sa_obj)
        except TypeError:
            logger.error("Service accounts must be defined as a list of YAML dictionaries!")
            sys.exit(1)

        return service_account_objects

    @staticmethod
    def parse_iam_attachments(iam_policy_attachments: list):
        """
        Parse a list of IAM policy attachment definitions into IamPolicyAttachment objects.

        Args:
            iam_policy_attachments: dict of IAM policy attachments

        Returns: [IamPolicyAttachment]
        """
        if not iam_policy_attachments:
            logger.debug("No IAM policy attachments configured, skipping.")
            return []

        iam_policy_attachment_objects = []
        try:
            logger.debug(f"Parsing {len(iam_policy_attachments)} IAM policy attachments...")
            for user in iam_policy_attachments:
                iam_policy_attachments.append(IamPolicyAttachment(user["username"], user["policies"]))
        except TypeError:
            logger.error("IAM policy attachments must be defined as a list of YAML dictionaries!")
            sys.exit(1)

        return iam_policy_attachment_objects

    @staticmethod
    def parse_iam_policies(iam_policies: dict):
        """
        Parse a list of IAM policy definitions into IamPolicy objects.

        Args:
            iam_policies: dict of IAM policies

        Returns: [IamPolicy]
        """
        if not iam_policies:
            logger.debug("No IAM policies configured, skipping.")
            return []

        iam_policy_objects, iam_policy_names = [], []
        try:
            logger.debug(f"Parsing {len(iam_policies)} IAM policies...")
            for iam_policy in iam_policies:
                name = iam_policy["name"]
                if name in iam_policy_names:
                    logger.error(f"IAM policy '{name}' defined multiple times. Stopping.")
                    sys.exit(1)
                iam_policy_names.append(name)
                iam_policy_objects.append(IamPolicy(name, iam_policy["policy_file"]))
        except TypeError:
            logger.error("IAM policies must be defined as a list of YAML dictionaries!")
            sys.exit(1)

        return iam_policy_objects

    def parse_resources(self, resources_file: str):
        """
        Parse resources from a YAML file, ensuring they are valid before trying to use them.

        Args:
            resources_file: string path to the YAML file
        """
        logger.info("Loading and parsing resources...")

        try:
            resources = read_yaml(resources_file)
        except FileNotFoundError:
            logger.error(f"Resources file {resources_file} not found. Stopping.")
            sys.exit(1)
        except PermissionError:
            logger.error(f"Incorrect file permissions on {resources_file}. Stopping.")
            sys.exit(1)

        if not resources:
            logger.error("Is the resources file empty?")
            sys.exit(1)

        buckets = resources.get("buckets")
        self.buckets = self.parse_buckets(buckets)

        bucket_policies = resources.get("bucket_policies")
        self.bucket_policies = self.parse_bucket_policies(bucket_policies)

        service_accounts = resources.get("service_accounts")
        self.service_accounts = self.parse_service_accounts(service_accounts)

        iam_policies = resources.get("iam_policies")
        self.iam_policies = self.parse_iam_policies(iam_policies)

        iam_policy_attachments = resources.get("iam_policy_attachments")
        self.iam_policy_attachments = self.parse_iam_attachments(iam_policy_attachments)

        if not any([buckets, bucket_policies, service_accounts, iam_policies, iam_policy_attachments]):
            logger.warning("No resources configured.")
            sys.exit(0)


cluster_resources = ClusterResources()
cluster_resources.parse_resources(settings.cluster_resources_file)
