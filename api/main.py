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

from api.models.requests import FTQCRequest, FTQCModel
from api.models.responses import (
    HealthCheckResponse,
    FTQCResponse,
    StatusEnum,
    FTQCSolutionResponse,
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
ftqc_req_topic = config["Redis"]["ftqc_req"]


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
    title=config["FTQCNode"]["title"],
    version=config["FTQCNode"]["version"],
    description="Documentation for the FTQC API",
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
    application = config["FTQCNode"]["application"]
    return HealthCheckResponse(status="OK", application=application)


@app.post("/emulate", response_model=FTQCResponse)
async def post_emulate(request: FTQCRequest):
    """Creates a request and sends it to the FTQC node.
    Returns:
        status (str): The status of the request.
        template_id (str): The ftqc id of the request.
    """
    logger.info("()")
    try:
        request_id = str(uuid4())
        message = FTQCModel(
            **request.dict(exclude_unset=True),
            request_id=request_id,
        )

        # Send message to FTQC Node
        redis.rpush(ftqc_req_topic, message.json())

    except Exception as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal Error",
        )

    response = FTQCResponse(request_id=request_id, status=StatusEnum.executing)

    logger.info(f"FTQCResponse = {{{response}}}")
    return response


@app.get("/emulate/{request_id}", response_model=FTQCSolutionResponse)
async def get_emulated_report(request_id: str):
    """Gets the report of given ftqc id.
    Returns:
        FTQCSolutionResponse: Contains details about the ftqc solution
    """
    logger.info("()")
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

    if msg:
        msg_dict = json.loads(msg.decode())
        response = FTQCSolutionResponse(request_id=request_id, **msg_dict)
    else:
        status = StatusEnum.executing
        response = FTQCSolutionResponse(request_id=request_id, status=status)

    logger.info(f"FTQCSolutionResponse = {{{response}}}")
    return response
