from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class StatusEnum(str, Enum):
    done = "done"
    executing = "executing"
    failed = "failed"


class HealthCheckResponse(BaseModel):
    """Healthcheck response model."""

    status: str = Field(description="The health of this server.")
    application: str = Field(
        description="The name of the application running on this server."
    )


class SKResponse(BaseModel):
    """SK response model."""

    request_id: str = Field(description="Id of the SK job request.")
    status: StatusEnum = Field(description="Current status of SK job.")


class SKSolutionResponse(SKResponse):
    """SKsolution response model."""

    sk_circuit_path: Optional[str] = Field(description="Path of the SK circuit.")
    accumulated_error: Optional[float] = Field(
        description="Accumulated_error of the SK circuit."
    )
    message: Optional[str] = Field(description="Error message when status is failed.")
