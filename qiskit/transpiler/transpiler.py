# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Tools for compiling a batch of quantum circuits."""
import logging
import warnings

from qiskit.circuit import QuantumCircuit
from qiskit.mapper import CouplingMap, swap_mapper
from qiskit.tools.parallel import parallel_map
from qiskit.converters import circuit_to_dag
from qiskit.converters import dag_to_circuit
from qiskit.extensions.standard import SwapGate
from qiskit.mapper.layout import Layout
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passes.unroller import Unroller

from .passes.cx_cancellation import CXCancellation
from .passes.decompose import Decompose
from .passes.optimize_1q_gates import Optimize1qGates
from .passes.dag_fixed_point import DAGFixedPoint
from .passes.mapping.barrier_before_final_measurements import BarrierBeforeFinalMeasurements
from .passes.mapping.check_cnot_direction import CheckCnotDirection
from .passes.mapping.cx_direction import CXDirection
from .passes.mapping.dense_layout import DenseLayout
from .passes.mapping.trivial_layout import TrivialLayout
from .passes.mapping.enlarge_with_ancilla import EnlargeWithAncilla
from .passes.mapping.extend_layout import ExtendLayout

from .exceptions import TranspilerError

logger = logging.getLogger(__name__)


def transpile(circuits, backend=None, basis_gates=None, coupling_map=None,
              initial_layout=None, seed_mapper=None, pass_manager=None):
    """transpile one or more circuits.

    Args:
        circuits (QuantumCircuit or list[QuantumCircuit]): circuits to compile
        backend (BaseBackend): a backend to compile for
        basis_gates (list[str]): list of basis gate names supported by the
            target. Default: ['u1','u2','u3','cx','id']
        coupling_map (list): coupling map (perhaps custom) to target in mapping
        initial_layout (list): initial layout of qubits in mapping
        seed_mapper (int): random seed for the swap_mapper
        pass_manager (PassManager): a pass_manager for the transpiler stages

    Returns:
        QuantumCircuit or list[QuantumCircuit]: transpiled circuit(s).

    Raises:
        TranspilerError: if args are not complete for the transpiler to function
    """
    return_form_is_single = False
    if isinstance(circuits, QuantumCircuit):
        circuits = [circuits]
        return_form_is_single = True

    # Check for valid parameters for the experiments.
    basis_gates = basis_gates or backend.configuration().basis_gates
    if coupling_map:
        coupling_map = coupling_map
    elif backend:
        # This needs to be removed once Aer 0.2 is out
        coupling_map = getattr(backend.configuration(), 'coupling_map', None)
    else:
        coupling_map = None

    if not basis_gates:
        raise TranspilerError('no basis_gates or backend to compile to')

    # Convert integer list format to Layout
    if isinstance(initial_layout, list) and \
            all(isinstance(elem, int) for elem in initial_layout):
        if isinstance(circuits, list):
            circ = circuits[0]
        else:
            circ = circuits
        initial_layout = Layout.generate_from_intlist(initial_layout, *circ.qregs)

    if initial_layout is not None and not isinstance(initial_layout, Layout):
        initial_layout = Layout(initial_layout)

    circuits = parallel_map(_transpilation, circuits,
                            task_kwargs={'basis_gates': basis_gates,
                                         'coupling_map': coupling_map,
                                         'initial_layout': initial_layout,
                                         'seed_mapper': seed_mapper,
                                         'pass_manager': pass_manager})
    if return_form_is_single:
        return circuits[0]
    return circuits


def _transpilation(circuit, basis_gates=None, coupling_map=None,
                   initial_layout=None, seed_mapper=None,
                   pass_manager=None):
    """Perform transpilation of a single circuit.

    Args:
        circuit (QuantumCircuit): A circuit to transpile.
        basis_gates (list[str]): list of basis gate names supported by the
            target. Default: ['u1','u2','u3','cx','id']
        coupling_map (list): coupling map (perhaps custom) to target in mapping
        initial_layout (list): initial layout of qubits in mapping
        seed_mapper (int): random seed for the swap_mapper
        pass_manager (PassManager): a pass_manager for the transpiler stage

    Returns:
        QuantumCircuit: A transpiled circuit.

    Raises:
        TranspilerError: if args are not complete for transpiler to function.
    """
    if pass_manager and not pass_manager.working_list:
        return circuit

    dag = circuit_to_dag(circuit)
    del circuit

    # pick a trivial layout if the circuit already satisfies the coupling constraints
    # else layout on the most densely connected physical qubit subset
    # FIXME: this should be simplified once it is ported to a PassManager
    if coupling_map and initial_layout is None:
        cm_object = CouplingMap(coupling_map)
        check_cnot_direction = CheckCnotDirection(cm_object)
        check_cnot_direction.run(dag)
        if check_cnot_direction.property_set['is_direction_mapped']:
            trivial_layout = TrivialLayout(cm_object)
            trivial_layout.run(dag)
            initial_layout = trivial_layout.property_set['layout']
        else:
            dense_layout = DenseLayout(cm_object)
            dense_layout.run(dag)
            initial_layout = dense_layout.property_set['layout']

    final_dag = transpile_dag(dag, basis_gates=basis_gates,
                              coupling_map=coupling_map,
                              initial_layout=initial_layout,
                              seed_mapper=seed_mapper,
                              pass_manager=pass_manager)

    out_circuit = dag_to_circuit(final_dag)

    return out_circuit


