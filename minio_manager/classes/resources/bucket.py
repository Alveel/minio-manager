from __future__ import annotations

from enum import Enum

from minio import S3Error
from minio.lifecycleconfig import LifecycleConfig
from minio.versioningconfig import VersioningConfig
from pydantic import BaseModel, Field

from minio_manager import logger, settings
from minio_manager.clients import s3_client
from minio_manager.utilities import compare_objects, increment_error_count


def validate_bucket_name(name: str):
    if len(name) > 63 or len(name) < 3:
        logger.error(f"Bucket '{name}' is {len(name)} characters long;")
        logger.error("Bucket names must be between 3 and 63 characters in length!")
        increment_error_count()

    allowed_prefixes = settings.allowed_bucket_prefixes
    if allowed_prefixes:
        noun = "prefix" if len(allowed_prefixes) == 1 else "prefixes"
        prefixes_str = ", ".join(allowed_prefixes)
        logger.info(f"Only allowing buckets with the following {noun}: {prefixes_str}")

    if allowed_prefixes and not name.startswith(allowed_prefixes):
        logger.error(f"Bucket '{name}' does not start with one of the required prefixes {allowed_prefixes}!")
        increment_error_count()
        return False


class Bucket(BaseModel):
    """
    Bucket represents an S3 bucket.

    name: The name of the bucket
    create_service_account: Whether to create a service account for the bucket (True or False)
    versioning: The versioning configuration for the bucket (Enabled or Suspended)
    lifecycle_config: The path to a lifecycle configuration JSON file for the bucket
    """

    class Config:
        arbitrary_types_allowed = True

    class BucketState(Enum):
        UNKNOWN = 0
        EXISTS = 1
        DOES_NOT_EXIST = 2

    class VersioningState(Enum):
        UNKNOWN = 0
        ENABLED = "Enabled"
        DISABLED = "Disabled"
        OFF = "Off"
        SUSPENDED = "Suspended"

    name: str = Field(..., min_length=3, max_length=63)
    create_sa: bool = Field(default=settings.auto_create_service_account)
    versioning: VersioningConfig | None = Field(default=None)
    lifecycle_config: LifecycleConfig | None = Field(default=None)
    state: BucketState = Field(default=BucketState.UNKNOWN)
    desired_state: BucketState = Field(default=BucketState.EXISTS)

    def create(self):
        if self.desired_state is not self.BucketState.EXISTS:
            return

        try:
            if not s3_client.bucket_exists(self.name):
                self.state = self.BucketState.DOES_NOT_EXIST
                logger.info(f"Creating bucket {self.name}")
                s3_client.make_bucket(self.name)
            else:
                logger.debug(f"Bucket {self.name} already exists")
                self.state = self.BucketState.EXISTS
        except S3Error as s3e:
            if s3e.code == "AccessDenied":
                logger.error(f"Controller user does not have permission to manage bucket {self.name}")
                logger.debug(s3e.message)
                increment_error_count()
                return
            else:
                logger.error(f"Unknown error creating bucket {self.name}: {s3e.message}")
                increment_error_count()
                return
        self.state = self.BucketState.EXISTS

    def configure_versioning(self):
        versioning = s3_client.get_bucket_versioning(self.name)
        if self.versioning.status == versioning.status:
            return
        try:
            logger.debug(f"Bucket {self.name}: setting versioning to {self.versioning.status.lower()}")
            s3_client.set_bucket_versioning(self.name, self.versioning)
        except S3Error as s3e:
            logger.error(f"Bucket {self.name}: error setting versioning: {s3e.message}")
            increment_error_count()
            return
        if self.versioning.status == "Suspended":
            logger.warning(f"Bucket {self.name}: versioning is suspended!")
        logger.debug(f"Bucket {self.name}: versioning {self.versioning.status.lower()}")

    def configure_lifecycle(self):
        # First compare the current lifecycle configuration with the desired configuration
        logger.debug(
            f"Bucket {self.name}: comparing existing lifecycle management policy with desired state for bucket"
        )
        lifecycle_status: LifecycleConfig = s3_client.get_bucket_lifecycle(self.name)
        lifecycle_diff = compare_objects(lifecycle_status, self.lifecycle_config)
        if not lifecycle_diff:
            # If there is no difference, there is no need to update the lifecycle configuration
            logger.debug(f"Bucket {self.name}: lifecycle management policies already up to date")
            return

        logger.debug(f"Bucket {self.name}: current lifecycle management policy does not match desired state")
        # First clean up the existing lifecycle configuration
        s3_client.delete_bucket_lifecycle(self.name)
        logger.debug(f"Bucket {self.name}: removed existing lifecycle management policy")
        s3_client.set_bucket_lifecycle(self.name, self.lifecycle_config)
        logger.info(f"Bucket {self.name}: lifecycle management policies updated")

    def configure_service_account(self):
        # TODO
        pass

    def ensure(self):
        self.create()
        self.configure_versioning()
        self.configure_lifecycle()
        self.configure_service_account()
