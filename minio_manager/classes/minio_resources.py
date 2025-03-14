from __future__ import annotations


class BucketPolicy:
    """
    BucketPolicy represents an S3 bucket policy.

    bucket: The name of the bucket
    policy_file: The path to a JSON policy file
    """

    # TODO: try loading the policy file in order to validate its contents
    def __init__(self, bucket: str, policy_file: str):
        self.bucket = bucket
        self.policy_file = policy_file


class IamPolicy:
    """
    IamPolicy represents an S3 IAM policy.

    name: The name of the policy
    policy_file: The path to a JSON policy file
    """

    def __init__(self, name: str, policy_file: str):
        self.name = name
        self.policy_file = policy_file


class IamPolicyAttachment:
    """
    IamPolicyAttachment represents an S3 IAM policy attachment.

    username: The name of the user to attach the policies to
    policies: A list of policies to attach to the user
    """

    def __init__(self, username: str, policies: list):
        self.username = username
        self.policies = policies
