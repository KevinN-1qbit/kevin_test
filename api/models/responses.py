from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict


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


class ParityCheckTime(BaseModel):
    value: float
    unit: str


class FittingParam(BaseModel):
    value: float
    error: float


class Fit(BaseModel):
    functional_form: str
    fitting_parameters: Dict[str, FittingParam]


class FTQCResponse(BaseModel):
    """FTQC response model."""

    request_id: str = Field(description="Id of the ftqc circuit job request.")
    status: StatusEnum = Field(description="Current status of circuit job.")


class FTQCSolutionResponse(FTQCResponse):
    """FTQC solution response model."""

    parity_check_time: Optional[ParityCheckTime]
    fit: Optional[Fit]
    emulator_plot_path: Optional[str]
    message: Optional[str] = Field(description="Error message when status is failed.")
