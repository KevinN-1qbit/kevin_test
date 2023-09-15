import os
import uuid
import logging.config
import configparser
import json
import shutil
from logger.logger_config import get_logging_config
from redis import Redis
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.exceptions import RequestValidationError, ValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.models.requests import SKRequest, SKModel
from api.models.responses import (
    HealthCheckResponse,
    SKResponse,
    StatusEnum,
    SKSolutionResponse,
)

# Load configs
config = configparser.ConfigParser()
config.read_file(open("/app/config/server.conf"))

# Setup Logger
is_slack_enabled = config.getboolean("Slack", "slack_logging_enabled")
slack_webhook_id = config["Slack"]["slack_webhook_id"]
logging.config.dictConfig(get_logging_config(is_slack_enabled, slack_webhook_id))
logger = logging.getLogger(__name__)

# Set up Redis
redis_host = config["Redis"]["host"]
redis_port = config["Redis"]["port"]
sk_req_topic = config["Redis"]["sk_req"]


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
    title=config["SKNode"]["title"],
    version=config["SKNode"]["version"],
    description="Documentation for the SK API",
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
    application = config["SKNode"]["application"]
    return HealthCheckResponse(status="OK", application=application)


@app.post("/decompose", response_model=SKResponse)
async def decompose(request: SKRequest):
    """Creates a request and sends it to the SK node.
    Returns:
        status (str): The status of the request.
        template_id (str): The SK id of the request.
    """
    logger.info("()")
    logger.info(f"SKRequest = {{{request}}}")
    try:
        request_id = str(uuid4())
        message = SKModel(
            **request.dict(exclude_unset=True),
            request_id=request_id,
        )

        # Send message to SK Node
        redis.rpush(sk_req_topic, message.json())

        # Send waiting status to get request topic
        status_message = json.dumps({"status": StatusEnum.waiting})
        redis.rpush(request_id, status_message)

    except Exception as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal Error",
        )

    response = SKResponse(request_id=request_id, status=StatusEnum.waiting)

    logger.info(f"SKResponse = {{{response}}}")
    return response


@app.get("/decompose/{request_id}", response_model=SKSolutionResponse)
async def decompose(request_id: str):
    """Gets the solution of given sk id.
    Returns:
        SKSolutionResponse: Contains details about the SK solution
    """
    logger.info("()")

    # Check if request_id exists in redis
    topic = request_id
    number_of_topic_exists = redis.exists(topic)
    if number_of_topic_exists == 0:
        err_msg = f"Invalid request id: {request_id}."
        logger.error(err_msg)
        raise HTTPException(
            status_code=404,
            detail=err_msg,
        )

    try:
        topic = request_id
        # Peek at the first element in topic
        msg = redis.lindex(topic, 0)

    except Exception as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal Error",
        )

    msg_dict = json.loads(msg.decode())
    response = SKSolutionResponse(request_id=request_id, **msg_dict)

    logger.info(f"SKSolutionResponse = {{{response}}}")
    return response
