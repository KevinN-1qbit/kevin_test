""" Tests of module tile_layout.py """

import pytest
from scheduler.steiner_tree_heuristic import read_layout_from_pkl

from layout_processor import tile_layout, adjacency_graph


@pytest.fixture
def adj_graph_corner_layout():
    layout = read_layout_from_pkl(
        "sc_big_more_corner_qubits.pkl", factories_num={"x": 1, "y": 1}
    )

    g = layout.get_graph_for_mip()
    adj_graph = adjacency_graph.AdjacencyGraph()
    adj_graph.process_graph(g)
    return adj_graph


# noinspection PyTypeChecker
def test_process_graph(adj_graph_corner_layout) -> None:
    adj_expected = {
        ("q0", "X"): {0: {"weight": 100000}},
        ("q0", "Z"): {4: {"weight": 100000}},
        ("q1", "X"): {0: {"weight": 100000}},
        ("q1", "Z"): {6: {"weight": 100000}},
        ("q2", "X"): {1: {"weight": 100000}},
        ("q2", "Z"): {7: {"weight": 100000}},
        ("q3", "X"): {2: {"weight": 100000}},
        ("q3", "Z"): {10: {"weight": 100000}},
        ("q4", "X"): {3: {"weight": 100000}},
        ("q4", "Z"): {11: {"weight": 100000}},
        ("q5", "X"): {3: {"weight": 100000}},
        ("q5", "Z"): {13: {"weight": 100000}},
        ("q6", "Z"): {4: {"weight": 100000}},
        ("q6", "X"): {14: {"weight": 100000}},
        ("q7", "Z"): {6: {"weight": 100000}},
        ("q7", "X"): {14: {"weight": 100000}},
        ("q8", "Z"): {11: {"weight": 100000}},
        ("q8", "X"): {15: {"weight": 100000}},
        ("q9", "Z"): {13: {"weight": 100000}},
        ("q9", "X"): {15: {"weight": 100000}},
        ("q10", "X"): {16: {"weight": 100000}},
        ("q10", "Z"): {18: {"weight": 100000}},
        ("q11", "X"): {17: {"weight": 100000}},
        ("q11", "Z"): {21: {"weight": 100000}},
        ("q12", "Z"): {22: {"weight": 100000}},
        ("q12", "X"): {26: {"weight": 100000}},
        ("q13", "Z"): {25: {"weight": 100000}},
        ("q13", "X"): {27: {"weight": 100000}},
        ("q14", "X"): {28: {"weight": 100000}},
        ("q14", "Z"): {30: {"weight": 100000}},
        ("q15", "X"): {28: {"weight": 100000}},
        ("q15", "Z"): {32: {"weight": 100000}},
        ("q16", "X"): {29: {"weight": 100000}},
        ("q16", "Z"): {37: {"weight": 100000}},
        ("q17", "X"): {29: {"weight": 100000}},
        ("q17", "Z"): {39: {"weight": 100000}},
        ("q18", "Z"): {30: {"weight": 100000}},
        ("q18", "X"): {40: {"weight": 100000}},
        ("q19", "Z"): {32: {"weight": 100000}},
        ("q19", "X"): {40: {"weight": 100000}},
        ("q20", "Z"): {33: {"weight": 100000}},
        ("q20", "X"): {41: {"weight": 100000}},
        ("q21", "Z"): {36: {"weight": 100000}},
        ("q21", "X"): {42: {"weight": 100000}},
        ("q22", "Z"): {37: {"weight": 100000}},
        ("q22", "X"): {43: {"weight": 100000}},
        ("q23", "Z"): {39: {"weight": 100000}},
        ("q23", "X"): {43: {"weight": 100000}},
        ("m0", "Z"): {10: {"weight": 100000}},
        ("m1", "Z"): {16: {"weight": 100000}},
        ("m2", "Z"): {27: {"weight": 100000}},
        ("m3", "Z"): {33: {"weight": 100000}},
        ("r0", "Z"): {7: {"weight": 100000}},
        ("r0", "X"): {8: {"weight": 100000}},
        ("r1", "X"): {20: {"weight": 100000}},
        ("r1", "Z"): {17: {"weight": 100000}},
        ("r2", "X"): {23: {"weight": 100000}},
        ("r2", "Z"): {26: {"weight": 100000}},
        ("r3", "X"): {35: {"weight": 100000}},
        ("r3", "Z"): {36: {"weight": 100000}},
        ("s0", "Z"): {9: {"weight": 100000}},
        ("s1", "X"): {19: {"weight": 100000}},
        ("s2", "X"): {24: {"weight": 100000}},
        ("s3", "Z"): {34: {"weight": 100000}},
        0: {
            ("q0", "X"): {"weight": 100000},
            ("q1", "X"): {"weight": 100000},
            5: {"weight": 1},
        },
        1: {("q2", "X"): {"weight": 100000}, 2: {"weight": 1}, 8: {"weight": 1}},
        2: {1: {"weight": 1}, ("q3", "X"): {"weight": 100000}, 9: {"weight": 1}},
        3: {
            ("q4", "X"): {"weight": 100000},
            ("q5", "X"): {"weight": 100000},
            12: {"weight": 1},
        },
        4: {
            ("q0", "Z"): {"weight": 100000},
            ("q6", "Z"): {"weight": 100000},
            5: {"weight": 1},
        },
        5: {0: {"weight": 1}, 4: {"weight": 1}, 6: {"weight": 1}, 14: {"weight": 1}},
        6: {
            ("q1", "Z"): {"weight": 100000},
            5: {"weight": 1},
            7: {"weight": 1},
            ("q7", "Z"): {"weight": 100000},
        },
        7: {
            ("q2", "Z"): {"weight": 100000},
            6: {"weight": 1},
            8: {"weight": 1},
            ("r0", "Z"): {"weight": 100000},
        },
        8: {
            1: {"weight": 1},
            7: {"weight": 1},
            9: {"weight": 1},
            ("r0", "X"): {"weight": 100000},
        },
        9: {
            2: {"weight": 1},
            8: {"weight": 1},
            10: {"weight": 1},
            ("s0", "Z"): {"weight": 100000},
        },
        10: {
            ("q3", "Z"): {"weight": 100000},
            9: {"weight": 1},
            11: {"weight": 1},
            ("m0", "Z"): {"weight": 100000},
        },
        11: {
            ("q4", "Z"): {"weight": 100000},
            10: {"weight": 1},
            12: {"weight": 1},
            ("q8", "Z"): {"weight": 100000},
        },
        12: {3: {"weight": 1}, 11: {"weight": 1}, 13: {"weight": 1}, 15: {"weight": 1}},
        13: {
            ("q5", "Z"): {"weight": 100000},
            12: {"weight": 1},
            ("q9", "Z"): {"weight": 100000},
        },
        14: {
            5: {"weight": 1},
            ("q6", "X"): {"weight": 100000},
            ("q7", "X"): {"weight": 100000},
            16: {"weight": 1},
        },
        15: {
            12: {"weight": 1},
            ("q8", "X"): {"weight": 100000},
            ("q9", "X"): {"weight": 100000},
            17: {"weight": 1},
        },
        16: {
            14: {"weight": 1},
            ("q10", "X"): {"weight": 100000},
            19: {"weight": 1},
            ("m1", "Z"): {"weight": 100000},
        },
        17: {
            15: {"weight": 1},
            ("r1", "Z"): {"weight": 100000},
            20: {"weight": 1},
            ("q11", "X"): {"weight": 100000},
        },
        18: {("q10", "Z"): {"weight": 100000}, 19: {"weight": 1}, 22: {"weight": 1}},
        19: {
            16: {"weight": 1},
            18: {"weight": 1},
            ("s1", "X"): {"weight": 100000},
            23: {"weight": 1},
        },
        20: {
            17: {"weight": 1},
            24: {"weight": 1},
            ("r1", "X"): {"weight": 100000},
            21: {"weight": 1},
        },
        21: {20: {"weight": 1}, 25: {"weight": 1}, ("q11", "Z"): {"weight": 100000}},
        22: {18: {"weight": 1}, ("q12", "Z"): {"weight": 100000}, 23: {"weight": 1}},
        23: {
            19: {"weight": 1},
            22: {"weight": 1},
            26: {"weight": 1},
            ("r2", "X"): {"weight": 100000},
        },
        24: {
            20: {"weight": 1},
            25: {"weight": 1},
            ("s2", "X"): {"weight": 100000},
            27: {"weight": 1},
        },
        25: {21: {"weight": 1}, 24: {"weight": 1}, ("q13", "Z"): {"weight": 100000}},
        26: {
            23: {"weight": 1},
            ("q12", "X"): {"weight": 100000},
            28: {"weight": 1},
            ("r2", "Z"): {"weight": 100000},
        },
        27: {
            24: {"weight": 1},
            ("q13", "X"): {"weight": 100000},
            29: {"weight": 1},
            ("m2", "Z"): {"weight": 100000},
        },
        28: {
            26: {"weight": 1},
            ("q14", "X"): {"weight": 100000},
            ("q15", "X"): {"weight": 100000},
            31: {"weight": 1},
        },
        29: {
            27: {"weight": 1},
            ("q16", "X"): {"weight": 100000},
            ("q17", "X"): {"weight": 100000},
            38: {"weight": 1},
        },
        30: {
            ("q18", "Z"): {"weight": 100000},
            ("q14", "Z"): {"weight": 100000},
            31: {"weight": 1},
        },
        31: {
            28: {"weight": 1},
            30: {"weight": 1},
            32: {"weight": 1},
            40: {"weight": 1},
        },
        32: {
            31: {"weight": 1},
            33: {"weight": 1},
            ("q19", "Z"): {"weight": 100000},
            ("q15", "Z"): {"weight": 100000},
        },
        33: {
            32: {"weight": 1},
            34: {"weight": 1},
            ("q20", "Z"): {"weight": 100000},
            ("m3", "Z"): {"weight": 100000},
        },
        34: {
            33: {"weight": 1},
            ("s3", "Z"): {"weight": 100000},
            41: {"weight": 1},
            35: {"weight": 1},
        },
        35: {
            34: {"weight": 1},
            42: {"weight": 1},
            36: {"weight": 1},
            ("r3", "X"): {"weight": 100000},
        },
        36: {
            35: {"weight": 1},
            ("q21", "Z"): {"weight": 100000},
            37: {"weight": 1},
            ("r3", "Z"): {"weight": 100000},
        },
        37: {
            36: {"weight": 1},
            ("q16", "Z"): {"weight": 100000},
            38: {"weight": 1},
            ("q22", "Z"): {"weight": 100000},
        },
        38: {
            29: {"weight": 1},
            37: {"weight": 1},
            43: {"weight": 1},
            39: {"weight": 1},
        },
        39: {
            38: {"weight": 1},
            ("q23", "Z"): {"weight": 100000},
            ("q17", "Z"): {"weight": 100000},
        },
        40: {
            31: {"weight": 1},
            ("q18", "X"): {"weight": 100000},
            ("q19", "X"): {"weight": 100000},
        },
        41: {34: {"weight": 1}, ("q20", "X"): {"weight": 100000}, 42: {"weight": 1}},
        42: {35: {"weight": 1}, 41: {"weight": 1}, ("q21", "X"): {"weight": 100000}},
        43: {
            38: {"weight": 1},
            ("q22", "X"): {"weight": 100000},
            ("q23", "X"): {"weight": 100000},
        },
    }
    assert adj_expected == dict(adj_graph_corner_layout.nx_graph.adj)
    print()


