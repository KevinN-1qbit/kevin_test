from __future__ import annotations

import csv
import json
import pickle
import random
import time
from time import localtime, strftime
from typing import Union

import networkx as nx
import scheduler.data_qubit_assignment as qa
import scheduler.dependency_graph as dp
from scheduler.caching import shortest_path_caching, steiner_tree_caching
from scheduler.circuit_and_rotation import circuit
from scheduler.circuit_and_rotation.circuit import MEASUREMENT, PI4, PI8, TURN
from scheduler.circuit_and_rotation.generate_rotation import (
    convert_Y_operators,
    parse_rotations,
)
from layout_processor import magic_state_factory as msf
from layout_processor import patches, tile_layout
from scheduler.surface_code_layout import tiles
from layout_processor.adjacency_graph import (
    AdjacencyGraph,
    AdjGraphNode,
    ComponentType,
    MagicStateStatus,
    StorageStatus,
    TileName,
    ZeroStateStatus,
)
from helpers import paths


# ! Move to a "solution.py" file?
def write_scheduler_result_to_pkl(rotation_assignment_results, result_file_name):
    """(add summary)"""
    tree_nodes_all_assignment = []
    for rotation_assigned_per_tick in rotation_assignment_results.values():
        tree_nodes_per_tick = []
        for rotation_assigned in rotation_assigned_per_tick:
            _, tree, _ = rotation_assigned
            nodes_in_tree = set()
            for nodes in tree:
                nodes_in_tree.add(nodes)
            tree_nodes_per_tick.append(nodes_in_tree)
        tree_nodes_all_assignment.append(tree_nodes_per_tick)
    result_file_name = "./data/outputs/scheduling/" + result_file_name
    # Open a file and use dump()
    with open(result_file_name, "wb") as file:
        # A new file will be created
        pickle.dump(tree_nodes_all_assignment, file)


#! what is this doing? needs description
class HansaEncode(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, tiles.Tile):
            return {
                "!type": "Tile",
                "x": obj.x,
                "y": obj.y,
            }
        elif isinstance(obj, frozenset):
            return {
                "!type": "frozenset",
                "values": list(obj),
            }
        return json.JSONEncoder.default(self, obj)


# ! Move to a "solution.py" file?
def write_to_csv(circuit_name, num_qubits, num_gates, tick, runtime, pi8_len):
    """Write results to an external csv file"""

    output_name = (
        "scheduler_benchmark_large_layout_"
        + strftime("%Y-%m-%d-%H-%M", localtime())
        + ".csv"
    )

    with open(output_name, "w") as output_file:
        writer = csv.writer(output_file)

        title_row = [
            "Circuit Name",
            "Num of Qubits",
            "Num of Gates",
            "Num of PI8",
            "Ticks",
            "Time",
        ]

        writer.writerow(title_row)

        for file_name, qubits, depth_gate, tick_count, time_count, pi8 in zip(
            circuit_name, num_qubits, num_gates, tick, runtime, pi8_len
        ):
            writer.writerow(
                [file_name, qubits, depth_gate, pi8, tick_count, time_count]
            )


#! move to somewhere?
def swap_xz(node: tuple) -> tuple:
    """Swap a node's angle"""
    if node[1] == "X":
        return node[0], "Z"
    if node[1] == "Z":
        return node[0], "X"
    raise Exception("Invalid node angle")


#! move to somewhere?
def is_steiner_tree_feasible(tree: nx.Graph, terminals: list) -> bool:
    """Check Steiner tree feasibility for a circuit. Conditions:
    1) ST is infeasible if at least one terminal node is not a leaf

    Args:
        tree (nx.Graph): Steiner tree to be checked
        terminals (list): all terminal nodes

    Returns:
        bool: is feasible?
    """

    # are all terminal nodes leaves?
    for node in terminals:
        if tree.degree[node] > 1:
            return False
    return True


