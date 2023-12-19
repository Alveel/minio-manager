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


class Bucket:
    def __init__(self, name: str, versioning: bool):
        self.name = name
        self.versioning = versioning


class BucketPolicy:
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    def __init__(self, name: str):
        if len(name) > 20:
            raise ValueError(f"The name of service account {name} must be less than 20 characters.")
        self.name = name


class IamPolicy:
    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    def __init__(self, name: str, policies: list):
        self.name = name
        self.policies = policies
