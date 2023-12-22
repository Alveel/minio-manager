from config import MinioConfig

from minio_manager.utilities import read_json, read_yaml


def test_read_yaml():
    test_minio_config = MinioConfig(
        "local-test",
        "127.0.0.1:9000",
        "minioadmin",
        "minioadmin",
        False,
        {"type": "keepass", "config": {"kdbx": "secret.kdbx", "generate_missing": True}},
    )
    assert read_yaml("tests/resources/config.yaml") == test_minio_config


def test_read_json():
    assert read_json("tests/resources/test-iam-policy.json") == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetBucketObjectLockConfiguration",
                    "s3:GetBucketPolicy",
                    "s3:GetBucketLocation",
                    "s3:GetBucketTagging",
                ],
                "Resource": ["arn:aws:s3:::potato-python-test-bucket"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:DeleteObject"],
                "Resource": ["arn:aws:s3:::potato-python-test-bucket/*"],
            },
        ],
    }
