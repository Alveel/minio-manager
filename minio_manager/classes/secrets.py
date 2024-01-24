from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from minio import S3Error
from pykeepass import PyKeePass

from ..utilities import logger, retrieve_environment_variable, setup_s3_client
from .minio_resources import MinioConfig


class MinioCredentials:
    def __init__(self, name: str, access_key: str | None = None, secret_key: str | None = None):
        self.name = name
        self.access_key = access_key
        self.secret_key = secret_key


class SecretManager:
    def __init__(self, config: MinioConfig):
        logger.debug("Initialising SecretManager")
        self._cluster_name = config.name
        self.backend_dirty = False
        self.backend_type = config.secret_backend_type
        self.backend_bucket = config.secret_s3_bucket
        self._backend_filename = None
        self._keepass_temp_file_name = None
        self._keepass_group = None
        self._backend_s3 = self.setup_backend_s3()
        self._backend = self.setup_backend()

    def __del__(self):
        if not self.backend_dirty:
            return
        # If we have dirty back-ends, we want to ensure they are saved before exiting.
        if self.backend_type == "keepass":
            # The PyKeePass save() function can take some time. So we want to run it once when the application is
            # exiting, not every time after creating or updating an entry.
            # After saving, upload the updated file to the S3 bucket and clean up the temp file.
            tmp_file = Path(self._keepass_temp_file_name)
            if isinstance(self._backend, PyKeePass):
                logger.info(f"Saving {self._keepass_temp_file_name}")
                self._backend.save()
                logger.info(f"Uploading modified {self._keepass_temp_file_name} to bucket {self.backend_bucket}")
                self._backend_s3.fput_object(self.backend_bucket, self._backend_filename, tmp_file)
            logger.debug(f"Cleaning up {tmp_file}")
            tmp_file.unlink()

    def setup_backend_s3(self):
        endpoint = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT")
        endpoint_secure_str = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT_SECURE", "true")
        endpoint_secure = endpoint_secure_str.lower() != "false"
        access_key = retrieve_environment_variable("MINIO_MANAGER_SECRET_BACKEND_S3_ACCESS_KEY")
        secret_key = retrieve_environment_variable("MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY")
        logger.debug(f"Setting up secret bucket {self.backend_bucket}")
        s3 = setup_s3_client(endpoint, access_key, secret_key, endpoint_secure)
        try:
            s3.bucket_exists(self.backend_bucket)
        except S3Error as s3e:
            logger.critical(f"{s3e.code}: Does the bucket exist? Does the user have the correct permissions?")
            sys.exit(10)
        return s3

    def setup_backend(self):
        """We dynamically configure the backend depending on the given backend type."""
        logger.debug(f"Configuring SecretManager with backend {self.backend_type}")
        method_name = f"retrieve_{self.backend_type}_backend"
        method = getattr(self, method_name)
        return method()

    def get_credentials(self, name: str) -> MinioCredentials:
        """Get a password from the configured secret backend.

        Args:
            name: str, the name of the password entry

        Returns: MinioCredentials
        """
        method_name = f"{self.backend_type}_get_credentials"
        method = getattr(self, method_name)
        return method(name)

    def set_password(self, credentials: MinioCredentials):
        method_name = f"{self.backend_type}_set_password"
        method = getattr(self, method_name)
        self.backend_dirty = True
        return method(credentials)

    def retrieve_dummy_backend(self, config):
        raise NotImplementedError

    def dummy_get_credentials(self, name):
        raise NotImplementedError

    def dummy_set_password(self, credentials: MinioCredentials):
        raise NotImplementedError

    def retrieve_keepass_backend(self) -> PyKeePass:
        """Back-end implementation for the keepass backend.
        Two-step process:
            - first we retrieve the kdbx file from the S3 bucket
            - then we configure the PyKeePass backend

        Returns: PyKeePass object, with the kdbx file loaded

        """
        self._backend_filename = retrieve_environment_variable("MINIO_MANAGER_KEEPASS_FILE", "secrets.kdbx")
        tmp_file = NamedTemporaryFile(suffix=self._backend_filename, delete=False)
        self._keepass_temp_file_name = tmp_file.name
        try:
            response = self._backend_s3.get_object(self.backend_bucket, self._backend_filename)
            with tmp_file as f:
                logger.debug(f"Writing kdbx file to temp file {tmp_file.name}")
                f.write(response.data)
        except S3Error as s3e:
            logger.debug(s3e)
            logger.critical(
                f"Unable to retrieve {self._backend_filename} from {self.backend_bucket}!\n"
                "Do the required bucket and kdbx file exist, and does the user have the correct "
                "policies assigned?"
            )
            sys.exit(11)
        finally:
            response.close()
            response.release_conn()

        kp_pass = retrieve_environment_variable("MINIO_MANAGER_KEEPASS_PASSWORD")
        logger.debug("Opening keepass database")
        kp = PyKeePass(self._keepass_temp_file_name, password=kp_pass)
        # noinspection PyTypeChecker
        self._keepass_group = kp.find_groups(path=["s3", self._cluster_name])
        if not self._keepass_group:
            logger.critical("Required group not found in Keepass! See documentation for requirements.")
            sys.exit(12)
        logger.debug("Keepass configured as secret backend")
        return kp

    def keepass_get_credentials(self, name) -> MinioCredentials | bool:
        """Get a password from the configured Keepass database.

        Args:
            name: str, the name of the password entry

        Returns:
            MinioCredentials if found, False if not found
        """
        logger.debug(f"Finding Keepass entry for {name}")
        entry = self._backend.find_entries(title=name, group=self._keepass_group, first=True)

        try:
            credentials = MinioCredentials(name, entry.username, entry.password)
            logger.debug(f"Found access key {credentials.access_key}")
        except AttributeError as ae:
            if not ae.obj:
                logger.warning(f"Entry for {name} not found!")
                return MinioCredentials(name=name)
            logger.critical(f"Unhandled exception: {ae}")
            sys.exit(13)
        else:
            return credentials

    def keepass_set_password(self, credentials: MinioCredentials):
        """Set the password for the given credentials.

        Args:
            credentials: MinioCredentials
        """
        logger.info(f"Creating Keepass entry for {credentials.access_key}")
        self._backend.add_entry(
            destination_group=self._keepass_group,
            title=credentials.name,
            username=credentials.access_key,
            password=credentials.secret_key,
        )
        self.backend_dirty = True
