import logging

from minio import Minio
from minio.versioningconfig import ENABLED, VersioningConfig

logger = logging.getLogger("root")


def handle_bucket(bucket, client: Minio):
    if not client.bucket_exists(bucket["name"]):
        logger.info("Creating bucket %s" % bucket["name"])
        client.make_bucket(bucket["name"])
    else:
        logger.info(f"Bucket {bucket['name']} already exists")

    if bucket["versioning"]:
        client.set_bucket_versioning(bucket["name"], VersioningConfig(ENABLED))
        versioning_status = client.get_bucket_versioning(bucket["name"]).status
        logger.info(versioning_status)
