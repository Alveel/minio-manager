import json
import logging

from minio import Minio, S3Error
from utilities import read_json

logger = logging.getLogger("root")


def handle_bucket_policy(policy, client: Minio):
    """
    Compare and apply policies for buckets

    Args:
        policy: dict
            bucket: str
            policy_file: str
        client: Minio
    """
    policy_object = None
    desired_policy = json.dumps(read_json(policy["policy_file"]), sort_keys=True)

    try:
        current_policy = client.get_bucket_policy(policy["bucket"])
        policy_object = json.dumps(json.loads(current_policy), sort_keys=True)
        logger.debug(f"Desired policy: {desired_policy}")
        logger.debug(f"Current policy: {policy_object}")
    except S3Error as s3e:
        if s3e.code == "NoSuchBucketPolicy":
            logger.info(f"Creating bucket policy for {policy['bucket']}")
            client.set_bucket_policy(policy["bucket"], desired_policy)
            policy_object = client.get_bucket_policy(policy["bucket"])

    if policy_object == desired_policy:
        return

    logger.info(f"Desired policy does not match existing. Updating bucket policy for {policy['bucket']}")
    client.set_bucket_policy(policy["bucket"], desired_policy)
