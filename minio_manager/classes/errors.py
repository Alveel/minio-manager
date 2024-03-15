class MinioManagerBaseError(Exception):
    """Base class for Minio Manager errors."""

    def __init__(self, message: str, cause=None):
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


def raise_specific_error(error_code: str, error_message: str):
    """Raise a specific Minio Manager error.

    TODO: only _raise_ if log level is DEBUG. Just do logger.error/critical if it's INFO.

    Args:
        error_code (str): the error code
        error_message (str): the error message
    """
    if error_code not in error_map:
        raise MinioManagerBaseError(error_code, error_message)
    raise error_map[error_code](error_message)
