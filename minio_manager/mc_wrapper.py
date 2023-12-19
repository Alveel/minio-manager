import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from .errors import raise_specific_error
from .minio_secrets import MinioCredentials


class McWrapper:
    def __init__(self, cluster_name, endpoint, access_key, secret_key, secure=True, timeout=60):
        self._logger = logging.getLogger("root")
        self._logger.info("Initialising McWrapper")
        self.cluster_name = cluster_name
        self.cluster_access_key = access_key
        self._timeout = timeout
        self.mc_config_path = self.set_config_path()
        self.mc = self.find_mc_command()
        self.configure(endpoint, access_key, secret_key, secure)

    def _run(self, args, multiline=False):
        """Execute mc command and return JSON output."""
        proc = subprocess.run(
            [self.mc, "--json", *args],  # noqa: S603
            capture_output=True,
            timeout=self._timeout,
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
        self._logger.debug(f"Cluster info: {cluster_info.status}")
        if cluster_info.status == "success":
            # Cluster is configured & available
            return

        if hasattr(cluster_info, "error"):
            # A connection error occurred
            raise ConnectionError(cluster_info.error)

        self._logger.info("Endpoint is not configured or erroneous, configuring...")
        url = f"https://{endpoint}" if secure else f"http://{endpoint}"
        self._run(["alias", "set", self.cluster_name, url, access_key, secret_key])

    def _service_account_run(self, cmd, args):
        """
        mc admin user svcacct helper function, no need to specify the cluster name
        Args:
            cmd: str, the svcacct command
            args: list of arguments to the command

        Returns: a SimpleNamespace object

        """
        multiline = cmd in ["list", "ls"]
        resp = self._run(["admin", "user", "svcacct", cmd, self.cluster_name, *args], multiline=multiline)
        if hasattr(resp, "error") and resp.error:
            error_details = resp.error.cause.error
            raise_specific_error(error_details.Code, error_details.Message)
        return resp

    def service_account_add(self, access_key) -> MinioCredentials:
        """
        mc admin user svcacct add alias-name 'username' --name "sa-test-key"
        Returns: str, the access key
        """
        # Create the service account in MinIO
        resp = self._service_account_run("add", [self.cluster_access_key, "--access-key", access_key])
        return MinioCredentials(resp.accessKey, resp.secretKey)

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
        """
        return self._service_account_run("info", [access_key])

    def service_account_delete(self):
        """
        mc admin user svcacct rm alias-name service-account-name
        Returns:

        """
        raise NotImplementedError
