from minio_manager.classes.secrets import secrets
from minio_manager.classes.settings import settings


class ControllerUser:
    """
    ControllerUser represents the controller user of our application.

    name: The name of the controller user
    access_key: The access key of the controller user
    secret_key: The secret key of the controller user
    """

    name: str
    access_key: str
    secret_key: str

    def __init__(self, name: str):
        self.name = name
        credentials = secrets.get_credentials(name)
        self.access_key = credentials.access_key
        self.secret_key = credentials.secret_key


controller_user = ControllerUser(name=settings.minio_controller_user)
