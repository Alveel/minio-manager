import re
from logging import Filter, LogRecord
from re import Pattern


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
    def mask_secret(message: str, regex: Pattern) -> str:
        result = regex.search(message)
        if result:
            message = message.replace(result.group("secret"), "************")
        return message
