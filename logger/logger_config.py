import os


def get_logging_config(slack_enabled, slack_webhook_id):
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            # Configuring all loggers using the blank string as the logger name.
            # This allows control over the level of chatty third-party loggers.
            # If you want to configure a specific logger, provide its name
            # instead of the empty string.
            "": {
                "level": os.getenv("LOG_LEVEL_APP"),
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
                "filename": os.getenv("LOG_FILE"),
                "mode": "a",
                "maxBytes": 100000,
                "backupCount": 20,
            },
            "slack": {
                "formatter": "formatter",
                "class": "logger.slack_logger.SlackHandler",
                "slack_webhook_id": slack_webhook_id,
                "level": "ERROR",
            },
        },
        "formatters": {
            "formatter": {
                "format": "[%(asctime)s] [%(name)s] "
                "[%(levelname)s][%(funcName)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
    }

    if slack_enabled:
        LOGGING_CONFIG["loggers"][""]["handlers"].append("slack")

    return LOGGING_CONFIG
