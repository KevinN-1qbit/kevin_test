import configparser
import logging

# Load configs
config = configparser.ConfigParser()
config.read_file(open("src/config/ftqc.conf"))
log_level = config["Logger"]["log_level"]
log_file = config["Logger"]["log_file"]

# Define a custom logging level named trace to log all the details
TRACE = logging.DEBUG - 1

# Register the custom level
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kws):
    """Log a message with the custom TRACE level.

    Args:
        message (str): The message to be logged.
        *args: Additional positional arguments to be passed to the logging message.
        **kws: Additional keyword arguments to be passed to the logging message.
    """
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kws)


# Assign the trace method to the Logger class
logging.Logger.trace = trace


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        # Configure all loggers
        "": {
            "level": log_level,
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "handlers": {
        "console": {
            "formatter": "formatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "formatter",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "mode": "a",
            "maxBytes": 100000,
            "backupCount": 20,
        },
    },
    "formatters": {
        "formatter": {
            "format": "[%(asctime)s] [%(name)s]"
            "[%(levelname)s][%(funcName)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
}
