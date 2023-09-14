from pydantic import BaseModel, Field
from typing import Optional, Dict


class ValueUnit(BaseModel):
    value: float
    unit: str


class QubitTechnologyParameters(BaseModel):
    qubit_measurement_time: ValueUnit
    qubit_preparation_time: ValueUnit
    qubit_reset_time: ValueUnit
    hadamard_gate_time: ValueUnit
    cnot_gate_time: ValueUnit
    T1_relaxation_time: ValueUnit
    T2_dephasing_time: ValueUnit
    measurement_fidelity: ValueUnit
    preparation_fidelity: ValueUnit
    reset_fidelity: ValueUnit
    hadamard_gate_fidelity: ValueUnit
    cnot_gate_fidelity: ValueUnit
    t_gate_fidelity: ValueUnit


class QubitTechnology(BaseModel):
    specifier: str
    parameters: QubitTechnologyParameters


class NoiseModel(BaseModel):
    specifier: str


class Decoder(BaseModel):
    specifier: str


class Protocol(BaseModel):
    specifier: str
    number_of_rounds: int


class Code(BaseModel):
    specifier: str


class FTQCRequest(BaseModel):
    """FTQC Request Object."""

    number_of_cores: int
    code: Code
    protocol: Protocol
    decoder: Decoder
    qubit_technology: QubitTechnology
    noise_model: NoiseModel


class FTQCModel(FTQCRequest):
    """FTQC Model Object."""

    request_id: str = Field(description="Id of the ftqc circuit job request.")
