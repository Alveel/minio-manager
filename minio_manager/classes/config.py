import yaml

from .minio_resources import Bucket, BucketPolicy, IamPolicy, IamPolicyAttachment, ServiceAccount


class ClusterResources(yaml.YAMLObject):
    """MinIO Cluster configuration object, aka the cluster contents: buckets, policies, etc."""

    yaml_tag = "!ClusterResources"
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


def parse_resources(resources: ClusterResources) -> tuple:
    service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments = [], [], [], [], []

    for service_account in resources.service_accounts:
        bucket = service_account.get("bucket", None)
        service_accounts.append(ServiceAccount(service_account["name"], bucket))

    for bucket in resources.buckets:
        versioning = bucket.get("versioning", True)
        buckets.append(Bucket(bucket["name"], versioning))

    for bucket_policy in resources.bucket_policies:
        bucket_policies.append(BucketPolicy(bucket_policy["bucket"], bucket_policy["policy_file"]))

    for iam_policy in resources.iam_policies:
        iam_policies.append(IamPolicy(iam_policy["name"], iam_policy["policy_file"]))

    for user in resources.iam_policy_attachments:
        iam_policy_attachments.append(IamPolicyAttachment(user["username"], user["policies"]))

    return service_accounts, buckets, bucket_policies, iam_policies, iam_policy_attachments
