import os.path as osp


def get_repo_root_dir():
    """
    Returns the root dir of the hansa-compiler project
    """
    file_dir = osp.dirname(__file__)
    while file_dir.split("/")[-1] != "hansa-compiler":
        file_dir = osp.dirname(file_dir)
    return file_dir


def get_tests_dir():
    return osp.join(get_repo_root_dir(), "tests")


def get_cache_dir():
    return osp.join(get_repo_root_dir(), "cache")


def get_txt_circuits_dir():
    return osp.join(get_repo_root_dir(), "tests/data/circuits")


def get_benchmark_circuits_dir():
    return osp.join(get_repo_root_dir(), "tests/data/circuits_benchmark")


def get_pickled_circuits_dir():
    return osp.join(get_txt_circuits_dir(), "preprocessed_rotations")


def get_output_dir():
    return osp.join(get_repo_root_dir(), "data/outputs")


def get_layout_dir():
    return osp.join(get_repo_root_dir(), "data/inputs/layout_files")
