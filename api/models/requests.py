from pydantic import BaseModel, Field


class SKRequest(BaseModel):
    """SK Request Object."""

    circuit_path: str = Field(description="Path to circuit file")
    error_budget: float = Field(description="Allowable error")


class SKModel(SKRequest):
    """SK Model Object."""

    request_id: str = Field(description="Id of the sk job request.")
