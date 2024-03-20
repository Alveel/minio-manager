from minio import S3Error

from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import Bucket, ServiceAccount
from minio_manager.clients import s3_client
from minio_manager.service_account_handler import handle_service_account


def configure_versioning(client, bucket):
    if not bucket.versioning:
        return

    versioning_status = client.get_bucket_versioning(bucket.name)
    if versioning_status.status != bucket.versioning.status:
        try:
            client.set_bucket_versioning(bucket.name, bucket.versioning)
        except S3Error as s3e:
            if s3e.code == "InvalidBucketState":
                logger.error(f"Error setting versioning for bucket {bucket.name}: {s3e.message}")
                return
        if bucket.versioning.status == "Suspended":
            logger.warning(f"Versioning on bucket {bucket.name} is suspended!")
        logger.debug(f"Versioning {bucket.versioning.status.lower()} for bucket {bucket.name}")


def configure_lifecycle(client, bucket):
    if not bucket.lifecycle_config:
        return

    lifecycle_status = client.get_bucket_lifecycle(bucket.name)
    if lifecycle_status != bucket.lifecycle_config:
        client.set_bucket_lifecycle(bucket.name, bucket.lifecycle_config)
        logger.debug(f"Lifecycle management configured for bucket {bucket.name}")


def handle_bucket(bucket: Bucket):
    """Handle the specified bucket.

    First validates the existence of the bucket. If it does not exist, it will be created.
    Then it will compare the current bucket versioning configuration and update it if needed.
    Lastly, a related service account will be created that gives access to this specific bucket.

    Args:
        bucket (Bucket): The bucket to handle.
    """
    try:
        if not s3_client.bucket_exists(bucket.name):
            logger.info("Creating bucket %s" % bucket.name)
            s3_client.make_bucket(bucket.name)
        else:
            logger.debug(f"Bucket {bucket.name} already exists")
    except S3Error as s3e:
        if s3e.code == "AccessDenied":
            logger.error(f"Controller user does not have permission to manage bucket {bucket.name}")
            return

    configure_versioning(s3_client, bucket)
    configure_lifecycle(s3_client, bucket)

    if bucket.create_sa:
        # TODO: is there a nicer way to go about this?
        service_account = ServiceAccount(name=bucket.name)
        service_account.generate_service_account_policy()
        handle_service_account(service_account)
