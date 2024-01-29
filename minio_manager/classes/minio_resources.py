from __future__ import annotations


class Bucket:
    def __init__(self, name: str, create_sa: bool, versioning: bool):
        self.name = name
        self.create_sa = create_sa
        self.versioning = versioning


class BucketPolicy:
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class ServiceAccount:
    def __init__(self, name: str, bucket: str | None = None):
        self.name = name
        self.bucket = bucket


class IamPolicy:
    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
