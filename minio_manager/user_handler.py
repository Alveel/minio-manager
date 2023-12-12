import json
import logging

from errors import MinioInvalidIamCredentialsError
from mc_wrapper import McWrapper
from minio.error import MinioAdminException
from secret_manager import SecretManager

logger = logging.getLogger("root")


def check_if_user_exists(client: McWrapper, access_key):
    try:
        user_info = client.service_account_info(access_key)
        logger.debug(f"User info: {user_info}")
    except MinioAdminException as mae:
        mae_obj = json.loads(mae._body)
        logger.debug(mae_obj)
        if mae_obj["Code"] == "XMinioAdminNoSuchUser":
            logger.warning(f"User '{access_key}' does not exist!")
            return False
    else:
        return user_info


def service_account_exists(client: McWrapper, secret: SecretManager, name):
    try:
        # TODO: find access key, compare to existing in secret backend and live in MinIO
        # TODO: determine for accessKey: automatically generate, or manually configure (20 chars max)
        # sas = client.service_account_list(client.cluster_access_key)
        # logger.debug(sas)
        access_key = secret.get_credentials(name).access_key
        return client.service_account_info(access_key)
    except AttributeError:
        # account does not exist in MinIO
        return False
    except MinioInvalidIamCredentialsError as e:
        logger.warning(e)
        return False


def handle_service_account(client: McWrapper, secrets: SecretManager, account):
    """
    Manage service accounts.

    Args:
        secrets: SecretManager
        client: McWrapper
        account: dict
            name: str
    """
    user = service_account_exists(client, secrets, account["name"])
    access_key = account["name"]
    if user:
        logger.debug(user)
        # TODO: check if user is correct.
        return

    resp = client.service_account_add(account["name"])
    logger.info(f"Created service account '{account['name']}', access key: {access_key}")
    logger.debug(resp)
