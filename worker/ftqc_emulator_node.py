import uuid
import logging.config
import configparser
import os
import json
import time
import shutil
import subprocess
from logger.logger_config import get_logging_config
from redis import Redis
from src.main import emulate_ftqc_json
from api.models.responses import StatusEnum

# Load configs
config = configparser.ConfigParser()
config.read_file(open("/app/config/server.conf"))

# Setup Logger
is_slack_enabled = config.getboolean("Slack", "slack_logging_enabled")
slack_webhook_id = config["Slack"]["slack_webhook_id"]
logging.config.dictConfig(get_logging_config(is_slack_enabled, slack_webhook_id))
logger = logging.getLogger(__name__)

redis_host = config["Redis"]["host"]
redis_port = config["Redis"]["port"]

# Create a global Redis instance
redis = Redis(host=redis_host, port=redis_port)
timeout_interval = config["FTQCNode"]["timeout_interval"]


def ftqc_emulate(message):
    logger.info("()")

    request_id = message["request_id"]
    code = message["code"]
    number_of_cores = message["number_of_cores"]
    protocol = message["protocol"]
    decoder = message["decoder"]
    qubit_technology = message["qubit_technology"]
    output_dir = config["FTQCNode"]["output_dir"]
    plot_filename = "ftqce_plot_" + request_id
    report_message = {}

    try:
        logger.debug("Starting FTQC emulation")
        report_message = emulate_ftqc_json(
            code,
            number_of_cores,
            protocol,
            decoder,
            qubit_technology,
            output_dir,
            plot_filename,
        )
        report_message["status"] = StatusEnum.done
        logger.debug("Done FTQC emulation")
    except Exception as e:
        logger.error(f"Error Message: {e}")

        # Hardcode the error message for now
        e = "Something went wrong during the run."
        report_message = {"status": StatusEnum.failed, "message": e}

    logger.debug(f"report_message={report_message}")
    # Serialize report message to JSON
    serialized_report = json.dumps(report_message)

    # Push report message
    report_topic = request_id
    redis.rpush(report_topic, serialized_report)

    logger.info("FTQC emulation finished")


if __name__ == "__main__":
    logger.info("Starting FTQC Node")
    # Set up Redis
    request_topic = config["Redis"]["ftqc_req"]
    redis = Redis(host=redis_host, port=redis_port)

    while True:
        try:
            msg = redis.lpop(request_topic)
            if msg:
                logger.info("Redis Msg received")
                ftqc_emulate(json.loads(msg))
            else:
                time.sleep(int(timeout_interval))
        except Exception as e:
            logger.error(e)
            continue
