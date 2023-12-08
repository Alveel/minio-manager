import logging
import secrets
import string

from pykeepass import PyKeePass
from utilities import retrieve_environment_variable


class SecretManager:
    def __init__(self, cluster_name: str, backend: dict):
        self._logger = logging.getLogger("root")
        self._logger.debug("Initialising SecretManager")
        self._cluster_name = cluster_name
        self._backend_type = backend["type"]
        self._backend_config = backend["config"]
        self._backend = self.__configure_backend()
        self._keepass_group = None

    def __configure_backend(self):
        self._logger.debug(f"Configuring SecretManager with backend {self._backend_type}")
        method_name = f"retrieve_{self._backend_type}_backend"
        method = getattr(self, method_name)
        return method(self._backend_config)

    def get_password(self, name: dict) -> str:
        """
        Get a password from the configured secret backend.
        Args:
            name: str, the name of the password entry

        Returns: str, the password

        """
        method_name = f"{self._backend_type}_get_password"
        method = getattr(self, method_name)
        password = method(name)
        self._logger.debug(password)
        return password

    def set_password(self, name, password):
        method_name = f"{self._backend_type}_set_password"
        method = getattr(self, method_name)
        return method(name, password)

    @staticmethod
    def generate_password(length=32):
        while True:
            password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= round(length / 3)
            ):
                break
        return password

    def retrieve_keepass_backend(self, config) -> PyKeePass:
        kp_pass = retrieve_environment_variable("KEEPASS_PASSWORD")
        kp = PyKeePass(config["kdbx"], password=kp_pass)
        self._keepass_group = f"Passwords/s3/{self._cluster_name}"
        return kp

    def keepass_get_password(self, name):
        """
        Get a password from the configured Keepass database.
        Args:
            name:

        Returns:

        """
        self._logger.debug(f"Finding Keepass entry for {name}")
        kp: PyKeePass
        kp = self._backend
        entry = kp.find_entries(title=name, username=name, path=self._keepass_group)

        try:
            return entry.password
        except AttributeError as ae:
            self._logger.debug(ae)
            if not ae.obj:
                self._logger.warning(f"Entry for {name} not found!")
                if self._backend_config["generate_missing"]:
                    entry = self.keepass_create_entry(name)
                    return entry.password

    def keepass_create_entry(self, name):
        self._logger.info(f"Creating Keepass entry for {name}")
        kp: PyKeePass
        kp = self._backend
        generated_password = self.generate_password()
        group = kp.find_groups(name=name, path=self._keepass_group)
        entry = kp.add_entry(destination_group=group, title=name, username=name, password=generated_password)
        return entry

    def keepass_set_password(self, name, password):
        raise NotImplementedError
