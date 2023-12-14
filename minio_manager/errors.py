from types import SimpleNamespace


class MinioManagerError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class MinioApiError(Exception):
    def __init__(self, error: SimpleNamespace):
        super().__init__(error)
        self.error_message = error.message
        self.cause_code = error.cause.error.Code
        self.cause_message = error.cause.error.Message
        self.request_id = error.cause.error.RequestID
        self.determine_cause()

    def determine_cause(self):
        if self.cause_code == "XMinioInvalidIAMCredentials":
            raise MinioInvalidIamCredentialsError(self.cause_message)
        if self.cause_code == "InternalError":
            raise MinioInternalError(self.cause_message)
        if self.cause_code == "XMinioAdminNoSuchUser":
            raise MinioNoSuchUserError(self.cause_message)
        if self.cause_code == "XMinioAdminNoSuchPolicy":
            raise MinioNoSuchPolicyError(self.cause_message)
        if self.cause_code == "XMinioAdminInvalidSecretKey":
            raise MinioInvalidSecretKeyError(self.cause_message)
        if self.cause_code == "XMinioAdminInvalidAccessKey":
            raise MinioInvalidAccessKeyError(self.cause_message)


class MinioInvalidIamCredentialsError(Exception):
    """Raised when the specified service account is not found."""


class MinioInternalError(Exception):
    """Raised when a MinIO internal error occurred."""


class MinioNoSuchUserError(Exception):
    """Raised when the specified user account is not found."""


class MinioNoSuchPolicyError(Exception):
    """Raised when the specified policy is not found."""


class MinioInvalidSecretKeyError(Exception):
    """Raised when the specified secret key is invalid."""


class MinioInvalidAccessKeyError(Exception):
    """Raised when the specified secret key is invalid."""
