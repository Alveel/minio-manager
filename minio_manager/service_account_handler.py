import json

from minio.error import MinioAdminException

from minio_manager.classes.errors import MinioMalformedIamPolicyError, raise_specific_error
from minio_manager.classes.logging_config import logger
from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.secrets import secrets
from minio_manager.classes.settings import settings
from minio_manager.clients import admin_client, controller_user_policy
from minio_manager.utilities import compare_objects, increment_error_count


def service_account_exists(account: ServiceAccount):
    try:
        if account.access_key:
            admin_client.get_service_account(account.access_key)
            return True
    except MinioAdminException as mae:
        decoded_error = json.loads(mae._body)
        if decoded_error["Code"] == "XMinioInvalidIAMCredentials":
            # account does not exist in MinIO
            logger.debug(
                f"Error for {account.access_key}: {decoded_error['Code']}, trying to find it in other service accounts."
            )
        else:
            # another error occurred, raise it
            raise_specific_error(decoded_error["Code"], decoded_error["Message"], caused_by=mae)

    logger.debug(f"Access key for {account.full_name} not found in secret backend, trying to find it in MinIO.")
    sa_list = json.loads(admin_client.list_service_account(settings.minio_controller_user))  # type: dict
    for sa in sa_list["accounts"]:
        access_key = sa["accessKey"]
        sa_info = json.loads(admin_client.get_service_account(access_key))  # type: dict
        if "name" not in sa_info:
            continue
        sa_name = sa_info.get("name")
        # Easy check for service accounts that are 32 characters or fewer long
        if account.full_name == sa_name:
            logger.debug(f"Found access key '{access_key}' for '{account.full_name}' in MinIO.")
            return True

        sa_description = sa_info.get("description")
        if not sa_description:
            logger.debug(f"Service account '{sa_name}' has no description, skipping.")
            continue

        # This ensures that the start of the description matches the full name of the account exactly in cases where
        # the full name is longer than 32 characters.
        # This program provides a description formatted as "{full_name} - {description}"
        if sa_description.startswith(f"{account.full_name} - "):
            logger.debug(f"Found access key '{access_key}' for '{account.full_name}' in MinIO.")
            return True

        # This is a fallback for when the description does not match the full name exactly
        if sa_name == account.name:
            logger.warning(f"Found possible access key '{access_key}' for '{account.name}' in MinIO.")
            logger.warning("Please verify and modify the description accordingly.")
            increment_error_count()
            return False
    return False


def apply_base_policy(account: ServiceAccount):
    account.generate_service_account_policy()
    admin_client.update_service_account(**account.as_dict)


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

    current_service_account = json.loads(admin_client.get_service_account(account.access_key))  # type: dict
    current_policy = json.loads(current_service_account.get("policy"))  # type: dict

    policies_diff_pre = compare_objects(current_policy, desired_policy)
    if not policies_diff_pre:
        return

    logger.debug(f"Updating service account policy for '{account.full_name}'.")
    try:
        admin_client.update_service_account(**account.as_dict)
    except MinioMalformedIamPolicyError:
        logger.error(
            f"Policy for service account '{account.full_name}' is malformed, reverting to base policy for service account."
        )
        apply_base_policy(account)
        return

    updated_service_account = json.loads(admin_client.get_service_account(account.access_key))  # type: dict
    updated_policy = json.loads(updated_service_account.get("policy"))  # type: dict
    policies_diff_post = compare_objects(updated_policy, desired_policy)
    if not policies_diff_post:
        logger.debug(f"Policy for service account '{account.full_name}' successfully updated.")
        return

    logger.warning(f"Applying policy for service account '{account.full_name}' failed.")
    logger.debug("Comparing controller user policy to currently applied policy...")
    policies_diff_fallback = compare_objects(controller_user_policy, updated_policy)
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
    sa_exists = service_account_exists(credentials)

    # Scenario 1: service account exists in MinIO but not in secret backend
    if sa_exists and not credentials.access_key:
        logger.error(
            f"Service account {credentials.full_name} exists in MinIO but not in secret backend! Manual intervention required."
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
            f"Service account {credentials.full_name} exists in secret backend but not in MinIO. Using existing credentials."
        )
        try:
            admin_client.add_service_account(**credentials.as_dict)
            logger.info(f"Created service account '{credentials.full_name}' with access key '{credentials.access_key}'")
        except MinioAdminException as mae:
            decoded_error = json.loads(mae._body)
            if decoded_error["Code"] == "XMinioMalformedIAMPolicy":
                logger.error(f"Malformed IAM policy for service account '{credentials.full_name}'")
                increment_error_count()
                return
            raise_specific_error(decoded_error["Code"], decoded_error["Message"], caused_by=mae)
        sa_exists = True
        logger.info(f"Created service account '{credentials.full_name}', access key: {credentials.access_key}")

    # Scenario 3: service account does not exist in neither MinIO nor the secret backend
    if not sa_exists and not credentials.access_key:
        logger.debug(f"Creating service account '{credentials.full_name}'")
        # TODO: catch scenario where an access key is deleted in MinIO, but MinIO does not accept the creation of a
        #  service account with the same access key, which sometimes happens.
        # Create the service account in MinIO
        new_service_account_raw = admin_client.add_service_account(**credentials.as_dict)
        new_service_account_dict = json.loads(new_service_account_raw)["credentials"]  # type: dict
        credentials.access_key = new_service_account_dict["accessKey"]
        credentials.secret_key = new_service_account_dict["secretKey"]
        # Create credentials in the secret backend
        secrets.set_password(credentials)
        logger.info(f"Created service account '{credentials.full_name}' with access key '{credentials.access_key}'")

    if credentials.policy_file:
        handle_sa_policy(credentials)
        if credentials.policy_generated:
            credentials.policy_file.unlink(missing_ok=True)
