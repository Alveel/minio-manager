import yaml


class MinioConfig(yaml.YAMLObject):
    """MinIO server configuration object, the connection details."""

    yaml_tag = "!MinioConfig"
    yaml_loader = yaml.SafeLoader

    def __init__(
        self,
        name: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: True,
        config: str,
        secret_backend: dict,
    ):
        self.name = name
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.config = config
        self.secret_backend = secret_backend

    def __repr__(self):
        return (
            f"MinioConfig(name={self.name}, endpoint={self.endpoint}, access_key={self.access_key}, "
            f"secret_key={self.secret_key}, secure={self.secure}, config={self.config}, "
            f"secret_backend={self.secret_backend})"
        )


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
        user_policy_attachments: list,
    ):
        self.buckets = buckets
        self.bucket_policies = bucket_policies
        self.service_accounts = service_accounts
        self.iam_policies = iam_policies
        self.user_policy_attachments = user_policy_attachments
