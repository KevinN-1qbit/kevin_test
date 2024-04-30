""" tests lys.py.  Mostly just smoke tests. """

from typing import Literal, Any

from pytest import mark

import src.lys as m
from utils import paths

_Language = Literal["qasm", "projectq"]


def get_expected_sys_argv(input_file_path: str, language: _Language) -> list[str]:
    return f"{__file__} -input {input_file_path} -language {language}".split()


def get_expected_cfg_dict_from_parsing_sys_argv(
    input_file_path: str, language: _Language
) -> dict[str, Any]:
    cfg = {
        "input_file": input_file_path,
        "language": language,
        "remove_non_t": True,
        "recompile_cpp": False,
        "epsilon": 1e-10,
    }
    return cfg


_input_files = [
    ("test_circuits/qasm_test_10_lines.qasm", "qasm"),
    ("test_circuits/projectq_measure_anc_short.txt", "projectq"),
    ("test_circuits/projectq_measure_anc_short_with_rz.txt", "projectq"),
]


@mark.tens_seconds
@mark.parametrize("input_file, language", _input_files)
def test_main(input_file: str, language: _Language, monkeypatch) -> None:
    input_file_path = paths.get_abs_path_to_input_file(input_file)

    expected_cfg = get_expected_cfg_dict_from_parsing_sys_argv(
        input_file_path, language
    )
    expected_sys_argv = get_expected_sys_argv(input_file_path, language)

    monkeypatch.setattr("sys.argv", expected_sys_argv)

    assert m.get_cfg() == expected_cfg

    # Smoke test
    m.main(m.get_cfg())

    print(
        f"\n\ntest_main passed, "
        f"\n\tlang:{language}, "
        f"\n\tinput_file:{input_file}\n\n\n"
    )


# if __name__ == "__main__": test_main("test_circuits/qasm_test_10_lines.qasm", "qasm")
# if __name__ == "__main__": test_main("test_circuits/projectq_measure_anc_short.txt", "projectq")
# if __name__ == "__main__": test_main("test_circuits/projectq_measure_anc_short_with_rz.txt", "projectq")


@mark.tens_seconds
@mark.parametrize("input_file, language", _input_files)
def test_get_compiled_circuit(input_file: str, language: _Language) -> None:
    """Tests "get_compiled_circuit" method without any subprocesses"""
    input_file_path = paths.get_abs_path_to_input_file(input_file)
    expected_cfg = get_expected_cfg_dict_from_parsing_sys_argv(
        input_file_path, language
    )

    chosen_parser, circuit_input = m.get_parser_and_circuit_input(expected_cfg)

    # Smoke test
    m.get_compiled_circuit(chosen_parser, circuit_input, expected_cfg)

    print(
        f"\n\ntest_get_compiled_circuit passed, "
        f"\n\tlang:{language}, "
        f"\n\tinput_file:{input_file}\n\n\n"
    )


# if __name__ == "__main__": test_get_compiled_circuit("test_circuits/qasm_test_10_lines.qasm", "qasm")
# if __name__ == "__main__": test_get_compiled_circuit("test_circuits/projectq_measure_anc_short.txt", "projectq")
# if __name__ == "__main__": test_get_compiled_circuit("test_circuits/projectq_measure_anc_short_with_rz.txt", "projectq")
