from minio import Minio
from minio.versioningconfig import ENABLED, VersioningConfig

from .classes.minio_resources import Bucket
from .utilities import logger


def handle_bucket(client: Minio, bucket: Bucket, create_service_account: bool = False):
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
