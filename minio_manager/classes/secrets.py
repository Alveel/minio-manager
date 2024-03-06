from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from minio import Minio, S3Error
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

from minio_manager.classes.config import MinioConfig
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.utilities import get_env_var, logger


class SecretManager:
    """SecretManager is responsible for managing credentials"""

    def __init__(self, config: MinioConfig):
        logger.debug("Initialising SecretManager")
        self._cluster_name = config.name
        self.backend_dirty = False
        self.backend_type = config.secret_backend_type
        self.backend_bucket = config.secret_s3_bucket
        self.backend_secure = config.secure
        self.backend_filename = None
        self.keepass_temp_file_name = None
        self.keepass_group = None
        self.backend_s3 = self.setup_backend_s3()
        self.backend = self.setup_backend()
        logger.info(f"Secret backend initialised with {self.backend_type}")

    def setup_backend_s3(self):
        endpoint = get_env_var("MINIO_MANAGER_S3_ENDPOINT")
        access_key = get_env_var("MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY")
        secret_key = get_env_var("MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY")
        logger.debug(f"Setting up secret bucket {self.backend_bucket}")
        s3 = Minio(endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=self.backend_secure)
        try:
            s3.bucket_exists(self.backend_bucket)
        except S3Error as s3e:
            if s3e.code == "SignatureDoesNotMatch":
                logger.critical("Invalid secret key provided for the secret backend bucket user.")
            if s3e.code == "InvalidAccessKeyId":
                logger.critical("Invalid access key ID provided for the secret backend bucket user.")
            if s3e.code == "AccessDenied":
                logger.critical(
                    "Access denied for the secret backend bucket user. Does the bucket exist, and does the "
                    "user have the correct permissions to the bucket?"
                )
            sys.exit(10)
        return s3

    def setup_backend(self):
        """We dynamically configure the backend depending on the given backend type."""
        logger.debug(f"Configuring SecretManager with backend {self.backend_type}")
        method_name = f"retrieve_{self.backend_type}_backend"
        method = getattr(self, method_name)
        return method()

    def get_credentials(self, name: str, required: bool = False) -> ServiceAccount:
        """Get a password from the configured secret backend.

        Args:
            name (str): the name of the password entry
            required (bool): whether the credentials must exist

        Returns: MinioCredentials
        """
        method_name = f"{self.backend_type}_get_credentials"
        method = getattr(self, method_name)
        return method(name, required)

    def set_password(self, credentials: ServiceAccount):
        method_name = f"{self.backend_type}_set_password"
        method = getattr(self, method_name)
        self.backend_dirty = True
        return method(credentials)

    def retrieve_dummy_backend(self, config):
        raise NotImplementedError

    def dummy_get_credentials(self, name):
        raise NotImplementedError

    def dummy_set_password(self, credentials: ServiceAccount):
        raise NotImplementedError

    def retrieve_keepass_backend(self) -> PyKeePass:
        """Back-end implementation for the keepass backend.
        Two-step process:
            - first we retrieve the kdbx file from the S3 bucket
            - then we configure the PyKeePass backend

        Returns: PyKeePass object, with the kdbx file loaded

        """
        self.backend_filename = get_env_var("MINIO_MANAGER_KEEPASS_FILE", "secrets.kdbx")
        tmp_file = NamedTemporaryFile(suffix=self.backend_filename, delete=False)
        self.keepass_temp_file_name = tmp_file.name
        try:
            response = self.backend_s3.get_object(self.backend_bucket, self.backend_filename)
            with tmp_file as f:
                logger.debug(f"Writing kdbx file to temp file {tmp_file.name}")
                f.write(response.data)
        except S3Error as s3e:
            logger.debug(s3e)
            logger.critical(
                f"Unable to retrieve {self.backend_filename} from {self.backend_bucket}!\n"
                "Do the required bucket and kdbx file exist, and does the user have the correct "
                "policies assigned?"
            )
            sys.exit(11)
        finally:
            response.close()
            response.release_conn()

        kp_pass = get_env_var("MINIO_MANAGER_KEEPASS_PASSWORD")
        logger.debug("Opening keepass database")
        try:
            kp = PyKeePass(self.keepass_temp_file_name, password=kp_pass)
        except CredentialsError:
            logger.critical("Invalid credentials for Keepass database.")
            sys.exit(13)
        # noinspection PyTypeChecker
        self.keepass_group = kp.find_groups(path=["s3", self._cluster_name])
        if not self.keepass_group:
            logger.critical("Required group not found in Keepass! See documentation for requirements.")
            sys.exit(12)
        logger.debug("Keepass configured as secret backend")
        return kp

    def keepass_get_credentials(self, name: str, required: bool) -> ServiceAccount:
        """Get a password from the configured Keepass database.

        Args:
            name (str): the name of the password entry
            required (bool): if the entry must exist

        Returns:
            ServiceAccount
        """
        logger.debug(f"Finding Keepass entry for {name}")
        entry = self.backend.find_entries(title=name, group=self.keepass_group, first=True)

        try:
            credentials = ServiceAccount(name=name, access_key=entry.username, secret_key=entry.password)
            logger.debug(f"Found access key {credentials.access_key}")
        except AttributeError as ae:
            if not ae.obj:
                if required:
                    logger.critical(f"Required entry for {name} not found!")
                    sys.exit(14)
                return ServiceAccount(name=name)
            logger.critical(f"Unhandled exception: {ae}")
        else:
            return credentials

    def keepass_set_password(self, credentials: ServiceAccount):
        """Set the password for the given credentials.

        Args:
            credentials (ServiceAccount): the credentials to set
        """
        logger.debug(f"Creating Keepass entry '{credentials.name}' with access key '{credentials.access_key}'")
        self.backend.add_entry(
            destination_group=self.keepass_group,
            title=credentials.name,
            username=credentials.access_key,
            password=credentials.secret_key,
        )

    def cleanup(self):
        if not self.backend_dirty:
            if self.keepass_temp_file_name:
                Path(self.keepass_temp_file_name).unlink()
            return

        # If we have dirty back-ends, we want to ensure they are saved before exiting.
        if self.backend_type == "keepass":
            # The PyKeePass save() function can take some time. So we want to run it once when the application is
            # exiting, not every time after creating or updating an entry.
            # After saving, upload the updated file to the S3 bucket and clean up the temp file.
            tmp_file = Path(self.keepass_temp_file_name)
            if isinstance(self.backend, PyKeePass):
                logger.info(f"Saving {self.keepass_temp_file_name}")
                self.backend.save()
                logger.info(f"Uploading modified {self.keepass_temp_file_name} to bucket {self.backend_bucket}")
                self.backend_s3.fput_object(self.backend_bucket, self.backend_filename, tmp_file)
            logger.debug(f"Cleaning up {tmp_file}")
            tmp_file.unlink()
