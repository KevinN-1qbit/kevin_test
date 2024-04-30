from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class StatusEnum(str, Enum):
    waiting = "waiting"
    done = "done"
    executing = "executing"
    failed = "failed"


class HealthCheckResponse(BaseModel):
    """Healthcheck response model."""

    status: str = Field(description="The health of this server.")
    application: str = Field(
        description="The name of the application running on this server."
    )


class TranspilerResponse(BaseModel):
    """Transpiler response model."""

    request_id: str = Field(description="Id of the transpiler circuit job request.")
    status: StatusEnum = Field(description="Current status of circuit job.")


class TranspilerSolutionResponse(TranspilerResponse):
    """Transpiler solution response model."""

    transpiled_circuit_path: Optional[str] = Field(
        description="Path of the transpiled circuit."
    )
    circuit_name: Optional[str] = Field(description="Name of the circuit.")
    instruction_set: Optional[str] = Field(description="Instruction set of circuit.")
    num_data_qubits_required: Optional[int] = Field(
        description="Number of data qubits required."
    )
    total_num_operations: Optional[int] = Field(
        description="Total number of operations."
    )
    num_non_clifford_operations: Optional[int] = Field(
        description="Number of non clifford operations."
    )
    num_clifford_operations: Optional[int] = Field(
        description="Number of clifford operations."
    )
    num_logical_measurements: Optional[int] = Field(
        description="Number of logical measurements."
    )
    elapsed_time: Optional[float] = Field(description="The elapsed time of the tool in seconds")
    bypass_optimization: Optional[bool] = Field(description="Flag to determine whether or not to bypass optimization and use basis conversion only")
    message: Optional[str] = Field(description="Error message when status is failed.")
