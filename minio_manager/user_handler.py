import json
import logging

from minio import MinioAdmin
from minio.error import MinioAdminException
from secret_manager import SecretManager

logger = logging.getLogger("root")


def check_if_user_exists(client: MinioAdmin, access_key):
    try:
        user_info = client.user_info(access_key)
        logger.debug(f"User '{access_key}' exists, returning info.")
    except MinioAdminException as mae:
        mae_obj = json.loads(mae._body)
        logger.debug(mae_obj)
        if mae_obj["Code"] == "XMinioAdminNoSuchUser":
            logger.debug(f"User '{access_key}' does not exist")
            return False
    else:
        return user_info


def handle_service_account(client: MinioAdmin, secret_manager: SecretManager, account):
    """
    Manage service accounts.

    Args:
        secret_manager: SecretManager
        account: dict
            name: str
        client: MinioAdmin
    """
    user = check_if_user_exists(client, account["name"])
    if user:
        logger.debug(user)
        # TODO: check if user is correct.
        return

    sa_password = secret_manager.get_password(account["name"])
    resp = client.user_add(account["name"], sa_password)
    logger.info(f"Created service account '{account['name']}'")
    logger.debug(resp)
