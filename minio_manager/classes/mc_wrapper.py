import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from minio_manager.classes.controller_user import controller_user
from minio_manager.classes.errors import MinioManagerBaseError, raise_specific_error
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.settings import settings


class McWrapper:
    """
    The McWrapper is responsible for executing mc commands.

    To be replaced with the new functions in the updated MinioAdmin library.
    """

    def __init__(self, timeout=60):
        logger.debug("Initialising McWrapper")
        self.timeout = timeout
        self.mc_config_path = TemporaryDirectory(prefix="mm.mc.")
        self.mc = self.find_mc_command()
        self.configure(
            endpoint=settings.s3_endpoint,
            access_key=controller_user.access_key,
            secret_key=controller_user.secret_key,
            secure=settings.s3_endpoint_secure,
        )
        logger.debug("McWrapper initialised")

    def _run(self, args: list, multiline=False) -> list[dict] | dict:
        """Execute mc command and return JSON output."""
        logger.debug(f"Running: {self.mc} --config-dir {self.mc_config_path.name} --json {' '.join(args)}")
        proc = subprocess.run(
            [self.mc, "--config-dir", self.mc_config_path.name, "--json", *args],  # noqa: S603
            capture_output=True,
            timeout=self.timeout,
            text=True,
        )
        if not proc.stdout:
            return [] if multiline else {}
        if multiline:
            return [json.loads(line) for line in proc.stdout.splitlines()]
        return json.loads(proc.stdout)

    @staticmethod
    def find_mc_command() -> Path:
        """Configure the path to the mc command, as it may be named 'mcli' on some systems."""
        mc = shutil.which("mc")
        if not mc:
            mc = shutil.which("mcli")
        return Path(mc)

    def configure(self, endpoint: str, access_key: str, secret_key: str, secure: bool):
        """Ensure the proper alias is configured for the cluster."""
        logger.info("Configuring 'mc'...")
        url = f"https://{endpoint}" if secure else f"http://{endpoint}"
        alias_set_resp = self._run(["alias", "set", settings.cluster_name, url, access_key, secret_key])
        if alias_set_resp.get("error"):
            error_details = alias_set_resp["error"]["cause"]["error"]
            try:
                raise_specific_error(error_details["Code"], error_details["Message"])
            except AttributeError as ae:
                logger.exception("Unknown error!")
                raise MinioManagerBaseError(alias_set_resp["error"]["cause"]["message"]) from ae

        cluster_ready = self._run(["ready", settings.cluster_name])
        healthy = cluster_ready.get("healthy")
        if healthy:
            # Cluster is configured & available
            return

        if cluster_ready.get("error"):
            # A connection error occurred
            raise ConnectionError(cluster_ready["error"])

    def _service_account_run(self, cmd: str, args: list) -> list[dict] | dict:
        """
        mc admin user svcacct helper function, no need to specify the cluster name
        Args:
            cmd: str, the svcacct command
            args: list of arguments to the command

        Returns: list | dict

        """
        multiline = cmd in ["list", "ls"]
        resp = self._run(["admin", "user", "svcacct", cmd, settings.cluster_name, *args], multiline=multiline)
        resp_error = resp[0] if multiline else resp
        if "error" in resp_error:
            resp_error = resp_error["error"]
            error_details = resp_error["cause"]["error"]
            raise_specific_error(error_details["Code"], error_details["Message"])
        return resp

    def service_account_add(self, credentials: ServiceAccount) -> ServiceAccount:
        """
        mc admin user svcacct add alias-name 'username' --name "sa-test-key"

        Args:
            credentials (ServiceAccount): object containing at least the user-friendly name of the service account

        Returns: ServiceAccount with the access and secret keys added to it
        """
        # Create the service account in MinIO
        args = [settings.minio_controller_user, "--name", credentials.name]
        if credentials.description:
            args.extend(["--description", credentials.description])
        if credentials.access_key:
            args.extend(["--access-key", credentials.access_key])
        if credentials.secret_key:
            args.extend(["--secret-key", credentials.secret_key])
        resp = self._service_account_run("add", args)
        credentials.access_key = resp["accessKey"]
        credentials.secret_key = resp["secretKey"]
        return credentials

    def service_account_list(self, access_key: str) -> list[dict]:
        """mc admin user svcacct ls alias-name 'access_key'"""
        return self._service_account_run("ls", [access_key])

    def service_account_info(self, access_key: str) -> dict:
        """mc admin user svcacct info alias-name service-account-access-key"""
        return self._service_account_run("info", [access_key])

    def service_account_delete(self):
        """mc admin user svcacct rm alias-name service-account-access-key"""
        raise NotImplementedError

    def service_account_get_policy(self, access_key: str) -> dict:
        info = self.service_account_info(access_key)
        return info["policy"]

    def service_account_set_policy(self, access_key: str, policy_file: str):
        """mc admin user svcacct edit alias-name service-account-access-key --policy policy-file"""
        return self._service_account_run("edit", [access_key, "--policy", policy_file])

    def cleanup(self):
        """
        We want to clean up the mc config file before the process finishes as otherwise it can cause issues with
        subsequent runs for different environments.
        """
        if not self.mc_config_path.name.startswith("/tmp"):  # noqa: S108
            raise MinioManagerBaseError("CleanUpError", "Error during cleanup: temporary directory is not in /tmp")
        logger.debug(f"Deleting temporary mc config directory {self.mc_config_path.name}")
        self.mc_config_path.cleanup()


mc_wrapper = McWrapper()
