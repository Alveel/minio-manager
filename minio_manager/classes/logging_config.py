import re
from logging import Filter


class MinioManagerFilter(Filter):
    wrapper_secret_re = re.compile(r"--secret-key (?P<secret>[\w+/]*)")

    def filter(self, record):
        if "--secret" in record.msg:
            record.msg = self.mask_wrapper_secret(record.msg)

        return True

    def mask_wrapper_secret(self, message):
        result = self.wrapper_secret_re.search(message)
        if result:
            message = message.replace(result.group("secret"), "************")
        return message
