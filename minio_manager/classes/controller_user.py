from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.secrets import secrets
from minio_manager.classes.settings import settings


class ControllerUser(ServiceAccount):
    """
    ControllerUser represents the controller user of our application.
    """

    def __init__(self, name: str):
        basic_account = ServiceAccount(name=name)
        account = secrets.get_credentials(basic_account, required=True)
        super().__init__(account.full_name, access_key=account.access_key, secret_key=account.secret_key)


controller_user = ControllerUser(name=settings.minio_controller_user)
