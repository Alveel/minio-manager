import logging

from .classes.errors import MinioInvalidIamCredentialsError
from .classes.mc_wrapper import McWrapper
from .classes.minio import ServiceAccount
from .classes.secrets import SecretManager

logger = logging.getLogger("root")


def service_account_exists(client: McWrapper, access_key):
    try:
        return client.service_account_info(access_key)
    except AttributeError:
        # account does not exist in MinIO
        return False
    except MinioInvalidIamCredentialsError as e:
        logger.warning(e)
        return False


def handle_service_account(client: McWrapper, secrets: SecretManager, account: ServiceAccount):
    """
    Manage service accounts.

    Steps taken:
    1) check if service account exists in minio
    2) check if service account exists in secret backend
    3) if it exists in one but not the other, throw an error and return
    4) if it exists in both, return
    5) if it does not, create service account in minio and secret backend

    Args:
        secrets (SecretManager)
        client (McWrapper)
        account (ServiceAccount)
    """
    # Determine if access key exists in MinIO
    user = service_account_exists(client, account.name)
    # Determine if access key entry exists in secret backend
    entry = secrets.get_credentials(account.name)

    if entry and not user:
        logger.error(
            f"Service account {account.name} exists in secret backend but not in MinIO! Manual intervention required."
        )
        return

    if user and not entry:
        logger.error(
            f"Service account {account.name} exists in MinIO but not in secret backend! Manual intervention required."
        )
        return

    if user and entry:
        logger.debug(f"Service account {account.name} OK: exists in both MinIO and secret backend.")
        return

    # Create the service account in MinIO
    credentials = client.service_account_add(account.name)
    # Create an entry in the secret backend
    secrets.set_password(credentials)
    secrets.backend_dirty = True

    access_key = account.name
    if user:
        logger.debug(user)
        # TODO: check if user is correct.
        return

    logger.info(f"Created service account '{account.name}', access key: {access_key}")
