from __future__ import annotations

import logging

from pykeepass import PyKeePass

from ..utilities import retrieve_environment_variable


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
        self.backend_type = backend["type"]
        self._backend_config = backend["config"]
        self._keepass_group = None
        self._backend = self.__configure_backend()

    def __del__(self):
        if not self.backend_dirty:
            return
        # If we have dirty back-ends, we want to ensure they are saved before exiting.
        if self.backend_type == "keepass":
            # The PyKeePass save() function can take some time. So we want to run it once when the application is
            # exiting, not every time after creating or updating an entry.
            self._logger.info(f"Saving {self._backend_config['kdbx']}")
            self._backend.save()

    def __configure_backend(self):
        self._logger.debug(f"Configuring SecretManager with backend {self.backend_type}")
        method_name = f"retrieve_{self.backend_type}_backend"
        method = getattr(self, method_name)
        return method(self._backend_config)

    def get_credentials(self, name: str) -> MinioCredentials:
        """
        Get a password from the configured secret backend.
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

    def retrieve_keepass_backend(self, config) -> PyKeePass:
        kp_pass = retrieve_environment_variable("KEEPASS_PASSWORD")
        kp = PyKeePass(config["kdbx"], password=kp_pass)
        # noinspection PyTypeChecker
        self._keepass_group = kp.find_groups(path=["s3", self._cluster_name])
        if not self._keepass_group:
            self._logger.exception("Required group not found in Keepass! See documentation for requirements.")
        self._logger.debug(f"Found {self._keepass_group}")
        return kp

    def keepass_get_credentials(self, name) -> MinioCredentials | bool:
        """
        Get a password from the configured Keepass database.
        Args:
            name:

        Returns:

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
            raise
        else:
            return credentials

    def keepass_set_password(self, credentials: MinioCredentials):
        self._logger.info(f"Creating Keepass entry for {credentials.access_key}")
        entry = self._backend.add_entry(
            destination_group=self._keepass_group,
            title=credentials.access_key,
            username=credentials.access_key,
            password=credentials.secret_key,
        )
        self.backend_dirty = True
        return entry
