from pathlib import Path
from tempfile import NamedTemporaryFile

from minio_manager.classes.errors import MinioInvalidIamCredentialsError
from minio_manager.classes.mc_wrapper import McWrapper
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.secrets import MinioCredentials
from minio_manager.clients import get_mc_wrapper, get_minio_config, get_secret_manager
from minio_manager.utilities import get_env_var, logger, module_directory

sa_policy_embedded = f"{module_directory}/resources/service-account-policy-base.json"
sa_policy_base_file = get_env_var("MINIO_MANAGER_SERVICE_ACCOUNT_POLICY_BASE_FILE", sa_policy_embedded)


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

    return False


def generate_service_account_policy(account: ServiceAccount) -> Path:
    with Path(sa_policy_base_file).open() as base:
        base_policy = base.read()

    temp_file = NamedTemporaryFile(prefix=account.bucket, suffix=".json", delete=False)
    with temp_file as out:
        new_content = base_policy.replace("BUCKET_NAME_REPLACE_ME", account.bucket)
        out.write(new_content.encode("utf-8"))

    return Path(temp_file.name)


def handle_service_account(account: ServiceAccount):
    """
    Manage service accounts.

    Steps taken:
    1) check if service account exists in minio
    2) check if service account exists in secret backend
    3) if it exists in MinIO but not the secret backend, throw an error and return
    4) if it exists in the secret backend but not in MinIO, create it using the secret backend credentials
    5) if it does not, create service account in minio and secret backend

    Args:
        account (ServiceAccount)
    """
    client = get_mc_wrapper()
    secrets = get_secret_manager(get_minio_config())

    # Determine if access key credentials exists in secret backend
    credentials = secrets.get_credentials(account.name)
    # Determine if access key exists in MinIO
    sa_exists = service_account_exists(client, credentials)

    # Scenario 1: service account exists in MinIO but not in secret backend
    if sa_exists and not credentials.access_key:
        logger.error(
            f"Service account {account.name} exists in MinIO but not in secret backend! Manual intervention required."
        )
        logger.error(
            "Either find the credentials elsewhere and add them to the secret backend, or delete the service "
            "account from MinIO and try again."
        )
        return

    # Scenario 2: service account exists in secret backend but not in MinIO
    if credentials.secret_key and not sa_exists:
        logger.warning(
            f"Service account {account.name} exists in secret backend but not in MinIO. Using existing credentials."
        )
        client.service_account_add(credentials)
        sa_exists = True
        logger.info(f"Created service account '{credentials.name}', access key: {credentials.access_key}")

    # Scenario 3: service account does not exist in neither MinIO nor the secret backend
    if not sa_exists and not credentials.access_key:
        # TODO: catch scenario where an access key is deleted in MinIO, but MinIO does not accept the creation of a
        #  service account with the same access key, which sometimes happens.
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

    if account.policy_file:
        client.service_account_set_policy()
