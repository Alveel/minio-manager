from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from minio import Minio, S3Error
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.settings import settings


class SecretManager:
    """SecretManager is responsible for managing credentials"""

    def __init__(self):
        logger.info("Loading secret backend...")
        self.backend_dirty = False
        self.backend_type = settings.secret_backend_type
        self.backend_bucket = settings.secret_backend_s3_bucket
        self.backend_secure = settings.s3_endpoint_secure
        self.backend_filename = None
        self.keepass_temp_file = None
        self.keepass_group = None
        self.backend_s3 = self.setup_backend_s3()
        self.backend = self.setup_backend()
        logger.debug(f"Secret backend initialised with {self.backend_type}")

    def setup_backend_s3(self):
        endpoint = settings.s3_endpoint
        access_key = settings.secret_backend_s3_access_key
        secret_key = settings.secret_backend_s3_secret_key
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
        self.backend_filename = settings.keepass_filename
        tmp_file = NamedTemporaryFile(prefix=f"mm.{self.backend_filename}.", delete=False)
        self.keepass_temp_file = tmp_file
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

        kp_pass = settings.keepass_password
        logger.debug("Opening keepass database")
        try:
            kp = PyKeePass(self.keepass_temp_file.name, password=kp_pass)
        except CredentialsError:
            logger.critical("Invalid credentials for Keepass database.")
            sys.exit(13)
        # noinspection PyTypeChecker
        self.keepass_group = kp.find_groups(path=["s3", settings.cluster_name])
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
            if self.keepass_temp_file:
                self.keepass_temp_file.close()
                Path(self.keepass_temp_file.name).unlink(missing_ok=True)
            return

        # If we have dirty back-ends, we want to ensure they are saved before exiting.
        if self.backend_type == "keepass":
            # The PyKeePass save() function can take some time. So we want to run it once when the application is
            # exiting, not every time after creating or updating an entry.
            # After saving, upload the updated file to the S3 bucket and clean up the temp file.
            if isinstance(self.backend, PyKeePass):
                t_filename = self.keepass_temp_file.name  # temp file name
                s_bucket_name = self.backend_bucket  # bucket name
                s_filename = self.backend_filename  # file name in bucket
                logger.info(f"Saving modified {s_filename} and uploading back to bucket {s_bucket_name}.")
                logger.debug(f"Saving temp file {t_filename}")
                self.backend.save()
                logger.debug(f"Uploading {t_filename} to bucket {s_bucket_name}")
                self.backend_s3.fput_object(s_bucket_name, s_filename, t_filename)
                logger.info(f"Successfully saved modified {s_filename}.")
            logger.debug(f"Cleaning up {self.keepass_temp_file.name}")
            self.keepass_temp_file.close()
            Path(self.keepass_temp_file.name).unlink(missing_ok=True)


secrets = SecretManager()
