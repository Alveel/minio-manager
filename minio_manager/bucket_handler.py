from minio import S3Error

from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import Bucket, ServiceAccount
from minio_manager.clients import s3_client
from minio_manager.service_account_handler import handle_service_account
from minio_manager.utilities import compare_objects, increment_error_count


def configure_versioning(bucket):
    if not bucket.versioning:
        return

    versioning_status = s3_client.get_bucket_versioning(bucket.name)
    if versioning_status.status != bucket.versioning.status:
        try:
            s3_client.set_bucket_versioning(bucket.name, bucket.versioning)
        except S3Error as s3e:
            if s3e.code == "InvalidBucketState":
                logger.error(f"Bucket {bucket.name}: error setting versioning: {s3e.message}")
                increment_error_count()
                return
        if bucket.versioning.status == "Suspended":
            logger.warning(f"Bucket {bucket.name}: versioning is suspended!")
        logger.debug(f"Bucket {bucket.name}: versioning {bucket.versioning.status.lower()}")


def configure_lifecycle(bucket):
    if not bucket.lifecycle_config:
        return

    # First compare the current lifecycle configuration with the desired configuration
    logger.debug(f"Bucket {bucket.name}: comparing existing lifecycle management policy with desired state for bucket")
    try:
        lifecycle_status = s3_client.get_bucket_lifecycle(bucket.name)
        lifecycle_diff = compare_objects(lifecycle_status, bucket.lifecycle_config)
        if not lifecycle_diff:
            # If there is no difference, there is no need to update the lifecycle configuration
            logger.debug(f"Bucket {bucket.name}: lifecycle management policies already up to date")
            return

        logger.debug(f"Bucket {bucket.name}: current lifecycle management policy does not match desired state")
    except ValueError as ve:
        if ve.args == "Rule filter must be provided":
            logger.debug("Endpoint does not appear to support a GET request on the lifecycle API.")
        else:
            logger.error(f"Error getting lifecycle configuration: {ve.args}, ")
            return

    # First clean up the existing lifecycle configuration
    s3_client.delete_bucket_lifecycle(bucket.name)
    logger.debug(f"Bucket {bucket.name}: removed existing lifecycle management policy")
    s3_client.set_bucket_lifecycle(bucket.name, bucket.lifecycle_config)
    logger.info(f"Bucket {bucket.name}: lifecycle management policies updated")


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
            logger.info(f"Creating bucket {bucket.name}")
            s3_client.make_bucket(bucket.name)
        else:
            logger.debug(f"Bucket {bucket.name} already exists")
    except S3Error as s3e:
        if s3e.code == "AccessDenied":
            logger.error(f"Controller user does not have permission to manage bucket {bucket.name}")
            logger.debug(s3e.message)
            increment_error_count()
            return
        else:
            logger.error(f"Unknown error creating bucket {bucket.name}: {s3e.message}")
            increment_error_count()
            return

    configure_versioning(bucket)
    configure_lifecycle(bucket)

    if bucket.create_service_account:
        # TODO: is there a nicer way to go about this?
        service_account = ServiceAccount(name=bucket.name)
        service_account.generate_service_account_policy()
        handle_service_account(service_account)
