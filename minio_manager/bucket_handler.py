from minio.versioningconfig import VersioningConfig

from minio_manager.classes.minio_resources import Bucket, ServiceAccount
from minio_manager.clients import get_s3_client
from minio_manager.service_account_handler import handle_service_account
from minio_manager.utilities import logger


def handle_bucket(bucket: Bucket):
    client = get_s3_client()
    if not client.bucket_exists(bucket.name):
        logger.info("Creating bucket %s" % bucket.name)
        client.make_bucket(bucket.name)
    else:
        logger.info(f"Bucket {bucket.name} already exists")

    versioning_status = client.get_bucket_versioning(bucket.name).status
    if versioning_status.lower() != bucket.versioning.lower():
        client.set_bucket_versioning(bucket.name, VersioningConfig(bucket.versioning))
        logger.debug(f"Versioning enabled for bucket {bucket.name}")

    if bucket.create_sa:
        # TODO: is there a nicer way to go about this?
        service_account = ServiceAccount(bucket.name, bucket.name)
        handle_service_account(service_account)
