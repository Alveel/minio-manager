import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from ..utilities import logger
from .errors import MinioManagerBaseError, raise_specific_error
from .minio_resources import MinioConfig
from .secrets import MinioCredentials


class McWrapper:
    def __init__(self, config: MinioConfig, timeout=60):
        logger.info("Initialising McWrapper")
        self.cluster_name = config.name
        self.cluster_controller_user = config.controller_user
        self.timeout = timeout
        self.mc_config_path = self.set_config_path()
        self.mc = self.find_mc_command()
        self.configure(config.endpoint, config.access_key, config.secret_key, config.secure)

    def _run(self, args, multiline=False):
        """Execute mc command and return JSON output."""
        logger.debug(f"Running: {self.mc} --json {' '.join(args)}")
        proc = subprocess.run(
            [self.mc, "--json", *args],  # noqa: S603
            capture_output=True,
            timeout=self.timeout,
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
        logger.debug(f"Validating config for cluster {self.cluster_name}")
        cluster_ready = self._run(["ready", self.cluster_name])
        logger.debug(f"Cluster status: {cluster_ready}")
        if not cluster_ready.error:
            # Cluster is configured & available
            return

        logger.info("Endpoint is not configured or erroneous, configuring...")
        url = f"https://{endpoint}" if secure else f"http://{endpoint}"
        alias_set_resp = self._run(["alias", "set", self.cluster_name, url, access_key, secret_key])
        if hasattr(alias_set_resp, "error"):
            error_details = alias_set_resp.error.cause.error
            try:
                raise_specific_error(error_details.Code, error_details.Message)
            except AttributeError as ae:
                logger.exception("Unknown error!")
                raise MinioManagerBaseError(alias_set_resp.error.cause.message) from ae

        cluster_ready = self._run(["ready", self.cluster_name])
        if cluster_ready.healthy:
            # Cluster is configured & available
            return

        if hasattr(cluster_ready, "error"):
            # A connection error occurred
            raise ConnectionError(cluster_ready.error)

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

    def service_account_add(self, credentials: MinioCredentials) -> MinioCredentials:
        """
        mc admin user svcacct add alias-name 'username' --name "sa-test-key"

        Args:
            credentials (MinioCredentials): object containing at least the user-friendly name of the service account

        Returns: MinioCredentials with the access and secret keys added to it
        """
        # Create the service account in MinIO
        args = [self.cluster_controller_user, "--name", credentials.name]
        if credentials.secret_key:
            args.extend(["--secret-key", credentials.secret_key])
        if credentials.access_key:
            args.extend(["--access-key", credentials.access_key])
        resp = self._service_account_run("add", args)
        credentials.access_key = resp.accessKey
        credentials.secret_key = resp.secretKey
        return credentials

    def service_account_list(self, access_key):
        """mc admin user svcacct ls alias-name 'access_key'"""
        return self._service_account_run("ls", [access_key])

    def service_account_info(self, access_key):
        """mc admin user svcacct info alias-name service-account-access-key"""
        return self._service_account_run("info", [access_key])

    def service_account_delete(self):
        """mc admin user svcacct rm alias-name service-account-access-key"""
        raise NotImplementedError

    def service_account_set_policy(self, access_key, policy_file):
        """mc admin user svcacct edit alias-name service-account-access-key --policy policy-file"""
        return self._service_account_run("edit", [access_key, "--policy", policy_file])