#! move to "solve_rotations_scheduling.py" file?
def print_strees_this_tick(
    rot_assigned_this_tick: list,
    rot_count: int,
    rot_total: int,
    tick: int,
    print_interval=1,
) -> int:
    """Print the Steiner trees generated in this tick

    Args:
        rot_assigned_this_tick (list): rotations assigned this tick
        rot_count (int): total number of rotations assigned so far
        rot_total (int): total number of rotations to be assigned
        tick (int): current tick number
        print_interval (int): interval to print rotations assigned

    Returns:
        int: rot_count updated
    """

    for rot, tree, _ in rot_assigned_this_tick:
        op_type = None
        if rot.operation_type == PI8:
            op_type = "PI8"
        elif rot.operation_type == PI4:
            op_type = "PI4"
        elif rot.operation_type == MEASUREMENT:
            op_type = "Measure"
        elif rot.operation_type == TURN:
            op_type = "Turn"

        # print
        if rot_count % print_interval == 0:
            print("tick", tick - 1, "...", end=" ")
            print(f"Rotation {rot_count:>4} / {rot_total:>4} | {op_type:>7} | ", end="")
            print("Tiles used:", tree.nodes())
        rot_count += 1
    return rot_count


#! move to "solve_rotations_packing.py"?
def candidate_rotations_precheck(
    candidate_rotation: list[bool],
    commutable_rotations: list[circuit.Rotation],
    ms_available: set[tuple[str, str]],
    components_unavailable: set[Union[str, int]],
    trees_and_terminals: list[tuple[Union[nx.Graph, None], Union[AdjGraphNode, None]]],
    adj_graph_full: AdjacencyGraph,
    fails_count: dict[str, int],
    random_generator: random.Random,
):
    # remove beforehand all rotations that are not required to solve the Steiner tree problem
    for idx, rotation in enumerate(commutable_rotations):
        # get qubits required in this rotation
        qubits_required = {n[0] for n in rotation.rotation_active_edges}

        # PRE-CHECK 1: if PI/8 and no magic state available, skip
        if rotation.operation_type == PI8 and len(ms_available) == 0:
            candidate_rotation[idx] = False
            continue

        # PRE-CHECK 2: if MEASURE with a single qubit, tree is a single node graph
        if (
            rotation.operation_type == MEASUREMENT
            and len(rotation.active_qubit) == 1
            and not qubits_required.issubset(components_unavailable)
        ):
            single_node_graph = nx.Graph()
            single_node_graph.add_node(next(iter(rotation.rotation_active_edges)))

            # save single node graph
            trees_and_terminals[idx] = (single_node_graph, None)
            candidate_rotation[idx] = False
            continue

        # PRE-CHECK 3: pack TURN operations
        if rotation.operation_type == TURN:
            # swap qubit angle
            qubit_to_turn = swap_xz(next(iter(rotation.rotation_active_edges)))

            # get bus tiles connected to
            bus_chosen = (
                set(adj_graph_full.nx_graph.neighbors(qubit_to_turn))
                - adj_graph_full.unavailable_nodes
            )
            if len(bus_chosen) > 0:
                # generate graph with a single edge connecting qubit and bus tile chosen
                bus_chosen = random_generator.choice(list(bus_chosen))
                steiner_tree = nx.Graph()
                steiner_tree.add_edge(qubit_to_turn, bus_chosen)

                # set ticks countdown for qubit turned and bus tile used, if required
                adj_graph_full.set_nodes_ticks([qubit_to_turn, bus_chosen], 3)

                # save single edge tree
                trees_and_terminals[idx] = (steiner_tree, bus_chosen)
            else:
                fails_count["Qubit cant rotate"] += 1

            # even if TURN is not possible, skip
            candidate_rotation[idx] = False
            continue

        # PRE-CHECK 4: if qubit terminal is unavailable (still turning), skip
        if len(qubits_required & components_unavailable) > 0:
            candidate_rotation[idx] = False
            continue


#! move to "solve_rotations_packing.py"?
def check_if_zero_state_in_stree(
    curr_adj_graph: AdjacencyGraph,
    steiner_tree: nx.Graph,
    adj_graph_full: AdjacencyGraph,
    zs_available: list[str],
    trees_and_terminals: list[tuple[Union[nx.Graph, None], Union[AdjGraphNode, None]]],
    idx: int,
):
    found = False

    for bus, zs_node in curr_adj_graph.get_bus_zs().items():
        # get bus tiles adjacent to this zero state that are in the tree
        bus_in_tree = list(set(bus) & set(steiner_tree))

        # if more than two bus tiles, then connect this zero state to the tree
        if len(bus_in_tree) >= 2:
            node_chosen = zs_node
            steiner_tree = nx.Graph(steiner_tree)

            # add missing edges
            neighbors = list(curr_adj_graph.nx_graph.neighbors(bus_in_tree[0]))
            for neighbor in neighbors:
                if adj_graph_full.get_node_type(neighbor) == ComponentType.ZERO:
                    steiner_tree.add_edge(bus_in_tree[0], neighbor)
                    steiner_tree.add_edge(bus_in_tree[1], swap_xz(neighbor))
                    break

            # remove zero state from available zero states
            node_x = (node_chosen, "X")
            node_z = (node_chosen, "Z")
            adj_graph_full.set_nodes_ticks([node_x, node_z], 1)
            zs_available.remove(node_chosen)

            # save tree found for this rotation
            trees_and_terminals[idx] = (steiner_tree, (node_x, node_z))
            curr_adj_graph.nx_graph.remove_nodes_from(steiner_tree.nodes())
            curr_adj_graph.remove_nodes_from_status(steiner_tree.nodes())
            found = True
            break

    return found


