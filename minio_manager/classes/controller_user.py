from minio_manager.classes.minio_resources import ServiceAccount
from minio_manager.classes.secrets import secrets
from minio_manager.classes.settings import settings


class ControllerUser(ServiceAccount):
    """
    ControllerUser represents the controller user of our application.
    """

    def __init__(self, name: str):
        super().__init__(name=name)
        account = secrets.get_credentials(self, required=True)
        self.access_key = account.access_key
        self.secret_key = account.secret_key


controller_user = ControllerUser(name=settings.minio_controller_user)
