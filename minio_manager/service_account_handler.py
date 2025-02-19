from minio_manager.classes.errors import MinioInvalidIamCredentialsError, MinioMalformedIamPolicyError
from minio_manager.classes.logging_config import logger
from minio_manager.classes.mc_wrapper import McWrapper, mc_wrapper
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.secrets import secrets
from minio_manager.classes.settings import settings
from minio_manager.clients import controller_user_policy
from minio_manager.utilities import compare_objects, increment_error_count


def service_account_exists(client: McWrapper, account: ServiceAccount):
    try:
        if account.access_key:
            client.service_account_info(account.access_key)
            return True
    except MinioInvalidIamCredentialsError as e:
        # account does not exist in MinIO
        logger.debug(f"Error for {account.access_key}: {e}")

    logger.debug(f"Access key for {account.full_name} not found in secret backend, trying to find it in MinIO.")
    sa_list = client.service_account_list(settings.minio_controller_user)
    for sa in sa_list:
        sa_info = client.service_account_info(sa["accessKey"])
        if "name" in sa_info and sa_info["name"] == account.name:
            logger.debug(f"Found access key '{sa_info['accessKey']}' for '{account.full_name}' in MinIO: {sa_info}")
            return True

    return False


def apply_base_policy(account: ServiceAccount):
    account.generate_service_account_policy()
    mc_wrapper.service_account_set_policy(account.access_key, str(account.policy_file))


def handle_sa_policy(account: ServiceAccount):
    """
    Manage policies for service accounts.

    Compare the desired policy with what is currently applied, and update if needed.
    Retrieves the updated policy and compares it again. If it does not match, compare to the controller user's policy.
    If those match, the supplied policy had more permissions than allowed, and we have to revert to the base policy.

    Args:
        account (ServiceAccount)
    """
    desired_policy = account.policy

    current_policy = mc_wrapper.service_account_get_policy(account.access_key)

    policies_diff_pre = compare_objects(current_policy, desired_policy)
    if not policies_diff_pre:
        return

    logger.debug(f"Updating service account policy for '{account.full_name}'.")
    try:
        mc_wrapper.service_account_set_policy(account.access_key, str(account.policy_file))
    except MinioMalformedIamPolicyError:
        logger.error(
            f"Policy for service account '{account.full_name}' is malformed, reverting to base policy for service account."
        )
        apply_base_policy(account)
        return

    # TODO: so this works as intended, but MinIO somehow now seems to accept a policy with more permissions?
    #  it won't actually allow the actions, but the policy is still valid and now won't get updated..?
    current_updated_policy = mc_wrapper.service_account_get_policy(account.access_key)
    policies_diff_post = compare_objects(current_updated_policy, desired_policy)
    if not policies_diff_post:
        return

    logger.warning(f"Applying policy for service account '{account.full_name}' failed.")
    logger.debug("Retrieving controller user credentials...")
    logger.debug("Comparing controller user policy to currently applied policy...")
    policies_diff_fallback = compare_objects(controller_user_policy, current_updated_policy)
    if policies_diff_fallback:
        logger.error("Unknown situation where the live service account policy")
        logger.error("a) does not match what we tried to apply;")
        logger.error("b) also does not match to the controller user's policy, which it should fall back to if")
        logger.error("the policy we tried to apply has more permissions than the controller user's.")
        increment_error_count()

    logger.warning(f"Reverting to base policy for service account '{account.full_name}'")
    apply_base_policy(account)


def handle_service_account(bare_account: ServiceAccount):
    """
    Manage service accounts.

    Steps taken:
    1) check if service account exists in minio
    2) check if service account exists in secret backend
    3) if it exists in MinIO but not the secret backend, throw an error and return
    4) if it exists in the secret backend but not in MinIO, create it using the secret backend credentials
    5) if it does not, create service account in minio and secret backend
    6) if a policy_file is configured, load it and try to apply it for the service account

    Args:
        bare_account (ServiceAccount): the service account to manage containing only basic details
    """
    # Determine if access key credentials exists in secret backend
    credentials = secrets.get_credentials(bare_account)
    # Determine if access key exists in MinIO
    sa_exists = service_account_exists(mc_wrapper, credentials)

    # Scenario 1: service account exists in MinIO but not in secret backend
    if sa_exists and not credentials.access_key:
        logger.error(
            f"Service account {bare_account.full_name} exists in MinIO but not in secret backend! Manual intervention required."
        )
        logger.error(
            "Either find the credentials elsewhere and add them to the secret backend, or delete the service "
            "account from MinIO and try again."
        )
        increment_error_count()
        return

    # Scenario 2: service account exists in secret backend but not in MinIO
    if credentials.secret_key and not sa_exists:
        logger.warning(
            f"Service account {bare_account.full_name} exists in secret backend but not in MinIO. Using existing credentials."
        )
        mc_wrapper.service_account_add(credentials)
        sa_exists = True
        logger.info(f"Created service account '{credentials.full_name}', access key: {credentials.access_key}")

    # Scenario 3: service account does not exist in neither MinIO nor the secret backend
    if not sa_exists and not credentials.access_key:
        # TODO: catch scenario where an access key is deleted in MinIO, but MinIO does not accept the creation of a
        #  service account with the same access key, which sometimes happens.
        # Create the service account in MinIO
        credentials = mc_wrapper.service_account_add(credentials)
        # Create credentials in the secret backend
        secrets.set_password(credentials)
        logger.info(f"Created service account '{credentials.full_name}' with access key '{credentials.access_key}'")

    bare_account.access_key = credentials.access_key
    bare_account.secret_key = credentials.secret_key

    if bare_account.policy_file:
        handle_sa_policy(bare_account)
        if bare_account.policy_generated:
            bare_account.policy_file.unlink(missing_ok=True)
