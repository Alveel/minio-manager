import logging
import re
from logging import Filter, Formatter, LogRecord

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
    wrapper_secret_re = re.compile(r"--secret-key (?P<secret>[\w+/]*)")
    alias_set_secret_re = re.compile(r"alias set .+ (?P<secret>[\w+/]*)$")

    def filter(self, record: LogRecord) -> bool:
        if "--secret" in record.msg:
            record.msg = self.mask_secret(record.msg, self.wrapper_secret_re)
        if "alias set" in record.msg:
            record.msg = self.mask_secret(record.msg, self.alias_set_secret_re)

        return True

    @staticmethod
    def mask_secret(message: str, regex: re.Pattern) -> str:
        result = regex.search(message)
        if result:
            message = message.replace(result.group("secret"), "************")
        return message


class MinioManagerFormatter(Formatter):
    def __init__(self, log_level: int):
        self.log_level = log_level
        if log_level is logging.INFO:
            log_format = "[{asctime}] [{levelname:^8s}] {message}"
            super().__init__(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S", style="{")
        else:
            log_format = "[{asctime}] [{levelname:^8s}] [{filename:>26s}:{lineno:<4d} - {funcName:<24s} ] {message}"
            super().__init__(fmt=log_format, style="{")

    def format(self, record: LogRecord):  # noqa: A003
        if record.levelname in COLORS:
            record.msg = COLORS[record.levelname] + record.msg + RESET
            # record.levelname = COLORS[record.levelname] + record.levelname + RESET

        return super().format(record)


class MinioManagerLogger(logging.Logger):
    def __init__(self, name: str, log_level: str):
        super().__init__(name)
        if log_level == "INFO":
            self.setLevel(logging.INFO)
        else:
            self.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        formatter = MinioManagerFormatter(self.level)
        this_filter = MinioManagerFilter()
        handler.setFormatter(formatter)
        handler.addFilter(this_filter)
        self.addHandler(handler)
