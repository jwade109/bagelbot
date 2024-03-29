import logging
import sys
from ws_dir import WORKSPACE_DIRECTORY


LOG_FILENAME     = WORKSPACE_DIRECTORY + "/log.txt"
ARCHIVE_FILENAME = WORKSPACE_DIRECTORY + "/private/archive.txt"


class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)-8s %(lineno)-5d %(filename)-25s %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(CustomFormatter())

log = logging.getLogger("bagelbot")
log.setLevel(logging.DEBUG)
log.addHandler(stdout_handler)


file_fmt = logging.Formatter(
    "%(levelname)-8s %(asctime)-25s %(name)-16s %(funcName)-40s %(message)s")
file_handler = logging.FileHandler(LOG_FILENAME)
file_handler.setFormatter(file_fmt)
log.addHandler(file_handler)
