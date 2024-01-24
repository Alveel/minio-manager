from pathlib import Path
from tempfile import NamedTemporaryFile

from .classes.errors import MinioInvalidIamCredentialsError
from .classes.mc_wrapper import McWrapper
from .classes.minio_resources import ServiceAccount
from .classes.secrets import MinioCredentials, SecretManager
from .utilities import logger


def service_account_exists(client: McWrapper, credentials: MinioCredentials):
    try:
        if credentials.access_key:
            client.service_account_info(credentials.access_key)
            return True
    except MinioInvalidIamCredentialsError as e:
        # account does not exist in MinIO
        logger.debug(f"Error for {credentials.access_key}: {e}")

    logger.debug(f"Access key for {credentials.name} not found in secret backend, trying to find it in MinIO.")
    sa_list = client.service_account_list(client.cluster_controller_user)
    for sa in sa_list:
        sa_info = client.service_account_info(sa.accessKey)
        if hasattr(sa_info, "name") and sa_info.name == credentials.name:
            logger.debug(f"Found access key '{sa_info.accessKey}' for '{credentials.name}' in MinIO: {sa_info}")
            return True

    logger.warning(f"Service account {credentials.name} does not exist or has no user-friendly name.")
    return False


def generate_service_account_policy(account: ServiceAccount) -> Path:
    with Path("examples/service-account-policy-base.json").open() as base:
        base_policy = base.read()

    temp_file = NamedTemporaryFile(prefix=account.bucket, suffix=".json", delete=False)
    with temp_file as out:
        new_content = base_policy.replace("BUCKET_NAME_REPLACE_ME", account.bucket)
        out.write(new_content.encode("utf-8"))

    return Path(temp_file.name)


def handle_service_account(client: McWrapper, secrets: SecretManager, account: ServiceAccount):
    """
    Manage service accounts.

    Steps taken:
    1) check if service account exists in minio
    2) check if service account exists in secret backend
    3) if it exists in MinIO but not the secret backend, throw an error and return
    4) if it exists in the secret backend but not in MinIO, create it using the secret backend credentials
    5) if it does not, create service account in minio and secret backend

    Args:
        secrets (SecretManager)
        client (McWrapper)
        account (ServiceAccount)
    """
    # Determine if access key credentials exists in secret backend
    credentials = secrets.get_credentials(account.name)
    # Determine if access key exists in MinIO
    sa_exists = service_account_exists(client, credentials)

    if sa_exists and not credentials.access_key:
        logger.error(
            f"Service account {account.name} exists in MinIO but not in secret backend! Manual intervention required."
        )
        logger.error(
            "Either find the credentials elsewhere and add them to the secret backend, or delete the service "
            "account from MinIO and try again."
        )
        return

    if credentials.secret_key:
        logger.debug(
            f"Service account {account.name} exists in secret backend but not in MinIO. Using existing credentials."
        )
        client.service_account_add(credentials)
        logger.info(f"Created service account '{credentials.name}', access key: {credentials.access_key}")
    else:
        # Create the service account in MinIO
        credentials = client.service_account_add(credentials)
        # Create credentials in the secret backend
        secrets.set_password(credentials)
        logger.info(f"Created service account '{credentials.name}' with access key '{credentials.access_key}'")

    if account.bucket:
        # TODO: validate existing policy before assigning
        policy_file = generate_service_account_policy(account)
        client.service_account_set_policy(credentials.access_key, str(policy_file))
        policy_file.unlink()
