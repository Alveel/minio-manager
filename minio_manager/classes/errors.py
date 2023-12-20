class MinioManagerBaseError(Exception):
    """Base class for Minio Manager errors."""

    def __init__(self, message: str, cause=None):
        super().__init__(f"{message}: {cause}" if cause else message)


class MinioInvalidIamCredentialsError(MinioManagerBaseError):
    """Raised when invalid IAM credentials are used."""


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


error_map = {
    "XMinioInvalidIAMCredentials": MinioInvalidIamCredentialsError,
    "InvalidAccessKeyId": MinioInvalidAccessKeyId,
    "XMinioIAMServiceAccountNotAllowed": MinioIamServiceAccountNotAllowedError,
    "InternalError": MinioInternalError,
    "XMinioAdminNoSuchUser": MinioNoSuchUserError,
    "XMinioAdminNoSuchPolicy": MinioNoSuchPolicyError,
    "XMinioAdminInvalidSecretKey": MinioInvalidSecretKeyError,
    "XMinioAdminInvalidAccessKey": MinioInvalidAccessKeyError,
}


def raise_specific_error(error_code, error_message):
    if error_code not in error_map:
        raise MinioManagerBaseError(error_code, error_message)
    raise error_map[error_code](error_message)
