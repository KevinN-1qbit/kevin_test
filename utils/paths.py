""" Utils module for manipulating paths within this package """

import os.path as osp
import re


def rel_path_to_abs_path(rel_path: str) -> str:
    full_file_path = osp.realpath(__file__)
    last_known_bit_of_path = "utils/paths.py"
    new_path, n_subs = re.subn(
        rf"/{last_known_bit_of_path}.*",
        rf"/{rel_path}",
        full_file_path,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert n_subs == 1
    return new_path


def get_abs_path_to_input_file(filename: str) -> str:
    return rel_path_to_abs_path(f"data/input/{filename}")