#! move to "solve_rotations_packing.py"?
def solve_stree_multi_qubit_terminals(
    qubit_terminals: list[TileName],
    curr_adj_graph: AdjacencyGraph,
    strees_cached: dict,
    rotation: circuit.Rotation,
    fails_count: dict[str, int],
    trees_and_terminals: list[tuple[Union[nx.Graph, None], Union[AdjGraphNode, None]]],
    idx: int,
    adj_graph_full: AdjacencyGraph,
    zs_available: list[str],
    shortest_path_cache: shortest_path_caching.SPCaching,
):
    # caching
    key = tuple(qubit_terminals)
    steiner_tree = steiner_tree_caching.search_rotation_cached(
        key, set(curr_adj_graph.nx_graph), strees_cached
    )

    # if caching failed, find steiner tree by solving the STP
    if steiner_tree is None:
        # create reduced graph
        subgraph = curr_adj_graph.remove_non_terminal_nodes_from_adj_graph(
            qubit_terminals, rotation.operation_type
        )

        # solve STP for this subgraph
        steiner_tree = subgraph.solve_stree(qubit_terminals, shortest_path_cache)

        # check if a feasible Steiner tree was found
        if steiner_tree is None:
            fails_count["Steiner tree not found"] += 1
            tree_completed = False
            return tree_completed, steiner_tree

        assert is_steiner_tree_feasible(
            steiner_tree, qubit_terminals
        ), "No feasible Steiner tree found"

        # save the new steiner tree found to the cached trees
        if key in strees_cached:
            strees_cached[key] += [steiner_tree]
        else:
            strees_cached[key] = [steiner_tree]

    # if rotation is a MEASUREMENT, save the cached/solved Steiner tree
    if rotation.operation_type == MEASUREMENT:
        trees_and_terminals[idx] = (steiner_tree, None)
        curr_adj_graph.nx_graph.remove_nodes_from(steiner_tree.nodes())
        curr_adj_graph.remove_nodes_from_status(steiner_tree.nodes())
        tree_completed = True
        return tree_completed, steiner_tree

    # check if there is a magic/zero state already connected to the tree
    if rotation.operation_type == PI4:
        found = check_if_zero_state_in_stree(
            curr_adj_graph,
            steiner_tree,
            adj_graph_full,
            zs_available,
            trees_and_terminals,
            idx,
        )
        if found:
            tree_completed = True
            return tree_completed, steiner_tree
        else:
            tree_completed = False
            return tree_completed, steiner_tree

    # If rotation is PI8, need to find the best magic state,
    # therefore tree is not yet completed
    else:
        tree_completed = False
        return tree_completed, steiner_tree


#! move to "solve_rotations_packing.py"?
def get_magic_resource_state(rotation, ms_available, zs_available, subgraph):
    # get all magic/zero state nodes in the subgraph
    if rotation.operation_type == PI8:
        optional_terminals = ms_available
    else:
        optional_terminals = []
        for zero_state in zs_available:
            zs_x = (zero_state, "X")
            zs_z = (zero_state, "Z")
            assert (
                zs_x in subgraph.nx_graph and zs_z in subgraph.nx_graph
            ), "Zero state not fully in subgraph"
            if zs_x in subgraph.nx_graph and zs_z in subgraph.nx_graph:
                zs_nodes = [zs_x, zs_z]
                optional_terminals.append(tuple(zs_nodes))

    return optional_terminals


#! move to "solve_rotations_packing.py"?
def transform_stree_into_single_node(subgraph, steiner_tree):
    # transform steiner_tree into a single merged node
    subgraph.nx_graph.add_node(steiner_tree)
    # connect steiner_tree node to the subgraph
    for node in steiner_tree:
        for nbr in set(subgraph.nx_graph.neighbors(node)) - set(steiner_tree.nodes()):
            subgraph.nx_graph.add_edge(steiner_tree, nbr)
        subgraph.nx_graph.remove_node(node)
    source = steiner_tree

    return source


#! move to "solve_rotations_packing.py"?
def save_stree_and_remove_terminals(
    trees_and_terminals, idx, steiner_tree, terminals, curr_adj_graph
):
    trees_and_terminals[idx] = (steiner_tree, terminals)
    curr_adj_graph.nx_graph.remove_nodes_from(steiner_tree.nodes())
    curr_adj_graph.remove_nodes_from_status(steiner_tree.nodes())


#! move to "solve_rotations_packing.py"?
def solve_rotations_packing(
    commutable_rotations: list[circuit.Rotation],
    adj_graph_full: AdjacencyGraph,
    shortest_path_cache: shortest_path_caching.SPCaching,
    steiner_trees_cached: dict[tuple[AdjGraphNode], list[nx.Graph]],
    random_generator: random.Random,
    fails_count: dict[str, int],
    magic_state_factory: msf.MagicStateFactory,
    hla_flag: bool = False,
) -> list[tuple[circuit.Rotation, Union[None, nx.Graph], Union[None, AdjGraphNode]]]:
    """Solve the rotations packing sub problem

    Args:
        commutable_rotations : current rotations to be packed
        adj_graph_full: full graph containing adjacency graph and node types in dictionaries
        shortest_path_cache: caching for shortest paths
        steiner_trees_cached: cached steiner trees
        random_generator: a random generator
        fails_count: store fail stats
        magic_state_factory: the magic state factory object
        calling_from_hla_scheduler: a boolean value that indicates whether the function is being called by the HLAScheduler.

    Returns:
        (rotation, trees, terminals):
            - Current commutable rotations
            - Steiner trees generated for each rotation packed
            - Magic state/zero states used for trees
    """

    if magic_state_factory.place_store == "before":
        # store all magic states 'ready' into storages 'empty' BEFORE packing rotations
        adj_graph_full.store_magic_states(
            policy=magic_state_factory.storage_store_policy
        )

    if magic_state_factory.place_reset == "before":
        # refresh the storages 'consumed' using zero states
        adj_graph_full.reset_storages(policy=magic_state_factory.storage_reset_policy)

    # container to store the trees packed
    trees_and_terminals = [(None, None)] * len(commutable_rotations)

    # get unavailable components from the nodes
    components_unavailable = {
        n if adj_graph_full.get_node_type(n) == ComponentType.BUS else n[0]
        for n in adj_graph_full.unavailable_nodes
    }

    # get magic/zero states available
    ms_available = (
        adj_graph_full.nodes_by_status[ComponentType.MAGIC][MagicStateStatus.READY]
        | adj_graph_full.nodes_by_status[ComponentType.STORAGE][StorageStatus.READY]
    )

    zs_available = [
        component
        for component, zs in adj_graph_full.components_by_type[
            ComponentType.ZERO
        ].items()
        if zs.status == ZeroStateStatus.READY
    ]

    # remove beforehand all rotations that are not required to solve the Steiner tree problem
    candidate_rotation = [True] * len(commutable_rotations)
    candidate_rotations_precheck(
        candidate_rotation,
        commutable_rotations,
        ms_available,
        components_unavailable,
        trees_and_terminals,
        adj_graph_full,
        fails_count,
        random_generator,
    )

    if True in candidate_rotation:
        # get current adjacency graph as a copy of the full graph w/o unavailable nodes
        curr_adj_graph = adj_graph_full.deep_copy_available_nodes()

        for idx, rotation in enumerate(commutable_rotations):
            steiner_tree = None
            shortest_path = None
            shortest_tree = None
            if not candidate_rotation[idx]:
                continue

            # RECHECK: if PI/8 and no magic state available, skip
            if rotation.operation_type == PI8 and len(ms_available) == 0:
                continue

            # get list of qubit terminals for this rotation
            qubit_terminals = list(rotation.rotation_active_edges)

            # CHECK: verify if any terminal is disconnected from the current adj graph
            fail = False
            for qubit in qubit_terminals:
                if len(set(curr_adj_graph.nx_graph.neighbors(qubit))) == 0:
                    fail = True
                    break
            if fail:
                fails_count["Qubit is disconnected from graph"] += 1
                continue

            # if multiple qubits, then cache or solve STP
            if len(qubit_terminals) > 1:
                tree_completed, steiner_tree = solve_stree_multi_qubit_terminals(
                    qubit_terminals,
                    curr_adj_graph,
                    steiner_trees_cached,
                    rotation,
                    fails_count,
                    trees_and_terminals,
                    idx,
                    adj_graph_full,
                    zs_available,
                    shortest_path_cache,
                )

                if tree_completed or steiner_tree is None:
                    continue

            # get the connected component in the current adjacent graph containing all terminals
            subgraph = curr_adj_graph.remove_non_terminal_nodes_from_adj_graph(
                qubit_terminals, rotation.operation_type
            )

            # Find the closest magic/zero state to this qubit/tree if:
            #   - PI8/PI4 with a single qubit
            #   - PI8/PI4 with a multiple qubits where no magic/zero state is connected to the tree
            # if rotation.operation_type in {PI4, PI8}:
            # get all magic/zero state nodes in the subgraph
            optional_terminals = get_magic_resource_state(
                rotation, ms_available, zs_available, subgraph
            )

            if len(optional_terminals) == 0:
                fails_count["No magic/zero state in subgraph"] += 1
                continue

            if len(qubit_terminals) > 1:
                assert steiner_tree is not None
                source = transform_stree_into_single_node(subgraph, steiner_tree)
            else:
                source = qubit_terminals[0]

            if rotation.operation_type == PI8:
                (
                    node_chosen,
                    shortest_path,
                ) = magic_state_factory.choose_best_magic_state(
                    subgraph.nx_graph, optional_terminals, source
                )

                # if no magic state was chosen, skip
                if node_chosen is None:
                    fails_count["No path to a magic state"] += 1
                    continue
            else:
                node_chosen, shortest_tree = subgraph.find_closest_zero_state(
                    optional_terminals, source
                )

                # if no zero state was chosen, skip
                if node_chosen is None:
                    fails_count["No path to a zero state"] += 1
                    continue

            if rotation.operation_type == PI8:
                if node_chosen[0][0] == "m":
                    # if magic state was consumed
                    adj_graph_full.set_nodes_ticks([node_chosen], -1)
                elif node_chosen[0][0] == "s":
                    # if storage was consumed
                    adj_graph_full.set_nodes_ticks([node_chosen], -4)
                ms_available.remove(node_chosen)
            else:
                adj_graph_full.set_nodes_ticks(
                    [(node_chosen, "X"), (node_chosen, "Z")], 1
                )
                zs_available.remove(node_chosen)

            if len(qubit_terminals) == 1:
                if rotation.operation_type == PI8:
                    # generate graph with this shortest path
                    steiner_tree = nx.Graph()
                    assert shortest_path is not None
                    nx.add_path(steiner_tree, shortest_path)

                    save_stree_and_remove_terminals(
                        trees_and_terminals,
                        idx,
                        steiner_tree,
                        node_chosen,
                        curr_adj_graph,
                    )
                    continue

                assert shortest_tree is not None
                save_stree_and_remove_terminals(
                    trees_and_terminals,
                    idx,
                    shortest_tree,
                    ((node_chosen, "X"), (node_chosen, "Z")),
                    curr_adj_graph,
                )
                continue

            # if rotation.operation_type in {PI4, PI8}:
            # add shortest path/tree found to the Steiner tree
            sp_and_stree = nx.Graph(steiner_tree)
            bridge = []
            if rotation.operation_type == PI8:
                assert shortest_path is not None
                nx.add_path(sp_and_stree, shortest_path)
                # get node that bridges the shortest path/tree to the Steiner tree
                bridge.append(shortest_path[-2])
            else:
                assert shortest_tree is not None
                sp_and_stree = nx.compose(sp_and_stree, shortest_tree)
                bridge.extend(list(shortest_tree.neighbors(steiner_tree)))

            # add bridge edge
            for link in bridge:
                edges_candidates = list(curr_adj_graph.nx_graph.edges(link))
                for edge in edges_candidates:
                    if edge[1] in steiner_tree:
                        sp_and_stree.add_edge(link, edge[1])
                        break
            sp_and_stree.remove_node(steiner_tree)

            # save tree found for this rotation
            if rotation.operation_type == PI8:
                trees_and_terminals[idx] = (sp_and_stree, node_chosen)
            else:
                trees_and_terminals[idx] = (
                    sp_and_stree,
                    ((node_chosen, "X"), (node_chosen, "Z")),
                )
            curr_adj_graph.nx_graph.remove_nodes_from(sp_and_stree.nodes())
            curr_adj_graph.remove_nodes_from_status(sp_and_stree.nodes())
            continue

    if magic_state_factory.place_store == "after":
        # store all magic states 'ready' into storages 'empty' AFTER packing rotations
        adj_graph_full.store_magic_states(
            policy=magic_state_factory.storage_store_policy
        )

    if magic_state_factory.place_reset == "after":
        # refresh the storages 'consumed' using zero states
        adj_graph_full.reset_storages(policy=magic_state_factory.storage_reset_policy)

    trees, terminals = zip(*trees_and_terminals)
    # reset the availability of all the magic states:
    if hla_flag:
        magic_state_nodes = adj_graph_full.get_nodes_of_type(
            node_type=ComponentType.MAGIC
        )
        zero_state_nodes = adj_graph_full.get_nodes_of_type(
            node_type=ComponentType.ZERO
        )
        adj_graph_full.set_nodes_ticks(zero_state_nodes, 0)
        adj_graph_full.set_nodes_ticks(magic_state_nodes, 0)
    return list(zip(commutable_rotations, trees, terminals))


#! move to "solve_rotations_scheduling.py"?
def solve_rotations_scheduling(
    _circuit_: circuit.Circuit,
    adj_graph_full: AdjacencyGraph,
    magic_state_factory: msf.MagicStateFactory,
) -> tuple[dict, int, float]:
    """Solve the rotations scheduling problem

    Args:
        shortest_path_cache: cache of shortest paths
        _circuit_ : full circuit containing all rotations to be scheduled
        adj_graph_full : quantum computer layout with nx graph
        magic_state_factory: magic state factory used to handle tick update logistics

    Returns:
        rot_assigned_all: rotation and tree packed in each tick
        magic_state_factory.tick: total ticks used
    """

    fails_count = {
        "Qubit cant rotate": 0,
        "Qubit is disconnected from graph": 0,
        "Steiner tree not found": 0,
        "No magic/zero state in subgraph": 0,
        "No path to a magic state": 0,
        "No path to a zero state": 0,
    }

    start = time.time()
    random_generator = random.Random(1)

    # global container to store the scheduling result
    # {tick: (rotation, tree)}
    rot_assigned_all = {}

    # initialize shortest path caching container
    shortest_path_cache = shortest_path_caching.SPCaching()
    shortest_path_cache.reset_spp_caching()

    # dictionary of result cache
    result_cached = {}
    strees_cached = {}

    # generate dependency graph and blocker containers
    dep_graph = dp.DependencyGraphTrivialCommute(_circuit_)
    blockers_reverse, blockers_simple, _ = dep_graph.get_dependency_graph()

    # get list of current rotations candidates for packing
    rot_curr_commutable = []
    rot_id_curr_commutable = []
    for r, n in blockers_simple.items():
        if n == 0:
            rot_curr_commutable.append(_circuit_.rotations[r])
            rot_id_curr_commutable.append(r)

    tick_elapsed = 0
    rot_count = 1
    # while there is any candidate rotation to schedule
    while rot_curr_commutable:
        # (rotation, tree, terminals)
        rot_assigned_this_tick = list(tuple())

        # CHECK: skip ticks while only magic states are required but none are available
        storage_consumed_nodes = adj_graph_full.nodes_by_status[ComponentType.STORAGE][
            StorageStatus.CONSUMED
        ]

        # get all available magic states, including those in the storages
        available_magic_states = (
            magic_state_factory.available_magic_state_for_current_tick(
                adj_graph_full, tick_elapsed
            )
            | adj_graph_full.nodes_by_status[ComponentType.STORAGE][StorageStatus.READY]
        )

        # if there are storage nodes 'consumed' we can assign to zero states now, so do not skip
        if len(storage_consumed_nodes) == 0:
            # check if magic state required (i.e. all current rotations are pi/8)
            magic_state_required = (
                magic_state_factory.check_if_only_magic_state_required(
                    rot_curr_commutable
                )
            )

            # increment tick if all rotations are pi/8 and no magic states available
            if magic_state_required and (not available_magic_states):
                # change storage nodes with status 'preparing' to 'ready'
                for n in frozenset(
                    adj_graph_full.nodes_by_status[ComponentType.STORAGE][
                        StorageStatus.PREPARING
                    ]
                ):
                    adj_graph_full.set_nodes_ticks(
                        [n], adj_graph_full.nx_graph.nodes[n]["ticks"] - 1
                    )
                    adj_graph_full.unavailable_nodes.remove(n)

                tick_elapsed += 1
                continue

        if tick_elapsed > 0:
            magic_state_factory.increment_tick(
                list(tuple()), adj_graph_full, rot_assigned_all, tick_elapsed
            )
            tick_elapsed = 0

        # compute key for candidate rotations at this tick
        key = steiner_tree_caching.compute_subproblem_key(
            available_magic_states, rot_curr_commutable
        )

        if key in result_cached:
            cached_result = result_cached[key]
            rot_assigned_this_tick = steiner_tree_caching.get_result_from_cache(
                cached_result, rot_curr_commutable, adj_graph_full.unavailable_nodes
            )

            rot: tuple
            for rot in rot_assigned_this_tick:
                if isinstance(rot[2], tuple) and rot[2][0][0] == "s":
                    # if storages are used, update their status from 'ready' to 'consumed'
                    assert (
                        adj_graph_full.nx_graph.nodes[rot[2]]["ticks"] == 0
                    ), "Storage is not ready"
                    adj_graph_full.set_nodes_ticks([rot[2]], -4)
                elif isinstance(rot[2], int):
                    # if turning qubit, make the qubit and bus used unavailable
                    adj_graph_full.set_nodes_ticks(rot[1].nodes, 3)
                elif isinstance(rot[2], tuple) and rot[2][0][0] == "m":
                    # if magic state is used, update status to 'depleted'
                    adj_graph_full.set_nodes_ticks([rot[2]], -1)

        if len(rot_assigned_this_tick) == 0:
            # solve the rotations packing problem for this tick
            rot_assigned_this_tick = solve_rotations_packing(
                commutable_rotations=rot_curr_commutable,
                adj_graph_full=adj_graph_full,
                shortest_path_cache=shortest_path_cache,
                steiner_trees_cached=strees_cached,
                random_generator=random_generator,
                fails_count=fails_count,
                magic_state_factory=magic_state_factory,
            )

            # filter rotations successfully packed
            rot_assigned_this_tick = [
                r for r in rot_assigned_this_tick if not r[1] is None
            ]

            # cache set of rotations packed
            cached_result = {}
            for pack in rot_assigned_this_tick:
                cached_result[steiner_tree_caching.get_rotation_key(pack[0])] = pack
            if cached_result:
                result_cached[key] = cached_result

        assigned_rotation_ids = {rot[0].ind for rot in rot_assigned_this_tick}

        magic_state_factory.increment_tick(
            rot_assigned_this_tick, adj_graph_full, rot_assigned_all, 1
        )

        # update blockers to get new available rotations
        new_candidates_ids = dp.update_blockers(
            blockers_simple, blockers_reverse, assigned_rotation_ids
        )

        # combine new rotations with rotations not scheduled
        rot_id_curr_commutable = list(
            (set(rot_id_curr_commutable) - assigned_rotation_ids) | new_candidates_ids
        )
        rot_curr_commutable = [
            _circuit_.rotations[rot_id] for rot_id in rot_id_curr_commutable
        ]

        # print trees generated this tick
        rot_count = print_strees_this_tick(
            rot_assigned_this_tick,
            rot_count,
            len(_circuit_.rotations),
            tick=magic_state_factory.tick,
            print_interval=1,
        )

    # ! (delete later) print packing fails count
    total_fails_count = 0
    print("\nPacking fails count...")
    for fail, count in fails_count.items():
        print("\t", fail, "=", count)
        total_fails_count += count
    print("Total = ", total_fails_count)

    print("\nTotal number of ticks : ", magic_state_factory.tick)
    end = time.time()
    total = end - start
    print(f"\nTotal time : {total:.3f}")
    return rot_assigned_all, magic_state_factory.tick, total
