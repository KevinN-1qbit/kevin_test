""" Contains the class AdjacencyGraph and functions to built AdjacencyGrpah instances """
from __future__ import annotations

import copy
import dataclasses
from abc import ABC
from enum import Enum
from itertools import chain
from typing import Collection, Iterable, Literal, NewType, cast

import networkx as nx
from networkx.utils import pairwise

import src.scheduler.caching.shortest_path_caching as spc
from src.scheduler.circuit_and_rotation.circuit import MEASUREMENT, PI4, PI8, TURN
from src.scheduler.surface_code_layout import tiles
from src.layout_processor import tile_layout

# encourage finding a Steiner tree that do not cross terminal nodes
EDGE_WEIGHT_VERY_HIGH = (
    100000  # ! at least EDGE_WEIGHT_HIGH * nb of edges with EDGE_WEIGHT_HIGH
)
# encourage finding a Steiner tree that do not cross bus tiles required by other trees
EDGE_WEIGHT_HIGH = 10000  # ! at least the number of bus tiles in the full graph


NodeName = NewType("Nodename", str)
BusTile = NewType("BusNode", int)

TileName = tuple[NodeName, Literal["X", "Z"]]
DoubleTileName = tuple[TileName, TileName]

AdjGraphNode = TileName | BusTile | DoubleTileName


class ComponentType(Enum):
    QUBIT = 1
    MAGIC = 2
    ZERO = 3
    BUS = 4
    STORAGE = 5


class QubitStatus(Enum):
    READY = 1
    BUSY = 2


class MagicStateStatus(Enum):
    READY = 1
    DEPLETED = 2
    REPLENISHING = 3


class ZeroStateStatus(Enum):
    READY = 1
    BUSY = 2


class BusTileStatus(Enum):
    READY = 1
    BUSY = 2


class StorageStatus(Enum):
    READY = 1
    CONSUMED = 2
    CONNECT_TO_0_STATE = 3
    EMPTY = 4
    PREPARING = 5


TileStatus = (
    ComponentType
    | QubitStatus
    | MagicStateStatus
    | ZeroStateStatus
    | BusTileStatus
    | StorageStatus
)


def get_node_status(node_type: ComponentType, ticks: int) -> TileStatus:
    """Return the status of a node given its type and ticks attributes"""

    if ticks == 0:
        # component is available
        if node_type == ComponentType.QUBIT:
            return QubitStatus.READY
        if node_type == ComponentType.ZERO:
            return ZeroStateStatus.READY
        if node_type == ComponentType.MAGIC:
            return MagicStateStatus.READY
        if node_type == ComponentType.BUS:
            return BusTileStatus.READY
        if node_type == ComponentType.STORAGE:
            return StorageStatus.READY
    if node_type in {ComponentType.QUBIT, ComponentType.ZERO, ComponentType.BUS}:
        if ticks > 0:
            # component is not available
            if node_type == ComponentType.QUBIT:
                return QubitStatus.BUSY
            if node_type == ComponentType.ZERO:
                return ZeroStateStatus.BUSY
            if node_type == ComponentType.BUS:
                return BusTileStatus.BUSY
    if node_type == ComponentType.MAGIC:
        if ticks == -1:
            # waiting to be replenished with the others ms in the same factory
            return MagicStateStatus.DEPLETED
        if ticks > 0:
            # ms factory is being replenished
            return MagicStateStatus.REPLENISHING
    if node_type == ComponentType.STORAGE:
        if ticks == -4:
            # storage is used and needs to be restored using a zero state
            return StorageStatus.CONSUMED
        if ticks == -3:
            return StorageStatus.CONNECT_TO_0_STATE
        if ticks == -2:
            # storage is ready to receive a magic state
            return StorageStatus.EMPTY
        if ticks > 0:
            # storage is charging (tick 1: connect to ms, tick 2: rotate edges)
            return StorageStatus.PREPARING
    raise ValueError(f"Invalid node_type {node_type}")


class Component(ABC):
    @property
    def status(self) -> TileStatus:
        ...

    def add_neighbor(
        self,
        n_or_axis: AdjGraphNode | Literal["X", "Z"],
        _neighbor: AdjGraphNode | None = None,
    ) -> None:
        ...

    def set_status(self, status: int | list[int]) -> None:
        ...


