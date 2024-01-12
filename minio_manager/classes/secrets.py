from __future__ import annotations

import logging

from minio import S3Error
from pykeepass import PyKeePass

from ..utilities import retrieve_environment_variable, setup_s3_client


class MinioCredentials:
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key


class SecretManager:
    def __init__(self, cluster_name: str, backend: dict):
        self._logger = logging.getLogger("root")
        self._logger.debug("Initialising SecretManager")
        self._cluster_name = cluster_name
        self.backend_dirty = False
        self.backend_type = retrieve_environment_variable("MINIO_MANAGER_SECRET_BACKEND_TYPE")
        self.backend_bucket = retrieve_environment_variable("MINIO_MANAGER_SECRET_S3_BUCKET", "minio-manager-secrets")
        self._backend_config = backend["config"]
        self._keepass_filename = None
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
            self._logger.info(f"Saving {self._keepass_filename}")
            self._backend.save()

    def setup_backend_s3(self):
        endpoint = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT")
        endpoint_secure_str = retrieve_environment_variable("MINIO_MANAGER_S3_ENDPOINT_SECURE", True)
        endpoint_secure = endpoint_secure_str.lower() != "false"
        access_key = retrieve_environment_variable("MINIO_MANAGER_SECRET_S3_ACCESS_KEY")
        secret_key = retrieve_environment_variable("MINIO_MANAGER_SECRET_S3_SECRET_KEY")
        self._logger.debug(f"Setting up secret bucket {self.backend_bucket}")
        s3 = setup_s3_client(endpoint, access_key, secret_key, endpoint_secure)
        try:
            s3.bucket_exists(self.backend_bucket)
        except S3Error as s3e:
            self._logger.critical(f"{s3e.code}: Does the bucket exist? Does the user have the correct permissions?")
        return s3

    def setup_backend(self):
        """We dynamically configure the backend depending on the given backend type."""
        self._logger.debug(f"Configuring SecretManager with backend {self.backend_type}")
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
        return method(credentials)

    def retrieve_dummy_backend(self, config):
        raise NotImplementedError

    def dummy_get_credentials(self, name):
        raise NotImplementedError

    def dummy_set_password(self, credentials: MinioCredentials):
        raise NotImplementedError

    def retrieve_keepass_backend(self) -> PyKeePass:
        self._keepass_filename = retrieve_environment_variable("MINIO_MANAGER_KEEPASS_FILE", "secrets.kdbx")
        try:
            self._backend_s3.fget_object(
                self.backend_bucket, self._keepass_filename, f"/tmp/{self._keepass_filename}"  # noqa: S108
            )
        except S3Error as s3e:
            self._logger.debug(s3e)
            self._logger.critical(
                f"Unable to retrieve {self._keepass_filename} from {self.backend_bucket}!\n"
                "Do the required bucket and kdbx file exist, and does the user have the correct "
                "permissions?"
            )
            exit(4)

        kp_pass = retrieve_environment_variable("MINIO_MANAGER_KEEPASS_PASSWORD")
        kp = PyKeePass(f"/tmp/{self._keepass_filename}", password=kp_pass)  # noqa: S108
        # noinspection PyTypeChecker
        self._keepass_group = kp.find_groups(path=["s3", self._cluster_name])
        if not self._keepass_group:
            self._logger.exception("Required group not found in Keepass! See documentation for requirements.")
        return kp

    def keepass_get_credentials(self, name) -> MinioCredentials | bool:
        """Get a password from the configured Keepass database.

        Args:
            name: str, the name of the password entry

        Returns:
            MinioCredentials if found, False if not found
        """
        self._logger.debug(f"Finding Keepass entry for {name}")
        kp: PyKeePass
        kp = self._backend
        entry = kp.find_entries(title=name, username=name, group=self._keepass_group, first=True)

        try:
            credentials = MinioCredentials(entry.username, entry.password)
            self._logger.debug(f"Found access key {credentials.access_key}")
        except AttributeError as ae:
            if not ae.obj:
                self._logger.warning(f"Entry for {name} not found!")
                return False
            exit(5)
        else:
            return credentials

    def keepass_set_password(self, credentials: MinioCredentials):
        """Set the password for the given credentials.

        Args:
            credentials: MinioCredentials
        """
        self._logger.info(f"Creating Keepass entry for {credentials.access_key}")
        self._backend.add_entry(
            destination_group=self._keepass_group,
            title=credentials.access_key,
            username=credentials.access_key,
            password=credentials.secret_key,
        )
        self.backend_dirty = True
