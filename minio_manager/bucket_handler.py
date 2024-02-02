from minio_manager.classes.minio_resources import Bucket, ServiceAccount
from minio_manager.clients import get_s3_client
from minio_manager.service_account_handler import handle_service_account
from minio_manager.utilities import logger


def configure_versioning(client, bucket):
    if not bucket.versioning:
        return

    versioning_status = client.get_bucket_versioning(bucket.name)
    if versioning_status.status != bucket.versioning.status:
        client.set_bucket_versioning(bucket.name, bucket.versioning)
        logger.debug(f"Versioning {bucket.versioning.status.lower()} for bucket {bucket.name}")


def configure_lifecycle(client, bucket):
    if not bucket.lifecycle_config:
        return

    lifecycle_status = client.get_bucket_lifecycle(bucket.name)
    if lifecycle_status != bucket.lifecycle_config:
        client.set_bucket_lifecycle(bucket.name, bucket.lifecycle_config)
        logger.debug(f"Lifecycle {bucket.lifecycle_config} for bucket {bucket.name}")


def handle_bucket(bucket: Bucket):
    """Handle the specified bucket.

    First validates the existence of the bucket. If it does not exist, it will be created.
    Then it will compare the current bucket versioning configuration and update it if needed.
    Lastly, a related service account will be created that gives access to this specific bucket.

    Args:
        bucket (Bucket): The bucket to handle.
    """
    client = get_s3_client()
    if not client.bucket_exists(bucket.name):
        logger.info("Creating bucket %s" % bucket.name)
        client.make_bucket(bucket.name)
    else:
        logger.info(f"Bucket {bucket.name} already exists")

    configure_versioning(client, bucket)
    configure_lifecycle(client, bucket)

    if bucket.create_sa:
        # TODO: is there a nicer way to go about this?
        service_account = ServiceAccount(bucket.name, bucket.name)
        handle_service_account(service_account)