# pylint: disable=redefined-builtin
def transpile_dag(dag, basis_gates=None, coupling_map=None,
                  initial_layout=None, seed_mapper=None, pass_manager=None):
    """Transform a dag circuit into another dag circuit (transpile), through
    consecutive passes on the dag.

    Args:
        dag (DAGCircuit): dag circuit to transform via transpilation
        basis_gates (list[str]): list of basis gate names supported by the
            target. Default: ['u1','u2','u3','cx','id']
        coupling_map (list): A graph of coupling::

            [
             [control0(int), target0(int)],
             [control1(int), target1(int)],
            ]

            eg. [[0, 2], [1, 2], [1, 3], [3, 4]}

        initial_layout (Layout or None): A layout object
        seed_mapper (int): random seed_mapper for the swap mapper
        pass_manager (PassManager): pass manager instance for the transpilation process
            If None, a default set of passes are run.
            Otherwise, the passes defined in it will run.
            If contains no passes in it, no dag transformations occur.

    Returns:
        DAGCircuit: transformed dag
    """
    # TODO: `basis_gates` will be removed after we have the unroller pass.
    # TODO: `coupling_map`, `initial_layout`, `seed_mapper` removed after mapper pass.

    # TODO: move this to the mapper pass

    num_qubits = sum([qreg.size for qreg in dag.qregs.values()])
    if num_qubits == 1:
        coupling_map = None

    if basis_gates is None:
        basis_gates = ['u1', 'u2', 'u3', 'cx', 'id']
    if isinstance(basis_gates, str):
        warnings.warn("The parameter basis_gates is now a list of strings. "
                      "For example, this basis ['u1','u2','u3','cx'] should be used "
                      "instead of 'u1,u2,u3,cx'. The string format will be "
                      "removed after 0.9", DeprecationWarning, 2)
        basis_gates = basis_gates.split(',')

    if initial_layout is None:
        initial_layout = Layout.generate_trivial_layout(*dag.qregs.values())

    if pass_manager:
        # run the passes specified by the pass manager
        # TODO return the property set too. See #1086
        dag = pass_manager.run_passes(dag)
    else:
        # default set of passes
        # TODO: move each step here to a pass, and use a default passmanager below
        name = dag.name

        dag = Unroller(basis_gates).run(dag)
        dag = BarrierBeforeFinalMeasurements().run(dag)

        # if a coupling map is given compile to the map
        if coupling_map:
            logger.info("pre-mapping properties: %s",
                        dag.properties())

            coupling = CouplingMap(coupling_map)

            # Extend and enlarge the the dag/layout with ancillas using the full coupling map
            logger.info("initial layout: %s", initial_layout)
            pass_ = ExtendLayout(coupling)
            pass_.property_set['layout'] = initial_layout
            pass_.run(dag)
            initial_layout = pass_.property_set['layout']
            pass_ = EnlargeWithAncilla(initial_layout)
            dag = pass_.run(dag)
            initial_layout = pass_.property_set['layout']
            logger.info("initial layout (ancilla extended): %s", initial_layout)

            # temporarily build old-style layout dict
            # (TODO: remove after transition to StochasticSwap pass)
            virtual_qubits = initial_layout.get_virtual_bits()
            initial_layout = {(v[0].name, v[1]): ('q', initial_layout[v]) for v in virtual_qubits}

            # Swap mapper
            dag, final_layout = swap_mapper(
                dag, coupling, initial_layout, trials=20, seed=seed_mapper)
            logger.info("final layout: %s", final_layout)
            # Expand swaps
            dag = Decompose(SwapGate).run(dag)
            # Change cx directions
            dag = CXDirection(coupling).run(dag)
            # Unroll to the basis
            dag = Unroller(['u1', 'u2', 'u3', 'id', 'cx']).run(dag)

            # Simplify single qubit gates and CXs
            pm_4_optimization = PassManager()
            pm_4_optimization.append([Optimize1qGates(), CXCancellation(), DAGFixedPoint()],
                                     do_while=lambda property_set: not property_set[
                                         'dag_fixed_point'])
            dag = transpile_dag(dag, pass_manager=pm_4_optimization)

        dag.name = name

    return dag
