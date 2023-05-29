"""This file simulates the magic state distillation and consumption process using Simpy
for a specific quantum chip layout with three blocks:
    - Distillation: Magic state factories following a distillation protocol
    - Storage: Magic state depots where newly distilled magic states are stored
    - Data: Space where the quantum data is processed using the magic states stored
"""
import configparser
import math
import os
import random
import string
from dataclasses import dataclass

import networkx as nx
import numpy as np
import simpy
import hla_scheduler.scheduler_sampler as ss
import scheduler.dependency_graph as dp
from scheduler.circuit_and_rotation import circuit
from scheduler.circuit_and_rotation import generate_rotation as m
from layout_processor.adjacency_graph import AdjacencyGraph
import layout_processor.magic_state_factory as msf
import scheduler.data_qubit_assignment as qa
from layout_processor.adjacency_graph import AdjacencyGraph, ComponentType

# Read from config file
config = configparser.ConfigParser()
config.read_file(open("src/config/scheduler.conf"))


def TruncatedNormal(mean, stddev, low, high):
    """Return a sample from a truncated normal distribution"""
    number = low - 1
    while number < low or number > high:
        number = round(np.random.normal(mean, stddev))
    return number


class Circuit:
    pi8: int  # nb of PI8 rotations in the circuit
    pi4: int  # nb of PI4 rotations in the circuit
    measurements: int  # nb of measurements in the circuit (must be equal to nb_qubits)
    rotations: list[m.Rotation]
    trans_cir: circuit.Circuit
    blockers_dict: dict[int, set]
    dependency_graph: nx.DiGraph
    name: str

    def __init__(self, pi8=0, pi4=0, measurements=0):
        self.pi8 = pi8
        self.pi4 = pi4
        self.measurements = measurements
        assert pi4 == 0, f"HLAScheduler requires no PI4"

    @property
    def nb_qubits(self):
        """Number of qubits in the circuit"""
        return self.measurements

    @property
    def total_operations(self):
        """Total number of operations in the circuit"""
        return self.pi8 + self.pi4 + self.measurements

    def read_circuit(self, circuit_dir):
        """Read input circuit from external file"""
        self.name = os.path.basename(circuit_dir)
        self.trans_cir = m.parse_rotations(circuit_dir=circuit_dir, split_y=False)

    def process_circuit(self, adj_graph):
        """Process circuit to convert Y operator, add qubit tile turning, and build a dependency graph"""
        # solve data qubit assignment problem
        _, non_corner_patches = qa.solve_data_qubit_assignment(
            self.trans_cir, adj_graph, policy=qa.AssignPolicy.RANDOM
        )
        self.trans_cir = m.convert_Y_operators(self.trans_cir, non_corner_patches)
        self.trans_cir.add_turn_qubits(adj_graph.qubit_angle)
        self.pi8 = len(self.trans_cir.inds_pi8_rots)
        self.pi4 = len(self.trans_cir.inds_pi4_rots)
        self.measurements = len(self.trans_cir.inds_meas)
        self.rotations = self.trans_cir.rotations
        self.blockers_dict, self.dependency_graph = self.get_dependency_graph()

    # TODO check for circuit "parallelibility" by generating its dependency graph
    def get_dependency_graph(self):
        dep_graph = dp.DependencyGraphTrivialCommute(self.trans_cir)
        _, _, blockers_dict = dep_graph.get_dependency_graph()
        nx_graph = dep_graph.get_dependency_graph_nx(blockers_dict)
        return blockers_dict, nx_graph

    # TODO suggest to compile the circuit or get an estimation based on the circuit "parallelibility"
    def is_parallelizable(self):
        pass

    # TODO get nb rotations in each depth of the dependency graph (e.g., [2,2,1,1,2,1,1] for 10 rotations)
    # TODO then, in each time step we can schedule up to that number of rotations to simulate a process with parallelization
    def get_rotations_per_depth(self):
        pass