@pytest.mark.parametrize(
    "magic_states_ready_before, "
    "magic_states_to_remove, "
    "magic_states_ready_after, ",
    [
        (
            {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")},
            [("m1", "Z"), ("m2", "Z")],
            {("m0", "Z"), ("m3", "Z")},
        ),
        (
            {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")},
            [("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")],
            set(),
        ),
        (
            {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")},
            [("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z"), ("m4", "X")],
            set(),
        ),
    ],
)
def test_remove_nodes_from_status(
    adj_graph_corner_layout,
    magic_states_ready_before,
    magic_states_to_remove,
    magic_states_ready_after,
):
    assert (
        adj_graph_corner_layout.nodes_by_status[adjacency_graph.ComponentType.MAGIC][
            adjacency_graph.MagicStateStatus.READY
        ]
        == magic_states_ready_before
    )

    adj_graph_corner_layout.remove_nodes_from_status(magic_states_to_remove)

    assert (
        adj_graph_corner_layout.nodes_by_status[adjacency_graph.ComponentType.MAGIC][
            adjacency_graph.MagicStateStatus.READY
        ]
        == magic_states_ready_after
    )


def test_get_bus_zs(adj_graph_corner_layout):
    bus_adj_to_zero_states = adj_graph_corner_layout.get_bus_zs()
    bus_adj_to_zero_states_expected = {
        (7, 8): "r0",
        (17, 20): "r1",
        (23, 26): "r2",
        (35, 36): "r3",
    }
    assert bus_adj_to_zero_states == bus_adj_to_zero_states_expected
    print()


@pytest.mark.parametrize(
    "nodes, "
    "node_types, "
    "nb_ticks, "
    "node_status_before_set_node_ticks, "
    "node_status_after_set_node_ticks, ",
    [
        (
            {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")},
            adjacency_graph.ComponentType.MAGIC,
            16,
            adjacency_graph.MagicStateStatus.READY,
            adjacency_graph.MagicStateStatus.REPLENISHING,
        ),
        (
            {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")},
            adjacency_graph.ComponentType.MAGIC,
            -1,
            adjacency_graph.MagicStateStatus.READY,
            adjacency_graph.MagicStateStatus.DEPLETED,
        ),
    ],
)
def test_set_node_ticks(
    adj_graph_corner_layout,
    nodes,
    node_types,
    nb_ticks,
    node_status_before_set_node_ticks,
    node_status_after_set_node_ticks,
):
    assert (
        adj_graph_corner_layout.nodes_by_status[node_types][
            node_status_before_set_node_ticks
        ]
        == nodes
    )

    assert (
        adj_graph_corner_layout.nodes_by_status[node_types][
            node_status_after_set_node_ticks
        ]
        == set()
    )

    adj_graph_corner_layout.set_nodes_ticks(nodes, nb_ticks)
    assert (
        adj_graph_corner_layout.nodes_by_status[adjacency_graph.ComponentType.MAGIC][
            node_status_after_set_node_ticks
        ]
        == nodes
    )

    assert (
        adj_graph_corner_layout.nodes_by_status[node_types][
            node_status_before_set_node_ticks
        ]
        == set()
    )


def test_store_magic_states(adj_graph_corner_layout):
    ms_ready_before = {("m0", "Z"), ("m1", "Z"), ("m2", "Z"), ("m3", "Z")}
    assert (
        adj_graph_corner_layout.nodes_by_status[adjacency_graph.ComponentType.MAGIC][
            adjacency_graph.MagicStateStatus.READY
        ]
        == ms_ready_before
    )

    adj_graph_corner_layout.store_magic_states("match")
