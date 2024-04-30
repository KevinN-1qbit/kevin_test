import logging.config
import configparser
import json
import time
import os
from redis import Redis
from shared.database_client import DatabaseClient
from src.transpiler.circuit import Circuit
from src.main import transpile
from api.models.responses import StatusEnum
from logger.logger_config import get_logging_config
from logger.redis_logger import RedisHandler

# Load configs
config = configparser.ConfigParser()
config.read_file(open("/app/config/server.conf"))
use_database = config.getboolean("Database", "use_database")
db_table_name = config["Database"]["db_table_name"]
database_host = config["Database"]["host"]

# Setup Logger
is_slack_enabled = config.getboolean("Logger", "slack_logging_enabled")
slack_webhook_id = config["Logger"]["slack_webhook_id"]
is_redis_logging_enabled = config.getboolean("Logger", "redis_logging_enabled")
logging.config.dictConfig(get_logging_config(is_slack_enabled, slack_webhook_id))
logger = logging.getLogger(__name__)

redis_host = config["Redis"]["host"]
redis_port = config["Redis"]["port"]
ttl_seconds = config["Redis"]["ttl_seconds"]

# Create a global Redis instance
redis = Redis(host=redis_host, port=redis_port)
timeout_interval = config["TranspilerNode"]["timeout_interval"]


def transpiler_function(message):
    """
    Transpile the input circuit.

    Args:
        message (dict): The message containing the ciruit path to be transpiled.

    Raises:
        Exception: If there is an error running the transpiler with the given
        input.
    """
    logger.info("()")
    try:
        file_path = message["file_path"]
        language = message["language"]
        timeout = message["timeout"]
        epsilon = message["epsilon"]
        bypass_optimization = message["bypass_optimization"]
        request_id = message["request_id"]
        output_path = config["TranspilerNode"]["output_path"]
        optimizer_executable = config["Optimizer"]["executable"]

        # Get the base name of the file (including the extension)
        file_name_with_extension = os.path.basename(file_path)

        # Split the file name and its extension
        input_file_name, _ = os.path.splitext(file_name_with_extension)

        # remove suffix
        if "_post_sk" in input_file_name:
            input_file_name = input_file_name.replace("_post_sk", "")

        file_name = output_path + input_file_name
        topic = request_id
        report_message = {}
        redis_handler = None

        if is_redis_logging_enabled:
            # Create and add redis handler to logger so that logs can be send to redis
            redis_handler = RedisHandler(
                redis_client=redis,
                redis_topic=request_id + "_logs",
                ttl_seconds=ttl_seconds,
            )
            logger.addHandler(redis_handler)

        logger.info(f"(message={message})")

        # Update the status to excuting in get_request topic
        try:
            status_message = json.dumps({"status": StatusEnum.executing})
            redis.rpush(topic, status_message)
            if redis.llen(topic) > 1:
                # Remove the previous status message
                redis.lpop(topic)
            logger.debug("Successfully updated status to executing.")
        except Exception as e:
            err_msg = f"""The status update for the get_request topic with ID {request_id}
                       to executing has encountered an error: {e}"""
            logger.error(err_msg)
            raise Exception(err_msg)

        if use_database:
            logger.info(f"Updating database entry with id: {request_id}")
            try:
                # Update entry in Database
                database_client = DatabaseClient(database_host)
                put_body = {"entry_id": request_id,"update_data": {"status": StatusEnum.executing}, "table": db_table_name}

                # Send request
                database_client.put_request(put_body)
            except Exception as e:
                err_msg = f"Failed to update entry in database: {e}"
                logger.error(err_msg)
                raise Exception(err_msg)

        try:
            start_time = time.time()
            transpile(
                file_path,
                language,
                file_name,
                time_out=timeout,
                epsilon=epsilon,
                bypass_optimization=bypass_optimization,
                redis_handler=redis_handler,
                optimizer_executable=optimizer_executable
            )

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            logger.debug(f"Elapsed time in seconds: {elapsed_time}")
            logger.debug("Successfully compiled the transpiled circuit.")

            if bypass_optimization:
                circuit_path = file_name + "_basis_conversion.txt"
            else:
                circuit_path = file_name + "_transpile.txt"
                
            logger.debug(f"Transpiler circuit path: {circuit_path}")

            transpiled_circuit = Circuit(circuit_path)

            report_message = {
                "status": StatusEnum.done,
                "circuit_name": transpiled_circuit.name,
                "instruction_set": "pauli_rotations",
                "num_data_qubits_required": transpiled_circuit.num_qubits,
                "total_num_operations": transpiled_circuit.total_operations,
                "num_non_clifford_operations": transpiled_circuit.pi8,
                "num_clifford_operations": transpiled_circuit.pi4,
                "num_logical_measurements": transpiled_circuit.measurements,
                "transpiled_circuit_path": circuit_path,
                "elapsed_time": elapsed_time,
                "bypass_optimization": bypass_optimization
            }
            logger.debug("Going to update status to done.")
        except Exception as e:
            logger.error(f"Error Message: {e}")

            # Hardcode the error message for now
            e = "Something went wrong during the run."
            report_message = {"status": StatusEnum.failed, "message": e}
            logger.debug("Going to update status to failed.")

        logger.debug(f"report_message={report_message}")

        try:
            # Serialize report content into a JSON string
            serialized_report_string = json.dumps(report_message)
            # Update the result and status in get_request topic
            redis.rpush(topic, serialized_report_string)
            if redis.llen(topic) > 1:
                # Remove the previous status message
                redis.lpop(topic)
            logger.debug(
                "Successfully updated result and status to done/failed in get request topic."
            )
        except Exception as e:
            err_msg = f"""The update of the result in the get_request topic with ID
                       {request_id} has failed: {e}."""
            logger.error(err_msg)
            raise Exception(err_msg)

        if use_database:
            logger.info(f"Updating database entry with id: {request_id}")
            try:
                # Update database entry
                put_body = {"entry_id": request_id,"update_data": report_message, "table": db_table_name}

                # Send request
                database_client.put_request(put_body)
            except Exception as e:
                err_msg = f"Failed to update entry in database: {e}"
                logger.error(err_msg)
                raise Exception(err_msg)
                
    finally:
        if is_redis_logging_enabled:
            logger.removeHandler(redis_handler)
            logger.debug("Removed redis handler")

    logger.info("Transpiler finished")


if __name__ == "__main__":
    logger.info("Starting Transpiler Node")
    # Set up Redis
    request_topic = config["Redis"]["transpiler_req"]
    redis = Redis(host=redis_host, port=redis_port)

    while True:
        try:
            msg = redis.lpop(request_topic)
            if msg:
                logger.info("Redis Msg received")
                transpiler_function(json.loads(msg))
            else:
                time.sleep(int(timeout_interval))
        except Exception as e:
            logger.error(e)
            continue
