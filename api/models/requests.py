from pydantic import BaseModel, Field
from typing import Optional


class TranspilerRequest(BaseModel):
    """Transpiler Request Object."""

    file_path: str = Field(description="Path to circuit file")
    language: str = Field(description="Language of circuit file", default="qasm")
    epsilon: Optional[float] = Field(
        description="Set the value of decomposition precision. Positive values only.",
        default=1e-10,
    )
    timeout: Optional[int] = Field(
        description="Timeout of transpilation process time in seconds",
        default=0,
    )
    bypass_optimization: Optional[bool] = Field(
        description="Flag to determine whether or not to bypass optimization and use basis conversion only",
        default=False
    )


class TranspilerModel(TranspilerRequest):
    """Transpiler Model Object."""

    request_id: str = Field(description="Id of the transpiler circuit job request.")
