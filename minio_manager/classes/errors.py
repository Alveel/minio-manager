from minio_manager.classes.logging_config import logger
from minio_manager.classes.settings import settings


class MinioManagerBaseError(Exception):
    """Base class for Minio Manager errors."""

    def __init__(self, message: str, cause=None, caused_by=None):
        if caused_by:
            self.__cause__ = caused_by
        super().__init__(f"{message}: {cause}" if cause else message)


class MinioInvalidIamCredentialsError(MinioManagerBaseError):
    """Raised when invalid IAM credentials are used."""


class MinioMalformedIamPolicyError(MinioManagerBaseError):
    """Raised when an invalid IAM policy is provided."""


class MinioInvalidAccessKeyId(MinioManagerBaseError):
    """Raised when an invalid user access key ID is provided."""


class MinioInternalError(MinioManagerBaseError):
    """Raised when a MinIO internal error occurred."""


class MinioNoSuchUserError(MinioManagerBaseError):
    """Raised when a specified user account is not found."""


class MinioNoSuchPolicyError(MinioManagerBaseError):
    """Raised when a specified policy is not found."""


class MinioInvalidSecretKeyError(MinioManagerBaseError):
    """Raised when an invalid secret key is used."""


class MinioInvalidAccessKeyError(MinioManagerBaseError):
    """Raised when an invalid access key is used."""


class MinioIamServiceAccountNotAllowedError(MinioManagerBaseError):
    """Raised when trying to add a service account that already exists."""


class MinioAccessDeniedError(MinioManagerBaseError):
    """Raised when executing an action that is not allowed."""

    def __init__(self, message, cause=None):
        message = "Verify the access policies of the controller user and configured access key."
        super().__init__(message)


error_map = {
    "BaseError": MinioManagerBaseError,
    "ConnectionError": ConnectionError,
    "XMinioInvalidIAMCredentials": MinioInvalidIamCredentialsError,
    "InvalidAccessKeyId": MinioInvalidAccessKeyId,
    "XMinioIAMServiceAccountNotAllowed": MinioIamServiceAccountNotAllowedError,
    "XMinioMalformedIAMPolicy": MinioMalformedIamPolicyError,
    "InternalError": MinioInternalError,
    "XMinioAdminNoSuchUser": MinioNoSuchUserError,
    "XMinioAdminNoSuchPolicy": MinioNoSuchPolicyError,
    "XMinioAdminInvalidSecretKey": MinioInvalidSecretKeyError,
    "XMinioAdminInvalidAccessKey": MinioInvalidAccessKeyError,
    "AccessDenied": MinioAccessDeniedError,
}


def raise_specific_error(error_code: str, error_message: str, caused_by: Exception | None = None):
    """Raise a specific Minio Manager error.
    If the log level is DEBUG, raise the relevant exception.
    If the log level is INFO, cleanly log the error and exit with code 1.
    If the error code is not a known issue, raise a generic MinioManagerBaseError.

    Args:
        error_code (str): the error code
        error_message (str): the error message
        caused_by (Exception): the exception that caused the error
    """
    if error_code not in error_map:
        raise MinioManagerBaseError(error_code, error_message, caused_by)

    if settings.log_level == "DEBUG":
        # Is this really necessary? I keep seeing None at the end of the stack trace without it.
        if caused_by:
            raise error_map[error_code](error_message, caused_by)
        raise error_map[error_code](error_message)

    err_str = f"Exception occurred with code {error_code}: {error_message}"
    if caused_by:
        err_str += f", caused by {caused_by!s}"
    logger.critical(err_str)
