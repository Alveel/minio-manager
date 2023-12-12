import logging

from minio import Minio
from minio.versioningconfig import ENABLED, VersioningConfig

logger = logging.getLogger("root")


def handle_bucket(client: Minio, bucket):
    if not client.bucket_exists(bucket["name"]):
        logger.info("Creating bucket %s" % bucket["name"])
        client.make_bucket(bucket["name"])
    else:
        logger.info(f"Bucket {bucket['name']} already exists")

    if not bucket["versioning"]:
        return

    versioning_status = client.get_bucket_versioning(bucket["name"]).status
    if versioning_status == ENABLED:
        return
    client.set_bucket_versioning(bucket["name"], VersioningConfig(ENABLED))
    logger.debug(f"Versioning enabled for bucket {bucket['name']}")
