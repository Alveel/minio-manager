from minio.versioningconfig import ENABLED, VersioningConfig

from minio_manager.classes.minio_resources import Bucket, ServiceAccount
from minio_manager.clients import get_s3_client
from minio_manager.service_account_handler import handle_service_account
from minio_manager.utilities import logger


def handle_bucket(bucket: Bucket, create_service_account: bool = False):
    client = get_s3_client()
    if not client.bucket_exists(bucket.name):
        logger.info("Creating bucket %s" % bucket.name)
        client.make_bucket(bucket.name)
    else:
        logger.info(f"Bucket {bucket.name} already exists")

    # TODO: disable versioning if explicitly disabled
    if not bucket.versioning:
        return

    versioning_status = client.get_bucket_versioning(bucket.name).status
    if versioning_status == ENABLED:
        return
    client.set_bucket_versioning(bucket.name, VersioningConfig(ENABLED))
    logger.debug(f"Versioning enabled for bucket {bucket.name}")

    if create_service_account:
        service_account = ServiceAccount(bucket.name)
        handle_service_account(service_account)