@dataclass
class DistillationProtocol:
    """Parameters of the distillation protocol used by the magic state factories

    e.g.:
        - 20:4 protocol: (3,20,4)
        - 15:1 protocol: (4,15,1)
    """

    # TODO the distillation protocol can be either a user input or a suggestion based on the circuit input
    protocol: string
    m_x: int  # nb factory data qubits (X_stabilizers)
    n: int  # nb lower-fidelity magic states (Z_operators)
    k: int  # nb distillation ports (X_logical_operators)

    #! according to Litinksi, the distillation protocol should minimize the following equation:
    #! min ( (qubits_per_factory * time_steps_to_distill) / (X_logical_operators * success_probability) ) * code_distance^3

    @property
    def t(self):
        # nb time steps to distill higher-fidelity magic states
        return self.n - self.m_x

    @property
    # TODO
    def output_fidelity(self):
        """Probability of a faulty higher-fidelity magic state distilled in a factory with this protocol"""
        # 15-to-1: 35p^3
        # 20-to-4: 22p^2
        # TODO search for the right formula to implement here...
        return 0


class DistillationFactory:
    """A magic state factory distills 'protocol.k' magic states every 'protocol.t' time steps with a success rate of 'p'"""

    id: int  # factory id
    protocol: DistillationProtocol  # distillation protocol used by this factory
    success_rate: float  # probability of a distillation process being successfull
    stats: dict  # stats for the factory during the simulation
    pi8_min_time: int  # minimum time to run a PI8 rotation when distilling
    pi8_max_time: int  # maximum time to run a PI8 rotation when distilling

    def __init__(self, id, protocol, physical_qubit_error_rate: float):
        self.id = id
        self.protocol = protocol
        self.success_rate = math.pow(
            1 - physical_qubit_error_rate, protocol.t + protocol.m_x
        )
        self.stats = {"success": 0, "fail": 0}
        self.pi8_min_time = 1
        self.pi8_max_time = 2
        if config["Experiments"]["pi8_time"] == "Fixed":
            self.pi8_max_time = 1
        assert self.pi8_min_time <= self.pi8_max_time

    def get_nb_logical_qubits(self):
        """Optimal number of qubits in this factory"""
        # Litinksi's layout (not always ideal)
        return math.ceil(1.5 * (self.protocol.m_x + self.protocol.k)) + 4

    def distill(
        self,
        env: simpy.Environment,
        depot: simpy.Container,
        input_depot: simpy.Resource,
        print_simulation="none",
    ):
        """Process to distill magic states in the factory
        Args:
            env: the simpy environment
            depot: the container which describes the storage area
            input_depot: the resource that specifies the depot entry
            print_simulation: switch for printing details
        """
        while True:
            # time to distill new magic states in a factory
            if self.pi8_min_time != self.pi8_max_time:
                producing_time = TruncatedNormal(
                    self.protocol.t * (self.pi8_min_time + self.pi8_max_time) / 2,
                    math.sqrt(
                        self.protocol.t
                        * (
                            math.pow(self.pi8_min_time, 2)
                            + math.pow(self.pi8_max_time, 2)
                        )
                        / 12
                    ),
                    self.protocol.t,
                    2 * self.protocol.t,
                )
            else:
                producing_time = self.protocol.t
            yield env.timeout(producing_time)

            # check for distillation process success
            if random.random() < self.success_rate:
                self.stats["success"] += 1
                if print_simulation == "full":
                    print(
                        f"Magic state factory {self.id+1} distilled {self.protocol.k} magic states at time step {env.now}"
                    )

                # store magic states distilled
                send = [
                    env.process(
                        self.store(env, depot, input_depot, ms_id, print_simulation)
                    )
                    for ms_id in range(self.protocol.k)
                ]
                yield simpy.events.AllOf(env, send)
            else:
                self.stats["fail"] += 1
                if print_simulation == "full":
                    print(f"Magic state factory {self.id+1} failed")

    def store(
        self,
        env: simpy.Environment,
        depot: simpy.Container,
        input_depot: simpy.Resource,
        ms_id: int,
        print_simulation="none",
    ):
        """Process to send each magic state distilled to depot"""
        if depot.level == depot.capacity:
            # when the depot is full, wait for a tick
            yield env.timeout(1)
        else:
            with input_depot.request() as req:
                # send magic state from distillation port to depot
                yield req
                yield env.timeout(1)

        # storage preparation time
        yield env.timeout(1)
        yield depot.put(1)

        if print_simulation == "full":
            print(
                f"Magic state {ms_id+1} from factory {self.id+1} is ready to be consumed at time step {env.now} - Storage level: {depot.level}"
            )


class DistillationBlock:
    """Parameters of the distillation block"""

    nb_factories: int  # nb distillation factories
    factories: list[DistillationFactory]  # list of factories

    def __init__(
        self,
        nb_factories,
        protocol,
        physical_qubit_error_rate,
        depot_in,
        depot_out,
        data_pi8_min_time,
        data_pi8_max_time,
    ):
        # create first factory
        self.factories = [
            DistillationFactory(
                id=1,
                protocol=protocol,
                physical_qubit_error_rate=physical_qubit_error_rate,
            )
        ]

        # if no nb_factories is provided and we will simulate a serial scheduling,
        # we will suggest the number of factories to use
        if nb_factories == None:
            assert (
                depot_out == 1
            ), "Invalid number of factories input for non-serial scheduling"
            # calculate the optimal number of factories
            nb_factories = self.get_opt_nb_factories_serial(
                protocol.t,
                protocol.k,
                math.pow(1 - physical_qubit_error_rate, protocol.t + protocol.m_x),
                depot_in,
                self.factories[0].pi8_min_time,
                self.factories[0].pi8_max_time,
                data_pi8_min_time,
                data_pi8_max_time,
            )

        self.nb_factories = nb_factories

        for fac_id in range(nb_factories - 1):
            self.factories.append(
                DistillationFactory(
                    id=fac_id + 2,
                    protocol=protocol,
                    physical_qubit_error_rate=physical_qubit_error_rate,
                )
            )

    def get_opt_nb_factories_serial(
        self,
        T,  # nb time steps to distill magic states in a factory
        M,  # nb magic states distill each distillation process
        P,  # distillation success rate
        D,  # nb entry points to storage block
        min_time_distil,
        max_time_distil,
        min_time_data,
        max_time_data,
    ) -> int:
        """
        Get the number of factories that leads to approx. equal consumption and distillation rate
        in a serial scheduling given that all factories follow the same distillation protocol.
        Overall, there is a trade-off between the nb. of factories and the estimated computation time.
        This can be used as a guide when these assumptions are relaxed.
        """
        avg_distillation_time = T * ((min_time_distil + max_time_distil) / 2)
        distillation_cycle_time = avg_distillation_time + math.ceil(M / D)
        ms_consumption_capacity = 1 / (
            (min_time_data + max_time_data) / 2
        )  # TODO for a parallel scheduling
        opt_nb_factories = math.ceil(
            (distillation_cycle_time / (P * M)) * ms_consumption_capacity
        )
        return opt_nb_factories

    def get_nb_logical_qubits(self, storage_nb_entry):
        """Total number of logical qubits in the distillation block"""
        total_nb_logical_qubits = 0

        for fac in self.factories:
            # logical qubits in the factories
            total_nb_logical_qubits += fac.get_nb_logical_qubits()

            # logical qubits to connect the factories to the storage
            total_nb_logical_qubits += fac.protocol.k * storage_nb_entry

        return total_nb_logical_qubits


class StorageBlock:
    """Parameters of the magic state storage block"""

    nb_entry: int  # number of entry points to the depot
    nb_exit: int  # number of exit points from the depot
    # TODO capacity should have a suggested value (still under investigation...)
    capacity: int  # number of storage qubits

    def __init__(self, capacity, nb_entry=1, nb_exit=1):
        self.nb_entry = nb_entry
        self.nb_exit = nb_exit
        self.capacity = capacity

    def get_nb_logical_qubits(self):
        """Total number of logical qubits in the storage block"""
        return 5 * (math.ceil(self.capacity / 2) + 2) + 2


class DataBlock:
    """Parameters of the data block"""

    nb_data_qubits: int  # number of data qubits in the memory fabric
    nb_bus_qubits: int  # number of bus qubits in the memory fabric
    pi8_min_time: int  # minimum time to run a PI8
    pi8_max_time: int  # maximum time to run a PI8
    all_rotations: list[
        m.Rotation
    ]  # the list of all the rotations in the order of the rotation ids

    def __init__(self, nb_data_qubits, nb_bus_qubits, circuit: Circuit):
        self.all_rotations = circuit.rotations
        self.nb_data_qubits = nb_data_qubits
        self.nb_bus_qubits = nb_bus_qubits
        self.pi8_min_time = 1
        self.pi8_max_time = 2
        if config["Experiments"]["pi8_time"] == "Fixed":
            self.pi8_max_time = 1
        assert self.pi8_min_time <= self.pi8_max_time

    def get_nb_logical_qubits(self):
        """Total number of logical qubits in the data block"""
        return self.nb_bus_qubits + self.nb_data_qubits

    def parallel_consume(
        self,
        env: simpy.Environment,
        sampler: ss.ScheduleSampler,
        depot: simpy.Container,
        output_depot: simpy.Resource,
        parallel_rs: simpy.Resource,
        rotation_scheduling: dict[int, list[int]],
        print_simulation: str = "none",
    ):
        """This is a generators which iteratively yield event which is triggered only all
        the parallized rotations are completed (yield simpy.events.AllOf(env, parallelizable_event)).
        The while loop is broken when there is no rotation left in the sampler (more specifically,
        when the adj graph does not have any node).
        Args:
            parallel_rs: an auxiliary simpy resource to grant an opportunity for
                the scheduler to parallize multiple rotations. This can prevent the following
                case from happening. Let's say we have four parallizable rotations ABCD.
                But there are only two buffers in the layout, so it should take 2 tics to complete
                them, which could be tic 1: (AB); tic 2: (CD). But without the resource, (AB) and (CD)
                would be performed at the same time, which results in 1 tic. So basically the opportunity of
                running multiple rotaitons in paralllel is also a resource. It is always assumed to be 1.

        """
        while sampler.any_rotation_left():
            # decide if we need to wait for another tic for magic states being replenished
            with parallel_rs.request() as req:
                yield req
                parallelizable_event = (
                    []
                )  # a list of event of operate_pi8 or operate_non_pi8
                rotations = sampler.sample(depot, output_depot)
                if len(rotations) == 0:
                    # if there is no rotation given by the sampler
                    # it means that no rotation can be scheduled at this tick due to
                    # lack of magic states so wait for 1 tick for replenishment
                    yield env.timeout(1)
                else:
                    rotation_scheduling[env.now] = rotations
                    if print_simulation == "full":
                        print(f"Rotations {rotations} are scheduled at tick {env.now}")
                    for rot_id in rotations:
                        # if it's a pi8 rotation append the event to the event list
                        if self.all_rotations[rot_id].operation_type == 1:
                            parallelizable_event.append(
                                env.process(
                                    self.operate_pi8(
                                        env,
                                        depot,
                                        output_depot,
                                        rot_id,
                                        print_simulation,
                                    )
                                )
                            )
                        else:
                            # else for a non-pi8 rotation
                            parallelizable_event.append(
                                env.process(
                                    self.operate_non_pi8(env, rot_id, print_simulation)
                                )
                            )
                    # generate an event which is triggered only all the event in the list are triggered
                    # because we can only move on when all the parallized rotations are finished
                    yield simpy.events.AllOf(env, parallelizable_event)

    def operate_non_pi8(
        self, env: simpy.Environment, rot_id: int, print_simulation="none"
    ):
        """
        the function takes a non-pi8 rotation and consume either a zero state or nothing.
        It always takes 1 tick to perform the rotation.
        """
        if print_simulation == "full":
            print(f"Rotation {rot_id} starts to be operated at time step {env.now}")
        yield env.timeout(1)

    def operate_pi8(
        self,
        env: simpy.Environment,
        depot: simpy.Container,
        output_depot: simpy.Resource,
        rot_id: int,
        print_simulation="none",
    ):
        """
        The function takes a pi8 rotation and consume one magic state.
        A pi8 rotation consumes one magic state every one or two time steps

        """
        with output_depot.request() as req:
            yield req
            yield depot.get(1)
            if print_simulation == "full":
                print(
                    f"Rotation {rot_id} start to consume a magic state at time step {env.now}"
                )
            yield env.timeout(random.randint(self.pi8_min_time, self.pi8_max_time))


class QuantumSystem:
    """Parameters of the quantum system (chip and circuit)"""

    circuit: Circuit
    physical_error: float
    distillation: DistillationBlock
    storage: StorageBlock
    data: DataBlock
    env: simpy.Environment()
    nb_runs: int
    adj_graph: AdjacencyGraph
    ms_fact: msf.MagicStateFactory
    scheduling_rotations: dict[int, list[int]]

    def __init__(
        self,
        circuit,
        adj_graph,
        ms_fact,
        distillation_protocol="20:4",
        physical_qubit_error_rate=0.001,
        depot_capacity=2,
        nb_factories=None,
        depot_entries=1,
        depot_exits=1,
    ) -> None:
        """
        Initialize the quantum system (chip and circuit)

        circuit: Circuit class containing the dependency graph and other info about the circuit
        distillation_protocol: magic state factory distillation protocol
        physical_qubit_error_rate: physical qubit error rate
        depot_capacity: number of magic state storage qubits in the storage block
        nb_factories: number of magic state factories in the distillation block
        depot_entries: number of distillation-storage blocks connections
        depot_exits: number of data-storage blocks connections (1 for serial scheduling)
        """

        # save circuit
        self.circuit = circuit

        # save adj graph
        self.adj_graph = adj_graph

        # assign the magic state factory
        self.ms_fact = ms_fact

        self.physical_error = physical_qubit_error_rate

        self.scheduling_rotations = dict()

        # 20-to-4 distillation protocol
        if distillation_protocol == "20:4":
            protocol = DistillationProtocol("20:4", 3, 20, 4)
        elif distillation_protocol == "15:1":
            protocol = DistillationProtocol("15:1", 4, 15, 1)

        self.data = DataBlock(
            nb_data_qubits=self.adj_graph.layout.n_qubits,
            nb_bus_qubits=self.adj_graph.layout.n_bus,
            circuit=self.circuit,
        )

        self.storage = StorageBlock(
            capacity=depot_capacity, nb_entry=depot_entries, nb_exit=depot_exits
        )

        self.distillation = DistillationBlock(
            nb_factories=nb_factories,
            protocol=protocol,
            physical_qubit_error_rate=self.physical_error,
            depot_in=depot_entries,
            depot_out=depot_exits,
            data_pi8_min_time=self.data.pi8_min_time,
            data_pi8_max_time=self.data.pi8_max_time,
        )
        self._validate_inputs()

    def get_nb_logical_qubits(self):
        return (
            self.distillation.get_nb_logical_qubits(self.storage.nb_entry)
            + self.storage.get_nb_logical_qubits()
            + self.data.get_nb_logical_qubits()
        )

    # TODO provide nb. physical qubits
    def get_nb_physical_qubits(self):
        pass

    def _validate_inputs(self):
        """Validate if the inputs are legal for the HLAScheduler to run
        1) Check if there are magic states in the default layout if there are pi8 rotations
        2) Check if there are zero states in the default layout if there are pi4 rotations
        """
        check_ms_exist_flag = self.circuit.pi8 == 0
        check_zs_exist_flag = self.circuit.pi4 == 0
        for rot in self.circuit.rotations:
            if check_zs_exist_flag and check_ms_exist_flag:
                break
            if not check_ms_exist_flag and rot.operation_type == 1:  # pi8
                # check any magic state exists
                assert len(self.adj_graph.get_nodes_of_type(ComponentType.MAGIC)) > 0
                check_ms_exist_flag = True
            if not check_zs_exist_flag and rot.operation_type == 2:  # pi4
                assert len(self.adj_graph.get_nodes_of_type(ComponentType.ZERO)) > 0
                check_ms_exist_flag = True
        print(f"The inputs for the HLAScheduler are valid")

    def simulate(self, nb_runs=1, print_simulation="none") -> int:
        self.nb_runs = nb_runs
        expected_runtime = 0
        # simulate nb_runs times
        for rep in range(nb_runs):
            # create simulation environment
            self.env = simpy.Environment()

            # generate depots
            depot = simpy.Container(self.env, capacity=self.storage.capacity, init=0)
            input_depot = simpy.Resource(self.env, capacity=self.storage.nb_entry)
            output_depot = simpy.Resource(self.env, capacity=self.storage.nb_exit)
            # utility resource
            parallel_oppo = simpy.Resource(self.env, capacity=1)

            # generate distill process for each factory
            for fac_id in range(self.distillation.nb_factories):
                self.env.process(
                    self.distillation.factories[fac_id].distill(
                        self.env, depot, input_depot, print_simulation=print_simulation
                    )
                )

            sampler = ss.ScheduleSampler(
                dep_graph=self.circuit.dependency_graph,
                trans_cir=self.circuit.trans_cir,
                adj_graph=self.adj_graph,
                ms_fact=self.ms_fact,
            )
            #  generate consume process
            last_pi8_event = self.env.process(
                self.data.parallel_consume(
                    self.env,
                    sampler,
                    depot,
                    output_depot,
                    parallel_oppo,
                    self.scheduling_rotations,
                    print_simulation,
                )
            )

            # run
            self.env.run(last_pi8_event)
            # print solution for this run
            if print_simulation == "per_run":
                print(f"Run {rep+1}: {self.env.now}")
            expected_runtime += self.env.now

        # return the expected quantum runtime
        return expected_runtime / nb_runs
