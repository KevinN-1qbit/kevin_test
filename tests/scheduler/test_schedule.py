import pytest
from src.scheduler.caching.data_qubits_caching import SPCaching
from src.scheduler.circuit_and_rotation.generate_rotation import parse_rotations
from src.scheduler.dependency_graph import DependencyGraphTrivialCommute
from src.scheduler.steiner_tree_heuristic import (
    AssignPolicy,
    solve_qubits_assignment,
    solve_rotations_scheduling,
    read_layout_from_pkl,
)
from src.layout_processor.adjacency_graph import AdjacencyGraph
from src.layout_processor.magic_state_factory import MagicStateFactory
from src.helpers import paths


def prep_circuit(circuit_name, policy: AssignPolicy = AssignPolicy.RANDOM_CORNER):
    layout = read_layout_from_pkl(
        "sc_big_with_storage_3.pkl", factories_num={"x": 2, "y": 2}
    )

    adj_graph = AdjacencyGraph()
    adj_graph.process_graph(layout.get_graph_for_mip())

    sp_caching = SPCaching()
    sp_caching.reset_spp_caching()

    ms_factory = MagicStateFactory(
        tick_replenish=17,
        num_factory=2 * 2,
        ms_per_factory=4,
        col=2,
        row=2,
        graph=adj_graph,
    )

    circuits_dir = paths.get_benchmark_circuits_dir()
    circuit_path = circuits_dir + "/" + circuit_name
    circuit = parse_rotations(circuit_path, True)

    solve_qubits_assignment(circuit, adj_graph, policy=policy)
    circuit.add_turn_qubits(adj_graph.qubit_angle)

    return sp_caching, circuit, adj_graph, ms_factory


@pytest.mark.parametrize(
    "circuit_name",
    [
        "Compiled_sparseIsing_num-qubits-10_num-interactions-4_seed-2022_20220323-17-51.txt",
        "Compiled_k_sat_QASM_single_iterate(6-num_clauses,4-num_variables)_20220304-11-34.txt",
        "Compiled_trotterAtAIsingTr_qb10_sd0_20220323-21-57.txt",
        "Compiled_trotterChain_qb10_bd3_sd1_20220306-06-51.txt",
        # big ones, comment out to save time
        "Compiled_trotterChain_qb50_bd3_sd1_20220306-09-26.txt",
        "Compiled_sparseIsing_num-qubits-50_num-interactions-8_seed-2022_20220323-21-50.txt",
        "Compiled_trotterAtAIsingTr_qb50_sd0_20220326-18-36.txt",
        "Compiled_k_sat_QASM_single_iterate(10-num_clauses,6-num_variables)_20220305-13-32.txt",
    ],
)
def test_schedule_is_ordered(circuit_name):
    sp_caching, circuit, adj_graph_full, magic_state_factory = prep_circuit(
        circuit_name
    )
    dep_graph = DependencyGraphTrivialCommute(circuit)

    dep_rev, dep_for, deps = dep_graph.get_dependency_graph()

    rot_assigned, ticks, _ = solve_rotations_scheduling(
        sp_caching, circuit, adj_graph_full, magic_state_factory
    )

    rotations_seen = set()

    for tick in range(ticks):
        if tick not in rot_assigned:
            continue

        rotations_this_tick = set()

        rotations = rot_assigned[tick]

        for rotation, _, _ in rotations:
            blockers_for_this_rotation = deps[rotation.ind]

            for blocker in blockers_for_this_rotation:
                assert blocker in rotations_seen

            rotations_this_tick.add(rotation.ind)

        rotations_seen |= rotations_this_tick


@pytest.mark.parametrize(
    "circuit_name",
    [
        "Compiled_sparseIsing_num-qubits-10_num-interactions-4_seed-2022_20220323-17-51.txt",
        "Compiled_k_sat_QASM_single_iterate(6-num_clauses,4-num_variables)_20220304-11-34.txt",
        "Compiled_trotterAtAIsingTr_qb10_sd0_20220323-21-57.txt",
        "Compiled_trotterChain_qb10_bd3_sd1_20220306-06-51.txt",
    ],
)
def test_schedule_is_ordered_random(circuit_name):
    sp_caching, circuit, adj_graph_full, magic_state_factory = prep_circuit(
        circuit_name, AssignPolicy.RANDOM
    )
    dep_graph = DependencyGraphTrivialCommute(circuit)

    dep_rev, dep_for, deps = dep_graph.get_dependency_graph()

    rot_assigned, ticks, _ = solve_rotations_scheduling(
        sp_caching, circuit, adj_graph_full, magic_state_factory
    )

    rotations_seen = set()

    for tick in range(ticks):
        if tick not in rot_assigned:
            continue

        rotations_this_tick = set()

        rotations = rot_assigned[tick]

        for rotation, _, _ in rotations:
            blockers_for_this_rotation = deps[rotation.ind]

            for blocker in blockers_for_this_rotation:
                assert blocker in rotations_seen

            rotations_this_tick.add(rotation.ind)

        rotations_seen |= rotations_this_tick


@pytest.mark.parametrize(
    "circuit_name",
    [
        "Compiled_sparseIsing_num-qubits-10_num-interactions-4_seed-2022_20220323-17-51.txt",
        "Compiled_k_sat_QASM_single_iterate(6-num_clauses,4-num_variables)_20220304-11-34.txt",
        "Compiled_trotterAtAIsingTr_qb10_sd0_20220323-21-57.txt",
        "Compiled_trotterChain_qb10_bd3_sd1_20220306-06-51.txt",
        # big ones, comment out to save time
        "Compiled_trotterChain_qb50_bd3_sd1_20220306-09-26.txt",
        "Compiled_sparseIsing_num-qubits-50_num-interactions-8_seed-2022_20220323-21-50.txt",
        "Compiled_trotterAtAIsingTr_qb50_sd0_20220326-18-36.txt",
        "Compiled_k_sat_QASM_single_iterate(10-num_clauses,6-num_variables)_20220305-13-32.txt",
    ],
)
def test_schedule_does_not_overlap(circuit_name):
    sp_caching, circuit, adj_graph_full, magic_state_factory = prep_circuit(
        circuit_name
    )
    dep_graph = DependencyGraphTrivialCommute(circuit)

    dep_rev, dep_for, deps = dep_graph.get_dependency_graph()

    rot_assigned, ticks, _ = solve_rotations_scheduling(
        sp_caching, circuit, adj_graph_full, magic_state_factory
    )

    for tick in range(ticks):
        if tick not in rot_assigned:
            continue

        rotations = rot_assigned[tick]

        nodes = set()

        for _, graph, _ in rotations:
            for node in graph.nodes:
                assert node not in nodes
                nodes.add(node)