@dataclasses.dataclass
class Qubit(Component):
    """Qubit component

    Stores information about data qubit components:
        - id: component id in the format qX
        - tile: tile occupied by this component
        - status: current component status
        - neighbors: neighbor nodes
            Note: qubit components are only linked to buses.
    """

    id: NodeName
    tile: tiles.Tile | None = None
    status: QubitStatus = QubitStatus.READY
    neighbors: dict[Literal["X", "Z"], set[AdjGraphNode]] = dataclasses.field(
        default_factory=dict
    )

    def __post_init__(self):
        self.neighbors["X"] = set()
        self.neighbors["Z"] = set()

    @property
    def angle_active(self) -> Literal["X", "Z", "B", ""]:
        """Return the angle active for this qubit"""
        if len(self.neighbors["X"]) > 0 and len(self.neighbors["Z"]) > 0:
            return "B"
        if len(self.neighbors["X"]) > 0:
            return "X"
        if len(self.neighbors["Z"]) > 0:
            return "Z"
        return ""

    def set_tile(self, _tile: tiles.Tile) -> None:
        """Set qubit tile"""
        self.tile = _tile

    def set_status(self, ticks: int) -> None:
        """Set qubit status:
        - 'busy': qubit is busy (either turning or already scheduled this tick)
        - 'ready': qubit is ready for use
        """
        status = get_node_status(ComponentType.QUBIT, ticks)
        assert isinstance(status, QubitStatus)
        self.status = status

    def add_neighbor(self, axis: Literal["X", "Z"], neighbor: AdjGraphNode) -> None:
        """Add neighbor"""
        self.neighbors[axis].add(neighbor)

    def turn_qubit(self) -> None:
        """Turn qubit angle (change neighbors)"""
        control = self.neighbors["X"]
        self.neighbors["X"] = self.neighbors["Z"]
        self.neighbors["Z"] = control


@dataclasses.dataclass
class MagicState(Component):
    """Magic state component

    Stores information about magic state components:
        - node: node id in the format (mX,'Z')
            Note: magic state components are represented by a single node with edge 'Z'.
        - tile: tile occupied by this component
        - (NOT IMPLEMENTED) factory: factory which this component belongs to (int between 1 to NUM_FACTORIES)
        - status: current component status
        - neighbors: neighbor nodes
            Note: magic state components are only linked to buses *and storages (NOT IMPLEMENTED)*.
    """

    node: AdjGraphNode
    tile: tiles.Tile | None = None
    status: MagicStateStatus = MagicStateStatus.READY
    neighbor: AdjGraphNode | None = None

    def set_tile(self, tile: tiles.Tile) -> None:
        """Set magic state tile"""
        self.tile = tile

    def set_neighbor(self, neighbor: AdjGraphNode) -> None:
        """Set magic state neighbor (only one neighbor)"""
        self.neighbor = neighbor

    def set_status(self, ticks: int) -> None:
        """Set magic state status:
        - 'depleted': waiting to start the replenishment
        - 'ready': ready for use
        - 'replenishing': facotry is being replenished
        """
        status = get_node_status(ComponentType.MAGIC, ticks)
        assert isinstance(status, MagicStateStatus)
        self.status = status


@dataclasses.dataclass
class Storage(Component):
    """Storage component

    Stores information about storage components:
    - node: node id in the format (sX,'Z')
        Note: like magic states, storage components are represented by a single node with edge 'Z'.
    - tile: tile occupied by this component
    - status: current component status
    - neighbors: neighbor nodes
        Note: storage components are only linked to buses *and magic states (NOT IMPLEMENTED)*.
    """

    node: AdjGraphNode
    tile: tiles.Tile | None = None
    status: StorageStatus = StorageStatus.READY
    neighbors: set[AdjGraphNode] = dataclasses.field(default_factory=set)

    def set_tile(self, _tile: tiles.Tile) -> None:
        """Set storage tile"""
        self.tile = _tile

    def set_neighbor(self, neighbor: AdjGraphNode) -> None:
        """Set storage neighbors"""
        self.neighbors.add(neighbor)

    def set_status(self, ticks: int) -> None:
        """Set storage status:
        - 'consumed': used and needs to be restored using a zero state
        - 'connected to 0 state': connected to a zero state this tick
        - 'empty': ready to receive a magic state
        - 'preparing': charging (tick 1: connect to ms, tick 2: rotate edges)
        - 'ready': ready to be used
        """
        status = get_node_status(ComponentType.STORAGE, ticks)
        assert isinstance(status, StorageStatus)
        self.status = status


@dataclasses.dataclass
class TileInfo:
    tile: tiles.Tile | None = None
    X: set = dataclasses.field(default_factory=set)
    Z: set = dataclasses.field(default_factory=set)

    def __getitem__(self, index: Literal["X", "Z"]) -> set:
        match index:
            case "X":
                return self.X
            case "Z":
                return self.Z


@dataclasses.dataclass
class ZeroState(Component):
    """Zero state component

    Stores information about zero state components:
        - id: component id in the format zX
            Note: all zero states can also be represented by a pair of nodes [(zX,'X'), (zX,'Z')]
        - tile: tiles occupied by this component
            Note: zero states occupy two tiles.
        - status: current component status
        - neighbors: neighbor nodes
            Note: zero state components are only linked to buses.
    """

    id: NodeName
    tiles: list[TileInfo] = dataclasses.field(
        default_factory=lambda: [TileInfo(), TileInfo()]
    )
    status: ZeroStateStatus = ZeroStateStatus.READY

    def set_tiles(self, pos: int, tile: tiles.Tile) -> None:
        """Set the two zero state tiles"""
        self.tiles[pos].tile = tile

    def set_status(self, ticks: list[int]) -> None:
        """Set zero state status:
        - 'busy': zero state is busy (already scheduled this tick)
        - 'ready': zero state is ready for use
        """
        # assert ticks[0] == ticks[1], f'Ticks count for zero states nodes are different'
        status = get_node_status(ComponentType.ZERO, ticks[0])
        assert isinstance(status, ZeroStateStatus)
        self.status = status


