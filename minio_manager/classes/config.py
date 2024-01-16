import yaml

from .minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount


class ClusterConfig(yaml.YAMLObject):
    """MinIO Cluster configuration object, aka the cluster contents: buckets, policies, etc."""

    yaml_tag = "!ClusterConfig"
    yaml_loader = yaml.SafeLoader

    def __init__(
        self,
        buckets: list,
        bucket_policies: list,
        service_accounts: list,
        iam_policies: list,
        iam_policy_attachments: list,
    ):
        self.buckets = buckets
        self.bucket_policies = bucket_policies
        self.service_accounts = service_accounts
        self.iam_policies = iam_policies
        self.iam_policy_attachments = iam_policy_attachments


def parse_resources(cluster_config: ClusterConfig) -> tuple:
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = [], [], [], [], []

    for service_account in cluster_config.service_accounts:
        service_accounts.append(ServiceAccount(service_account["name"]))

    for bucket in cluster_config.buckets:
        buckets.append(Bucket(bucket["name"], bucket["versioning"]))

    for bucket_policy in cluster_config.bucket_policies:
        bucket_policies.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))

    for iam_policy in cluster_config.iam_policies:
        iam_policies.append(IamPolicy(iam_policy["name"], iam_policy["policy_file"]))

    for user in cluster_config.iam_policy_attachments:
        iam_policy_attachments.append(IamPolicyAttachment(user["name"], user["policies"]))

    return service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments
