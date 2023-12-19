import yaml


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