@dataclasses.dataclass
class Bus(Component):
    """Bus tile component

    Stores information about bus components:
        - id: component id in the format X (int)
        - tile: tile occupied by this component
        - status: current component status
        - neighbors: neighbor nodes
            Note: bus tile components can be linked to all types of nodes.
    """

    node: int
    tile: tiles.Tile | None = None
    status: BusTileStatus = BusTileStatus.READY

    def set_tile(self, _tile: tiles.Tile):
        """Set bus tile"""
        self.tile = _tile

    def set_status(self, ticks: int):
        """Set bus status:
        - 'busy': bus is busy (either used for turning qubit or already scheduled this tick)
        - 'ready': bus is ready for use
        """
        status = get_node_status(ComponentType.BUS, ticks)
        assert isinstance(status, BusTileStatus)
        self.status = status


class AdjacencyGraph:
    """Adjacency graph"""

    def __init__(self, layout_: tile_layout.TileLayout):
        self.layout = layout_
        self.nx_graph: nx.Graph = nx.Graph()
        self.unavailable_nodes = set()

        self.components_by_type: dict[
            ComponentType, dict[NodeName | BusTile, Component]
        ] = {
            ComponentType.QUBIT: {},
            ComponentType.MAGIC: {},
            ComponentType.ZERO: {},
            ComponentType.BUS: {},
            ComponentType.STORAGE: {},
        }

        self.nodes_by_status: dict[
            ComponentType, dict[TileStatus, set[AdjGraphNode]]
        ] = {
            ComponentType.QUBIT: {QubitStatus.READY: set(), QubitStatus.BUSY: set()},
            ComponentType.MAGIC: {
                MagicStateStatus.READY: set(),
                MagicStateStatus.DEPLETED: set(),
                MagicStateStatus.REPLENISHING: set(),
            },
            ComponentType.ZERO: {
                ZeroStateStatus.READY: set(),
                ZeroStateStatus.BUSY: set(),
            },
            ComponentType.BUS: {BusTileStatus.READY: set(), BusTileStatus.BUSY: set()},
            ComponentType.STORAGE: {
                StorageStatus.READY: set(),
                StorageStatus.CONSUMED: set(),
                StorageStatus.CONNECT_TO_0_STATE: set(),
                StorageStatus.EMPTY: set(),
                StorageStatus.PREPARING: set(),
            },
        }

    @property
    def qubit_angle(self) -> dict[AdjGraphNode, Literal["X", "Z", "B"]]:
        """Return the qubits' angles available"""
        all_qubits = {}
        for qubit in self.get_nodes_of_type(ComponentType.QUBIT):
            if not qubit[0] in all_qubits:
                all_qubits[qubit[0]] = qubit[1]
            else:
                all_qubits[qubit[0]] = "B"
        return all_qubits

    def get_node_type(self, node: AdjGraphNode) -> ComponentType:
        """Return the node type"""

        if isinstance(node, int):
            return ComponentType.BUS
        if isinstance(node, tuple):
            if node[0][0] == "r":
                return ComponentType.ZERO
            if node[0][0] == "m":
                return ComponentType.MAGIC
            if node[0][0] == "q":
                return ComponentType.QUBIT
            if node[0][0] == "s":
                return ComponentType.STORAGE
        if isinstance(node, nx.graph):
            return "graph"
        raise ValueError(f"Unknown node {node}")

    def get_nodes_of_type(self, node_type: Enum) -> list:
        """Return all nodes in the adjacency graph of a given type"""
        nodes_types = nx.get_node_attributes(self.nx_graph, "type")
        return [n for n, v in nodes_types.items() if v == node_type]

    def remove_nodes_from_status(self, nodes_removed: list):
        """Remove nodes from the nodes_by_status container"""
        for node in nodes_removed:
            node_type = self.get_node_type(node)

            # remove from previous status
            for _, nodes in self.nodes_by_status[node_type].items():
                if node in nodes:
                    nodes.remove(node)
                    break

    def get_bus_zs(self) -> dict:
        """Return a dictionary with the zero states linked to each bus"""

        bzs = dict([])
        for zero_state in self.get_nodes_of_type(ComponentType.ZERO):
            if zero_state[0] in bzs:
                bzs[zero_state[0]] += list(self.nx_graph.neighbors(zero_state))
            else:
                bzs[zero_state[0]] = list(self.nx_graph.neighbors(zero_state))

        return {tuple(k): v for v, k in bzs.items()}

    def process_graph(self):
        """Generate the adjacency graph"""
        # get graph from layout
        graph_ = self.layout.get_graph_for_mip()

        # first, add qubit
        for key, val in graph_.inds_to_qubit_edges.items():
            component = NodeName("q" + str(val.ind))
            xz = val.xz_type
            self.nx_graph.add_node(
                (component, xz),
                type=ComponentType.QUBIT,
                id=component,
                tile=val.patch_tile,
            )

            q = Qubit(component)
            q.set_tile(val.patch_tile)
            self.components_by_type[ComponentType.QUBIT][component] = q

        # next, add magic state
        for key, val in graph_.inds_to_ms_edges.items():
            component = NodeName("m" + str(val.ind))
            xz = val.xz_type
            self.nx_graph.add_node(
                (component, xz),
                type=ComponentType.MAGIC,
                id=component,
                tile=val.patch_tile,
            )

            assert xz == "X" or xz == "Z"
            ms = MagicState((component, xz))
            ms.set_tile(val.patch_tile)
            self.components_by_type[ComponentType.MAGIC][component] = ms

        # next, add zero state
        for key, val in graph_.inds_to_resource_edges.items():
            component = NodeName("r" + str(val.ind))
            xz = val.xz_type
            self.nx_graph.add_node(
                (component, xz),
                type=ComponentType.ZERO,
                id=component,
                tile=val.patch_tile,
            )

            if id not in self.components_by_type[ComponentType.ZERO]:
                zs = ZeroState(component)
                zs.set_tiles(0, val.patch_tile)
                self.components_by_type[ComponentType.ZERO][component] = zs
            else:
                component = self.components_by_type[ComponentType.ZERO][component]
                assert isinstance(component, ZeroState)
                component.set_tiles(1, val.patch_tile)

        # next, add storage
        for key, val in graph_.inds_to_storage_edges.items():
            component = NodeName("s" + str(val.ind))
            xz = val.xz_type
            self.nx_graph.add_node(
                (component, xz),
                type=ComponentType.STORAGE,
                id=component,
                tile=val.patch_tile,
            )

            assert xz == "X" or xz == "Z"
            st = Storage((component, xz))
            st.set_tile(val.patch_tile)
            self.components_by_type[ComponentType.STORAGE][component] = st

        # next, add bus tiles
        for component, _tile in graph_.inds_to_bus_tiles.items():
            self.nx_graph.add_node(
                component, type=ComponentType.BUS, id=component, tile=_tile
            )
            component = BusTile(component)
            bus = Bus(component)
            bus.set_tile(_tile)
            # component =
            self.components_by_type[ComponentType.BUS][component] = bus

        # next, add all connections
        for key, val in graph_.adj_matrix.items():
            if key not in graph_.inds_to_bus_tiles:
                continue

            key = BusTile(key)

            for node in val:
                # add connecting bus tiles
                if node in graph_.inds_to_bus_tiles:
                    self.nx_graph.add_edge(key, node, weight=1)
                    node = BusTile(node)
                    self.components_by_type[ComponentType.BUS][key].add_neighbor(node)
                    self.components_by_type[ComponentType.BUS][node].add_neighbor(key)

                # add connecting qubit
                elif node in graph_.inds_to_qubit_edges:
                    edge = graph_.inds_to_qubit_edges[node]
                    xz = edge.xz_type
                    component = NodeName("q" + str(edge.ind))
                    self.nx_graph.add_edge(
                        key, (component, xz), weight=EDGE_WEIGHT_VERY_HIGH
                    )
                    assert xz == "X" or xz == "Z"
                    self.components_by_type[ComponentType.BUS][key].add_neighbor(
                        (component, xz)
                    )
                    self.components_by_type[ComponentType.QUBIT][
                        component
                    ].add_neighbor(xz, key)

                # add connecting zero state
                elif node in graph_.inds_to_resource_edges:
                    edge = graph_.inds_to_resource_edges[node]
                    xz = edge.xz_type
                    component = NodeName("r" + str(edge.ind))
                    assert self.get_node_type(key)
                    self.nx_graph.add_edge(
                        key, (component, xz), weight=EDGE_WEIGHT_VERY_HIGH
                    )
                    assert xz == "X" or xz == "Z"
                    self.components_by_type[ComponentType.BUS][key].add_neighbor(
                        (component, xz)
                    )

                    comp = self.components_by_type[ComponentType.ZERO][component]
                    assert isinstance(comp, ZeroState)
                    if comp.tiles[0].tile == edge.patch_tile:
                        comp.tiles[0][xz].add(key)
                    elif comp.tiles[1].tile == edge.patch_tile:
                        comp.tiles[1][xz].add(key)

                # add connecting magic state
                elif node in graph_.inds_to_ms_edges:
                    edge = graph_.inds_to_ms_edges[node]
                    xz = edge.xz_type
                    assert xz == "X" or xz == "Z"
                    component = NodeName("m" + str(edge.ind))
                    self.nx_graph.add_edge(
                        key, (component, xz), weight=EDGE_WEIGHT_VERY_HIGH
                    )

                    comp = self.components_by_type[ComponentType.BUS][key]
                    comp.add_neighbor((component, xz))
                    mcomp = self.components_by_type[ComponentType.MAGIC][component]
                    assert isinstance(mcomp, MagicState)
                    mcomp.set_neighbor(key)

                # add connecting storage
                elif node in graph_.inds_to_storage_edges:
                    edge = graph_.inds_to_storage_edges[node]
                    xz = edge.xz_type
                    assert xz == "X" or xz == "Z"
                    component = NodeName("s" + str(edge.ind))
                    self.nx_graph.add_edge(
                        key, (component, xz), weight=EDGE_WEIGHT_VERY_HIGH
                    )
                    self.components_by_type[ComponentType.BUS][key].add_neighbor(
                        (component, xz)
                    )
                    comp = self.components_by_type[ComponentType.STORAGE][component]
                    assert isinstance(comp, Storage)
                    comp.set_neighbor(key)

        nx.set_node_attributes(self.nx_graph, 0, name="ticks")
        tile_types = {
            ComponentType.QUBIT,
            ComponentType.MAGIC,
            ComponentType.ZERO,
            ComponentType.BUS,
        }

        for node_type in tile_types:
            for node in self.get_nodes_of_type(node_type):
                if node_type == ComponentType.QUBIT:
                    self.nodes_by_status[node_type][QubitStatus.READY].add(node)
                elif node_type == ComponentType.MAGIC:
                    self.nodes_by_status[node_type][MagicStateStatus.READY].add(node)
                elif node_type == ComponentType.ZERO:
                    self.nodes_by_status[node_type][ZeroStateStatus.READY].add(node)
                elif node_type == ComponentType.BUS:
                    self.nodes_by_status[node_type][BusTileStatus.READY].add(node)

                if node_type in {ComponentType.QUBIT, ComponentType.MAGIC}:
                    self.components_by_type[node_type][node[0]].set_status(0)
                elif node_type == ComponentType.BUS:
                    self.components_by_type[node_type][node].set_status(0)
                else:
                    self.components_by_type[node_type][node[0]].set_status([0, 0])

        # initialize storage nodes to the 'empty' status
        for node in self.get_nodes_of_type(ComponentType.STORAGE):
            self.nx_graph.nodes[node]["ticks"] = -2
            self.nodes_by_status[ComponentType.STORAGE][StorageStatus.EMPTY].add(node)
            self.components_by_type[ComponentType.STORAGE][node[0]].set_status(-2)

    def store_magic_states(self, policy: str):
        """Send available magic states to empty storages"""

        ms_nodes = frozenset(
            self.nodes_by_status[ComponentType.MAGIC][MagicStateStatus.READY]
        )

        for ms in ms_nodes:
            if policy == "match":
                assert self.get_node_type(ms) == ComponentType.MAGIC
                # match policy:
                #   get the storage that matches the magic state (i.e., s1-m1, s2-m2, etc.)
                name = NodeName("s" + ms[0][1:])
                comp = self.components_by_type[ComponentType.STORAGE][name]
                assert isinstance(comp, Storage)
                st = comp.node
                assert self.get_node_type(st) == ComponentType.STORAGE
                # check if it is empty
                scomp = self.components_by_type[ComponentType.STORAGE][st[0]]
                assert isinstance(scomp, Storage)
                if scomp.status == StorageStatus.EMPTY:
                    self.set_nodes_ticks([ms], -1)
                    self.set_nodes_ticks([st], 2)
            # elif policy == 'random':
            #     # TODO random policy: get a random empty storage
            #     st = random.choice(st_nodes)
            #     (length, path) = nx.single_source_dijkstra(self.nx_graph,
            #                                                st,
            #                                                target=ms,
            #                                                weight='weight')
            #     # what if path does not exist?
            else:
                raise Exception("Invalid magic state storage policy")

    def reset_storages(self, policy: str):
        """Reset magic state storages using zero states"""
        st_nodes = frozenset(
            self.nodes_by_status[ComponentType.STORAGE][StorageStatus.CONSUMED]
        )

        for st in st_nodes:
            if policy == "match":
                assert self.get_node_type(st) == ComponentType.STORAGE
                # match policy: get the zero state that matches the storage
                # ! BUG some matches are incorrect (i.e., s2-r4 and s4-r2)
                zs = self.components_by_type[ComponentType.ZERO][
                    NodeName("r" + st[0][1:])
                ]
                assert isinstance(zs, ZeroState)
                if zs.status == ZeroStateStatus.READY:
                    # TODO cache tree? solve shortest path and add the second node (faster)?
                    steiner_tree = self.solve_stree([st, (zs.id, "X"), (zs.id, "Z")])
                    assert steiner_tree is not None

                    # make nodes used unavailable this tick
                    for node in steiner_tree.nodes():
                        node = cast(AdjGraphNode, node)
                        if self.get_node_type(node) in {
                            ComponentType.BUS,
                            ComponentType.ZERO,
                        }:
                            # if node is bus or zero, make it 'busy'
                            self.set_nodes_ticks([node], 1)
                        else:
                            # if node is storage, make it 'connected to zero state'
                            self.set_nodes_ticks([node], -3)
            else:
                raise Exception("Invalid magic state storage reset policy")

    def turn_qubit(
        self,
        q_old: TileName,
    ):
        """Turn qubit in a graph

        Args:
            graph: full graph
            q_old: qubit state before turning

        Returns:
            graph: updated full graph
        """

        relabel = {}

        angle_new = cast(Literal["X", "Z"], list({"X", "Z"} - set(q_old[1]))[0])
        q_new = (q_old[0], angle_new)

        # relabel ('q','X') to ('','Z') and ('q','Z') to ('q','X')
        relabel[(q_old[0], "X")] = ("", "Z")
        nx.relabel_nodes(self.nx_graph, relabel, False)

        # ? why is it faster when clearing?
        relabel.clear()
        relabel[(q_old[0], "Z")] = (q_old[0], "X")
        nx.relabel_nodes(self.nx_graph, relabel, False)

        # relabel ('','Z') to ('q','Z')
        relabel.clear()
        relabel[("", "Z")] = (q_old[0], "Z")
        nx.relabel_nodes(self.nx_graph, relabel, False)

        # update components_by_type
        comp = self.components_by_type[ComponentType.QUBIT][q_old[0]]
        assert isinstance(comp, Qubit)
        control = comp.neighbors["X"]
        comp.neighbors["X"] = comp.neighbors["Z"]
        comp.neighbors["Z"] = control

        # update nodes_by_status
        self.nodes_by_status[ComponentType.QUBIT][QubitStatus.READY].remove(q_old)
        self.nodes_by_status[ComponentType.QUBIT][QubitStatus.READY].add(q_new)

        return self

    def set_nodes_ticks(self, nodes: Iterable[AdjGraphNode], nb_ticks: int) -> None:
        """Set the ticks countdown for a given list of nodes"""

        for node in nodes:
            # get node type and status
            node_type = self.get_node_type(node)

            if node_type in {
                ComponentType.QUBIT,
                ComponentType.MAGIC,
                ComponentType.STORAGE,
                ComponentType.ZERO,
            }:
                assert self.get_node_type(node) != ComponentType.BUS
                comp = self.components_by_type[node_type][node[0]]
                node_status: TileStatus = comp.status
            elif node_type == ComponentType.BUS:
                assert self.get_node_type(node) == ComponentType.BUS
                comp = self.components_by_type[node_type][node]
                node_status: TileStatus = comp.status
            else:
                raise ValueError("Invalid node_type", node_type)

            # remove node from this status
            flag = False
            if (
                node_type == ComponentType.ZERO
                and node not in self.nodes_by_status[node_type][node_status]
            ):
                # avoid error for the second zero state node
                self.nodes_by_status[ComponentType.ZERO][node_status].add(node)
                if node_status == ZeroStateStatus.BUSY:
                    node_status = ZeroStateStatus.READY
                elif node_status == ZeroStateStatus.READY:
                    node_status = ZeroStateStatus.BUSY
                self.nodes_by_status[ComponentType.ZERO][node_status].remove(node)
                flag = True
            else:
                self.nodes_by_status[node_type][node_status].remove(node)

            # set new number of ticks
            self.nx_graph.nodes[node]["ticks"] = nb_ticks

            # update node status
            if not flag:
                if node_type in {
                    ComponentType.QUBIT,
                    ComponentType.MAGIC,
                    ComponentType.STORAGE,
                    ComponentType.ZERO,
                }:
                    assert self.get_node_type(node) != ComponentType.BUS
                    if node_type == ComponentType.ZERO:
                        self.components_by_type[node_type][node[0]].set_status(
                            [nb_ticks]
                        )
                    else:
                        self.components_by_type[node_type][node[0]].set_status(
                            nb_ticks
                        )  # type I don't know why this is failing
                    node_status = self.components_by_type[node_type][node[0]].status
                elif node_type == ComponentType.BUS:
                    assert self.get_node_type(node) == ComponentType.BUS
                    self.components_by_type[node_type][node].set_status(nb_ticks)
                    node_status = self.components_by_type[node_type][node].status

                # add node to its new status
                self.nodes_by_status[node_type][node_status].add(node)

            # update nodes availability
            if nb_ticks != 0:
                if self.get_node_type(node) == ComponentType.STORAGE:
                    # if node is a storage, it is only unavailable when nb_ticks is positive
                    if nb_ticks > 0:
                        self.unavailable_nodes.add(node)
                else:
                    # if ticks is set to either -1 or a positive number
                    self.unavailable_nodes.add(node)

            # ? always remove node from unavailable_nodes?
            # needed for when set_nodes_ticks is called with nb_ticks=0
            elif node in self.unavailable_nodes:
                self.unavailable_nodes.remove(node)

    def decrease_nodes_ticks(self, tick_elapsed: int):
        """Decrease the ticks countdown by "ticks_elapsed" for all nodes"""

        qubits_to_turn = []
        nodes_become_available_again = set()
        for node in copy.copy(self.unavailable_nodes):
            assert self.nx_graph.nodes[node]["ticks"] != 0, "Node ticks count = 0"

            # ticks can be equal to -1 for magic states and storages
            if self.nx_graph.nodes[node]["ticks"] > 0:
                if self.nx_graph.nodes[node]["ticks"] - tick_elapsed > 0:
                    self.set_nodes_ticks(
                        [node], self.nx_graph.nodes[node]["ticks"] - tick_elapsed
                    )
                else:
                    self.set_nodes_ticks([node], 0)
                    nodes_become_available_again.add(node)

                    if self.get_node_type(node) == ComponentType.QUBIT:
                        qubits_to_turn.append(node)

        # ? (check) do we need this here?
        for qubit in qubits_to_turn:
            self = self.turn_qubit(qubit)

        # remove nodes that became available again from the set of unavailable nodes
        self.unavailable_nodes = self.unavailable_nodes - nodes_become_available_again

        # change storage status from 'connected to 0 state' to 'ready' when decreasing nodes ticks
        storage_connected = frozenset(
            self.nodes_by_status[ComponentType.STORAGE][
                StorageStatus.CONNECT_TO_0_STATE
            ]
        )
        if len(storage_connected) > 0:
            self.set_nodes_ticks(storage_connected, -2)

    def set_edge_weights(self, edges: set, weight: int):
        """Set weight value of a set of edges in the graph"""

        new_weights = {e: weight for e in edges}
        nx.set_edge_attributes(self.nx_graph, new_weights, "weight")

    def remove_non_terminal_nodes_from_adj_graph(
        self, terminals: list[TileName], operation_type: int
    ) -> AdjacencyGraph:
        """Remove all nodes that are not of interest"""

        # remove non terminal qubit nodes
        qubits_remove = (
            self.nodes_by_status[ComponentType.QUBIT][QubitStatus.READY]
            | self.nodes_by_status[ComponentType.QUBIT][QubitStatus.BUSY]
        ) - set(terminals)

        # remove magic/zero state nodes, if needed
        other_nodes: set[AdjGraphNode] = set()
        if operation_type == PI8:
            for nodes in self.nodes_by_status[ComponentType.ZERO].values():
                other_nodes |= nodes
            other_nodes |= (
                self.nodes_by_status[ComponentType.STORAGE][StorageStatus.EMPTY]
                | self.nodes_by_status[ComponentType.STORAGE][StorageStatus.CONSUMED]
            )
        elif operation_type == PI4:
            for node_type in [ComponentType.MAGIC, ComponentType.STORAGE]:
                for nodes in self.nodes_by_status[node_type].values():
                    other_nodes |= nodes
        elif operation_type == MEASUREMENT:
            for node_type in [
                ComponentType.ZERO,
                ComponentType.MAGIC,
                ComponentType.STORAGE,
            ]:
                for nodes in self.nodes_by_status[node_type].values():
                    other_nodes |= nodes

        nodes_to_remove = qubits_remove | other_nodes

        # generate a graph without the nodes to be removed
        reduced_graph = self.independent_shallow_copy()
        reduced_graph.nx_graph.remove_nodes_from(nodes_to_remove)

        return reduced_graph

    def find_closest_zero_state(
        self, zs_candidates: Collection[AdjGraphNode], target: TileName
    ) -> tuple[None, None] | tuple[str, nx.Graph | None]:
        """Find the closest zero state from a list of candidates to a target node"""

        min_weight = len(self.nx_graph) + 1
        terminals_chosen = None
        min_tree = None

        if len(zs_candidates) == 0:
            raise ValueError("zs_candidates cannot be empty")

        # find the smallest Steiner tree to connect target to the candidates
        for nodes in zs_candidates:
            for node in nodes:
                assert self.get_node_type(node) != ComponentType.BUS
            terminals = [target, nodes[0], nodes[1]]
            tree = self.solve_stree(terminals)

            if tree is None:
                continue

            weight = len(tree.nodes)

            if weight < min_weight:
                min_weight = weight
                min_tree = tree
                terminals_chosen = [*nodes]

        if min_weight == len(self.nx_graph) + 1:
            return None, None

        # cast: this is potentially None only because zs_candidates may be empty, but we already checked that
        terminals_chosen = cast(list[NodeName | str], terminals_chosen)
        return terminals_chosen[0][0], min_tree

    def independent_shallow_copy(self) -> AdjacencyGraph:
        """Creates new independent graph with a shallow copy"""

        copy_graph = AdjacencyGraph(self.layout)
        copy_graph.nx_graph = self.nx_graph.__class__()
        copy_graph.nx_graph.add_nodes_from(self.nx_graph)
        copy_graph.nx_graph.add_edges_from(self.nx_graph.edges)
        return copy_graph

    def deep_copy_available_nodes(self) -> AdjacencyGraph:
        """Creates new graph with a deep copy without unavailable nodes"""

        copy_graph = self.independent_shallow_copy()

        # remove unavailable nodes
        copy_graph.nx_graph.remove_nodes_from(self.unavailable_nodes)

        # copy attributes
        for node in copy_graph.nx_graph.nodes():
            copy_graph.nx_graph.nodes[node]["type"] = self.nx_graph.nodes[node]["type"]
            copy_graph.nx_graph.nodes[node]["ticks"] = self.nx_graph.nodes[node][
                "ticks"
            ]

        # get node status
        for node in copy_graph.nx_graph.nodes():
            node = cast(AdjGraphNode, node)
            node_type = self.get_node_type(node)
            node_status = get_node_status(node_type, self.nx_graph.nodes[node]["ticks"])
            copy_graph.nodes_by_status[node_type][node_status].add(node)

        return copy_graph

    def solve_stree(
        self, terminals: list[TileName], sp_caching: spc.SPCaching | None = None
    ) -> nx.Graph | None:
        """Return a Steiner tree for the given list of terminal nodes in graph
        Args:
            terminals: terminal nodes
            sp_caching: caching for shortest paths
        """

        # reimplementing stree.steiner_tree from NetworkX
        H = nx.complete_graph(terminals)
        terminals = list(terminals)
        attrs = {}
        edges_removed = set()

        # find shortest path between all pairs of terminal nodes
        for i in range(0, len(terminals) - 1):
            for j in range(i + 1, len(terminals)):
                source = terminals[i]
                target = terminals[j]
                length, path = None, None
                try:
                    length, path = shortest_path_internal_caching(
                        self.nx_graph, source, target, sp_caching
                    )
                except nx.NetworkXNoPath:
                    # if no path exists, this ST problem is infeasible
                    self.nx_graph.add_edges_from(
                        edges_removed, weight=EDGE_WEIGHT_VERY_HIGH
                    )
                    return None

                attrs[(source, target)] = {"distance": length, "path": path}

                # remove edges connected to terminals but not used in this path
                # to avoid crossing a terminal node when generating the stree
                if len(terminals) > 2:
                    # remove from graph the edges linked to the terminals but not used in this path
                    edges_to_remove = set()
                    if (
                        not self.get_node_type(source) == ComponentType.BUS
                        and not self.get_node_type(source) == "graph"
                    ):
                        edges_to_remove.update(self.nx_graph.edges(source))
                        edges_to_remove.remove((source, path[1]))
                    if (
                        not self.get_node_type(target) == ComponentType.BUS
                        and not self.get_node_type(target) == "graph"
                    ):
                        edges_to_remove.update(self.nx_graph.edges(target))
                        edges_to_remove.remove((target, path[len(path) - 2]))
                    self.nx_graph.remove_edges_from(edges_to_remove)
                    edges_removed.update(edges_to_remove)

        # add back to the graph the edges removed
        if len(terminals) > 2:
            self.nx_graph.add_edges_from(edges_removed, weight=EDGE_WEIGHT_VERY_HIGH)

        nx.set_edge_attributes(H, attrs)

        # mst_edges: generate a minimum spanning tree that connects all nodes in H
        mst_edges = nx.minimum_spanning_edges(H, weight="distance", data=True)

        # get the edges used in the paths of the mst generated
        edges = chain.from_iterable(pairwise(d["path"]) for u, v, d in mst_edges)

        # T: final Steiner tree
        T = self.nx_graph.edge_subgraph(edges)

        return T


def shortest_path_internal_caching(
    graph: nx.Graph,
    source: TileName,
    target: TileName,
    sp_caching: spc.SPCaching | None = None,
) -> tuple[float | int, list[AdjGraphNode]]:
    (length, path) = (None, None)
    if sp_caching:
        spp_res_by_cache = sp_caching.query_spp_cache(source, target, graph)
        if spp_res_by_cache:
            (length, path) = spp_res_by_cache[1]
        else:
            # find shortest path between source and target nodes
            length, path = nx.bidirectional_dijkstra(
                graph, source, target=target, weight="weight"
            )
            path = cast(list[AdjGraphNode], path)
            sp_caching.add_spp_cache(source, target, (length, path))
    else:
        (length, path) = nx.bidirectional_dijkstra(
            graph, source, target=target, weight="weight"
        )
    path = cast(
        list[AdjGraphNode], path
    )  # can be removed once caching has type annotations
    return length, path
