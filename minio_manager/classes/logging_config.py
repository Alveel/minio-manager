import re
from logging import DEBUG, INFO, Filter, Formatter, Logger, LogRecord, StreamHandler

from minio_manager.classes.settings import settings

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
PURPLE = "\033[0;35m"
BOLD = "\033[1m"
RESET = "\033[0m"

COLORS = {
    "DEBUG": PURPLE,
    "INFO": GREEN,
    "WARNING": YELLOW,
    "ERROR": RED,
    "CRITICAL": BOLD + RED,
}


class MinioManagerFilter(Filter):
    """
    The MinioManagerFilter is a custom logging Filter that masks secret values.
    """

    wrapper_secret_re = re.compile(r"--secret-key (?P<secret>[\w+/]*)")
    alias_set_secret_re = re.compile(r"alias set .+ (?P<secret>[\w+/]*)$")
    env_keepass_password_re = re.compile(r"MINIO_MANAGER_KEEPASS_PASSWORD: (?P<secret>[\w+/]*)$")
    env_secret_key_re = re.compile(r"MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY: (?P<secret>[\w+/]*)$")

    def filter(self, record: LogRecord) -> bool:
        if not isinstance(record.msg, str):
            return True

        if "--secret" in record.msg:
            record.msg = self.mask_secret(record.msg, self.wrapper_secret_re)
        if "alias set" in record.msg:
            record.msg = self.mask_secret(record.msg, self.alias_set_secret_re)
        if "MINIO_MANAGER_KEEPASS_PASSWORD" in record.msg:
            record.msg = self.mask_secret(record.msg, self.env_keepass_password_re)
        if "MINIO_MANAGER_SECRET_BACKEND_S3_SECRET_KEY" in record.msg:
            record.msg = self.mask_secret(record.msg, self.env_secret_key_re)

        return True

    @staticmethod
    def mask_secret(message: str, regex: re.Pattern) -> str:
        result = regex.search(message)
        if result:
            message = message.replace(result.group("secret"), "************")
        return message


class MinioManagerFormatter(Formatter):
    """
    The MinioManagerFormatter is a custom logging Formatter that provides formatting and colourises log messages.
    """

    def __init__(self, level: int):
        self.log_level = level
        if level is INFO:
            log_format = "[{asctime}] [{levelname:^8s}] {message}"
            super().__init__(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S", style="{")
        else:
            log_format = "[{asctime}] [{levelname:^8s}] [{filename:>26s}:{lineno:<4d} - {funcName:<24s} ] {message}"
            super().__init__(fmt=log_format, style="{")

    def format(self, record: LogRecord):
        if isinstance(record.msg, str) and record.levelname in COLORS:
            record.msg = COLORS[record.levelname] + record.msg + RESET

        # noinspection StrFormat
        return super().format(record)


class MinioManagerLogger(Logger):
    """
    The MinioManagerLogger is a custom Logger that implements our MinioManagerFilter and MinioManagerFormatter.
    """

    def __init__(self, name: str, level: str):
        super().__init__(name)
        if level == "INFO":
            self.setLevel(INFO)
        else:
            self.setLevel(DEBUG)

        handler = StreamHandler()
        formatter = MinioManagerFormatter(self.level)
        this_filter = MinioManagerFilter()
        handler.setFormatter(formatter)
        handler.addFilter(this_filter)
        self.addHandler(handler)


log_level = settings.log_level
log_name = "root" if log_level == "DEBUG" else "minio-manager"
logger = MinioManagerLogger(log_name, log_level)
logger.debug(f"Configured log level: {log_level}")
