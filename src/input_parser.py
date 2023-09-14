from enum import Enum


class Code(Enum):
    ROTATED_SURFACE_CODE = "rotated_surface_code"


class Protocol(Enum):
    MEMORY_Z = "memory_z"


class Decoder(Enum):
    MWPM = "minimum_weight_perfect_matching"


class QubitTechnology(Enum):
    TRANSMON = "transmon"


class NoiseModel(Enum):
    IDLING = "circuit_noise_with_idling"


def validate_input_data(args):
    if args["code"]["specifier"] not in Code._value2member_map_:
        raise ValueError(f"Invalid code: {args['code']['specifier']}")

    if args["protocol"]["specifier"] not in Protocol._value2member_map_:
        raise ValueError(f"Invalid instruction set: {args['protocol']['specifier']}")

    if args["protocol"]["number_of_rounds"] > 1:
        raise ValueError(
            f"Invalid number of rounds: {args['protocol']['parameters']['number_of_rounds']}"
        )

    if args["decoder"]["specifier"] not in Decoder._value2member_map_:
        raise ValueError(f"Invalid decoder: {args['decoder']['specifier']}")

    if args["qubit_technology"]["specifier"] not in QubitTechnology._value2member_map_:
        raise ValueError(
            f"Invalid qubit technology: {args['qubit_technology']['specifier']}"
        )

    if args["noise_model"]["specifier"] not in NoiseModel._value2member_map_:
        raise ValueError(f"Invalid noise model: {args['noise_model']['specifier']}")


def get_protocol_specifier(code_specifier, protocol_specifier) -> str:
    if code_specifier == Code.ROTATED_SURFACE_CODE.value:
        if protocol_specifier == Protocol.MEMORY_Z.value:
            return "surface_code:rotated_memory_z"


def get_decoder_specifier(decoder_specifier) -> list[str]:
    if decoder_specifier == Decoder.MWPM.value:
        return ["pymatching"]
