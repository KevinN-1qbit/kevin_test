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
from skalg.qiskit_sk import run_sk_pipeline
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
timeout_interval = config["SKNode"]["timeout_interval"]


def decompose_sk(message):
    logger.info("()")

    circuit_path = message["circuit_path"]
    error_budget = message["error_budget"]
    request_id = message["request_id"]
    output_path = config["SKNode"]["output_path"]

    sk_output_path = output_path + request_id + "_post_sk.qasm"
    report_message = {}

    try:
        run_sk_pipeline(circuit_path, sk_output_path, error_budget)

        # TODO implement error calculation
        accumulated_error = 0.0001

        report_message = {
            "status": StatusEnum.done,
            "sk_circuit_path": sk_output_path,
            "accumulated_error": accumulated_error,
        }
        logger.debug(f"SK circuit path: {{{sk_output_path}}}")
    except Exception as e:
        logger.error(f"Error Message: {e}")

        # Hardcode the error message for now
        e = "Something went wrong during the run."
        report_message = {"status": StatusEnum.failed, "message": e}

    logger.debug(f"report_message={report_message}")
    # Serialize report message to JSON
    serialized_report = json.dumps(report_message)

    # Push circuit path message
    topic = request_id
    redis.rpush(topic, serialized_report)

    logger.info("SK finished")


if __name__ == "__main__":
    logger.info("Starting SK Node")

    request_topic = config["Redis"]["SK_req"]

    while True:
        try:
            msg = redis.lpop(request_topic)
            if msg:
                logger.info("Redis Msg received")
                decompose_sk(json.loads(msg))
            else:
                time.sleep(int(timeout_interval))
        except Exception as e:
            logger.error(e)
            continue
