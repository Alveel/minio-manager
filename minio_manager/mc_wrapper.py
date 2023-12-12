import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from errors import MinioManagerError
from secret_manager import SecretManager


class McWrapper:
    def __init__(
        self, cluster_name, endpoint, access_key, secret_key, secret_manager: SecretManager, secure=True, timeout=60
    ):
        self._logger = logging.getLogger("root")
        self._logger.info("Initialising McWrapper")
        self.cluster_name = cluster_name
        self.cluster_access_key = access_key
        self._timeout = timeout
        self.mc_config_path = self.set_config_path()
        self.mc = self.find_mc_command()
        self._secret_manager = secret_manager
        self.configure(endpoint, access_key, secret_key, secure)

    def _run(self, args, multiline=False):
        """Execute mc command and return JSON output."""
        proc = subprocess.run(
            [self.mc, "--json", *args],  # noqa: S603
            capture_output=True,
            timeout=self._timeout,
            # check=True,
            text=True,
        )
        if not proc.stdout:
            return [] if multiline else {}
        if multiline:
            return [json.loads(line, object_hook=lambda d: SimpleNamespace(**d)) for line in proc.stdout.splitlines()]
        return json.loads(proc.stdout, object_hook=lambda d: SimpleNamespace(**d))

    @staticmethod
    def set_config_path():
        """Set the path to the mc config.json file"""
        env_mc_config_path = os.getenv("MC_CONFIG_PATH")
        env_home = os.getenv("HOME")
        mc_paths = [
            f"{env_mc_config_path}/config.json",
            f"{env_home}/.mc/config.json",
            f"{env_home}/.mcli/config.json",
        ]
        for path in mc_paths:
            if os.path.exists(path):
                return path

    @staticmethod
    def find_mc_command() -> Path:
        """Configure the path to the mc command, as it may be named 'mcli' on some systems."""
        mc = shutil.which("mc")
        if not mc:
            mc = shutil.which("mcli")
        return Path(mc)

    def configure(self, endpoint, access_key, secret_key, secure: bool):
        """Ensure the proper alias is configured for the cluster."""
        self._logger.debug(f"Validating config for cluster {self.cluster_name}")
        cluster_info = self._run(["admin", "info", self.cluster_name])
        if cluster_info.status != "success":
            raise MinioManagerError(cluster_info.error)

        self._logger.info("Endpoint is not configured or erroneous, configuring...")
        url = f"https://{endpoint}" if secure else f"http://{endpoint}"
        self._run(["alias", "set", self.cluster_name, url, access_key, secret_key])

    def _service_account_run(self, cmd, args):
        """
        mc admin user svcacct helper function, no need to specify the cluster name
        Args:
            cmd: str, the svcacct command
            args: list, list of arguments to the command

        Returns: a SimpleNamespace object

        """
        multiline = cmd in ["list", "ls"]
        resp = self._run(["admin", "user", "svcacct", cmd, self.cluster_name, *args], multiline=multiline)
        if hasattr(resp, "error") and resp.error:
            raise MinioManagerError(resp.error)
        return resp

    def service_account_add(self, name) -> str:
        """
        mc admin user svcacct add alias-name 'username' --name "sa-test-key"
        Returns: str, the access key
        TODO: move secret logic to user_handler
        """
        # Check if the service account already exists in the secret backend
        entry = self._secret_manager.get_credentials(name)
        if entry:
            backend_type = self._secret_manager.backend_type
            self._logger.exception(f"Secret for {name} already exists in {backend_type}, not creating service account!")
        # Create the service account in MinIO
        resp = self._service_account_run("add", [self.cluster_access_key, "--name", name])
        # Create an entry in the secret backend
        credentials = self._secret_manager.MinioCredentials(name, resp.accessKey, resp.secretKey)
        self._secret_manager.set_password(credentials)
        self._secret_manager.backend_dirty = True
        self._logger.info(f"Created service account {name} with access key {resp.accessKey}")
        return credentials.access_key

    def service_account_list(self, username):
        """
        mc admin user svcacct ls alias-name 'username'
        Returns:

        """
        return self._service_account_run("ls", [username])

    def service_account_info(self, access_key):
        """
        mc admin user svcacct info alias-name service-account-name
        Returns:
        TODO: move secret logic to user_handler
        """
        resp = self._service_account_run("info", [access_key])

        return resp

    def service_account_delete(self):
        """
        mc admin user svcacct rm alias-name service-account-name
        Returns:

        """
        raise NotImplementedError
