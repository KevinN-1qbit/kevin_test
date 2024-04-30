import uuid
import logging.config
import configparser
import json
from logger.logger_config import get_logging_config
from logger.redis_logger import RedisHandler
from redis import Redis
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.exceptions import RequestValidationError, ValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from shared.database_client import DatabaseClient

from api.models.requests import TranspilerRequest, TranspilerModel
from api.models.responses import (
    HealthCheckResponse,
    TranspilerResponse,
    StatusEnum,
    TranspilerSolutionResponse,
)

# Load configs
config = configparser.ConfigParser()
config.read_file(open("/app/config/server.conf"))
use_database = config.getboolean("Database", "use_database")
db_table_name = config["Database"]["db_table_name"]
database_host = config["Database"]["host"]

# Setup Logger
is_slack_enabled = config.getboolean("Logger", "slack_logging_enabled")
is_redis_logging_enabled = config.getboolean("Logger", "redis_logging_enabled")
slack_webhook_id = config["Logger"]["slack_webhook_id"]
logging.config.dictConfig(get_logging_config(is_slack_enabled, slack_webhook_id))
logger = logging.getLogger(__name__)

# Set up Redis
redis_host = config["Redis"]["host"]
redis_port = config["Redis"]["port"]
transpiler_req_topic = config["Redis"]["transpiler_req"]
ttl_seconds = config["Redis"]["ttl_seconds"]


redis = Redis()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect redis
    redis.connection_pool.connection_kwargs["host"] = redis_host
    redis.connection_pool.connection_kwargs["port"] = redis_port
    yield
    # Close redis connection
    redis.close()


app = FastAPI(
    title=config["TranspilerNode"]["title"],
    version=config["TranspilerNode"]["version"],
    description="Documentation for the Transpiler API",
    lifespan=lifespan,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception):
    error = json.loads(exception.json())
    logger.error(error)
    return JSONResponse(
        status_code=422,
        content=error,
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exception):
    error = json.loads(exception.json())
    logger.error(error)
    return JSONResponse(
        status_code=422,
        content=error,
    )


@app.get("/healthcheck", response_model=HealthCheckResponse)
def healthcheck():
    """Check the health of the application.
    Returns:
        status (str): The health status of the server.
        application (str): The application name of the server.
    """
    logger.info("()")
    logger.info("- Return status OK")
    application = config["TranspilerNode"]["application"]
    return HealthCheckResponse(status="OK", application=application)


@app.post("/transpile", response_model=TranspilerResponse)
async def post_transpile(request: TranspilerRequest):
    """Creates a request and sends it to the Transpiler node.
    Returns:
        status (str): The status of the request.
        template_id (str): The transpiler id of the request.
    """
    logger.info("()")

    request_id = str(uuid4())

    try:
        if is_redis_logging_enabled:
            # Create and add redis handler to logger so that logs can be send to redis
            redis_handler = RedisHandler(redis, request_id + "_logs", ttl_seconds)
            logger.addHandler(redis_handler)

        logger.info(f"(request={{{request}}})")
        logger.debug(f"Generated id: {request_id}.")

        message = TranspilerModel(
            **request.dict(exclude_unset=True),
            request_id=request_id,
        )

        # Send message to Transpiler Node
        redis.rpush(transpiler_req_topic, message.json())

        # Update waiting status to get_request topic
        status_message = json.dumps({"status": StatusEnum.waiting})
        redis.rpush(request_id, status_message)

        if use_database:
            logger.info(f"Creating database entry with id: {request_id}")
            try:
                # Create entry in Database
                database_client = DatabaseClient(database_host)
                post_body = {"entry": {"status": StatusEnum.waiting},"entry_id": request_id, "table": db_table_name}
                logger.debug(f"Post body: {post_body}")

                # Send request
                database_client.post_request(post_body)
            except Exception as e:
                err_msg = f"Failed to create entry in database: {e}"
                logger.error(err_msg)
                raise Exception(err_msg)

    except Exception as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal Error",
        )
    finally:
        if is_redis_logging_enabled:
            logger.removeHandler(redis_handler)
            logger.info("Removed redis handler")

    response = TranspilerResponse(request_id=request_id, status=StatusEnum.waiting)

    logger.info(f"TranspilerResponse = {{{response}}}")
    return response


@app.get("/transpile/{request_id}", response_model=TranspilerSolutionResponse)
async def get_transpiled_circuit(request_id: str):
    """Gets the solution of given transpiler id.
    Returns:
        TranspilerSolutionResponse: Contains details about the transpiler solution
    """
    logger.info("()")

    # Check if request_id exists in redis
    topic = request_id
    if redis.exists(topic) == 0:
        # Check database if request_id doesn't exist
        if use_database:
            logger.info(f"Reading database entry with id: {request_id}")
            try:
                # Read database entry
                database_client = DatabaseClient(database_host)
                get_response = database_client.get_request(request_id, db_table_name)
            except Exception as e:
                err_msg = f"Failed to get entry in database: {e}"
                logger.error(err_msg)
                raise Exception(err_msg)

            if get_response.status_code == 404:
                err_msg = f"Invalid request id: {request_id}."
                logger.error(err_msg)
                raise HTTPException(
                    status_code=404,
                    detail=err_msg,
                )
            msg_dict = json.loads(get_response.content)

        else:
            err_msg = f"Invalid request id: {request_id}."
            logger.error(err_msg)
            raise HTTPException(
                status_code=404,
                detail=err_msg,
            )
    else:
        try:
            # Peek at the first element in topic
            msg = redis.lindex(topic, 0)
            msg_dict = json.loads(msg.decode())
        except Exception as e:
            error_msg = f"Internal Error + {e}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg,
            )

    response = TranspilerSolutionResponse(request_id=request_id, **msg_dict)

    logger.info(f"TranspilerSolutionResponse = {{{response}}}")
    return response


@app.get("/logs/{request_id}")
async def get_logs(request_id: str):
    """Gets the solution of given request ID.
    Args:
        request_id (str): The ID of the request.
    Returns:
        logs_array (array): The logs associated with the request ID.
    Raises:
        HTTPException (500): If there is an error retrieving the logs.
    """
    logger.info(f"request_id={request_id}")

    # Check if request_id_logs exists in redis
    topic = request_id + "_logs"
    if redis.exists(topic) == 0:
        err_msg = f"The provided request_id: {request_id} is either invalid or the logs have expired."
        logger.error(err_msg)
        raise HTTPException(
            status_code=404,
            detail=err_msg,
        )
    try:
        # Read logs from redis
        logs_array = redis.lrange(topic, 0, -1)
    except Exception as e:
        error_msg = f"Internal Error + {e}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg,
        )

    # Log the logs_array in bytes for illustration purpose
    logger.info(f"logs_array={logs_array}")

    # FastAPI will automaticaly handle decoding the bytes string to unicode string
    # when serializing the response to JSON.
    return logs_array


@app.post("/covert_basis")
async def post_covert_basis(qasm: str):
    # TODO
    pass


@app.get("/covert_basis")
async def get_covert_basis(qasm: str):
    # TODO
    pass
