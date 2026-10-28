"""Deterministic combinational netlist simulation and fault injection.

Scope: zero-delay, two-state Boolean logic. No X/Z propagation, timing, or analog effects.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from itertools import product, combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import time

OPS = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "BUF"}
MUTATIONS = {
    "AND": ("NAND", "OR", "XOR"),
    "OR": ("NOR", "AND", "XOR"),
    "XOR": ("XNOR", "OR", "AND"),
    "NAND": ("AND", "NOR", "OR"),
    "NOR": ("OR", "NAND", "AND"),
    "XNOR": ("XOR", "AND", "OR"),
    "NOT": ("BUF",),
    "BUF": ("NOT",),
}

@dataclass(frozen=True)
class Gate:
    name: str
    op: str
    inputs: Tuple[str, ...]

@dataclass(frozen=True)
class Fault:
    kind: str                    # stuck_at, mutation, bridge_and, bridge_or
    node: Optional[str] = None
    value: Optional[int] = None
    replacement: Optional[str] = None
    nodes: Optional[Tuple[str, str]] = None

    def label(self) -> str:
        if self.kind == "stuck_at":
            return f"{self.node} SA{self.value}"
        if self.kind == "mutation":
            return f"{self.node}: {self.replacement}"
        if self.kind in ("bridge_and", "bridge_or"):
            op = "AND-bridge" if self.kind == "bridge_and" else "OR-bridge"
            return f"{op}({self.nodes[0]}, {self.nodes[1]})"
        return self.kind

class Circuit:
    def __init__(self, name: str, inputs: Sequence[str], gates: Sequence[Gate],
                 outputs: Dict[str, str]):
        self.name = name
        self.inputs = tuple(inputs)
        self.gates = tuple(gates)
        self.outputs = dict(outputs)
        self._validate_and_sort()

    def _validate_and_sort(self):
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("Duplicate primary input names")
        if set(self.inputs) & {g.name for g in self.gates}:
            raise ValueError("Gate output names must not collide with primary inputs")
        names = set(self.inputs)
        pending = list(self.gates)
        ordered = []
        while pending:
            progressed = False
            for gate in pending[:]:
                if gate.op not in OPS:
                    raise ValueError(f"Unsupported gate operation {gate.op!r}")
                expected = 1 if gate.op in ("NOT", "BUF") else 2
                if len(gate.inputs) != expected:
                    raise ValueError(f"{gate.name}: {gate.op} requires {expected} input(s)")
                if all(x in names for x in gate.inputs):
                    if gate.name in names:
                        raise ValueError(f"Duplicate signal name {gate.name}")
                    ordered.append(gate)
                    names.add(gate.name)
                    pending.remove(gate)
                    progressed = True
            if not progressed:
                unresolved = {g.name: g.inputs for g in pending}
                raise ValueError(f"Netlist has unknown inputs or a combinational cycle: {unresolved}")
        if not self.outputs:
            raise ValueError("At least one primary output is required")
        for out, node in self.outputs.items():
            if node not in names:
                raise ValueError(f"Output {out} references unknown signal {node}")
        self.gates = tuple(ordered)
        self.nodes = tuple(self.inputs) + tuple(g.name for g in self.gates)
        self.gate_by_name = {g.name: g for g in self.gates}

    def clone(self):
        return Circuit(self.name, self.inputs, self.gates, self.outputs)

    def evaluate(self, vector: Dict[str, int], fault: Optional[Fault] = None):
        missing = set(self.inputs) - set(vector)
        extra = set(vector) - set(self.inputs)
        if missing or extra:
            raise ValueError(f"Input vector mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
        values = {}
        for name in self.inputs:
            bit = int(vector[name])
            if bit not in (0, 1):
                raise ValueError(f"Input {name} must be 0 or 1")
            values[name] = bit
        if fault and fault.kind == "stuck_at" and fault.node in self.inputs:
            values[fault.node] = int(fault.value)
        mutation = fault if fault and fault.kind == "mutation" else None
        # Bridge faults are applied as a deterministic short model: compute the
        # unbridged values, combine the two nodes, then re-evaluate with both
        # nodes forced to the combined value. Candidate bridge nodes are required
        # to be independent (neither is an ancestor of the other).
        if fault and fault.kind in ("bridge_and", "bridge_or"):
            base = self._evaluate_once(values, None, None)
            a, b = fault.nodes
            if a not in base or b not in base:
                raise ValueError("Bridge references an unknown signal")
            shared = (base[a] & base[b]) if fault.kind == "bridge_and" else (base[a] | base[b])
            values2 = {k: v for k, v in values.items()}
            forced = {a: shared, b: shared}
            for node in (a, b):
                if node in self.inputs:
                    values2[node] = shared
            result = self._evaluate_once(values2, None, forced)
            return {out: result[node] for out, node in self.outputs.items()}, result
        forced = {}
        if fault and fault.kind == "stuck_at" and fault.node not in self.inputs:
            if fault.node not in self.nodes:
                raise ValueError(f"Unknown stuck-at node: {fault.node}")
            forced[fault.node] = int(fault.value)
        result = self._evaluate_once(values, mutation, forced)
        return {out: result[node] for out, node in self.outputs.items()}, result

    def _evaluate_once(self, values, mutation=None, forced=None):
        forced = forced or {}
        vals = dict(values)
        for gate in self.gates:
            op = gate.op
            if mutation and mutation.node == gate.name:
                op = mutation.replacement
                if op not in OPS:
                    raise ValueError(f"Unsupported replacement operation {op}")
            x = [vals[n] for n in gate.inputs]
            if op == "AND": y = x[0] & x[1]
            elif op == "OR": y = x[0] | x[1]
            elif op == "XOR": y = x[0] ^ x[1]
            elif op == "NAND": y = 1 - (x[0] & x[1])
            elif op == "NOR": y = 1 - (x[0] | x[1])
            elif op == "XNOR": y = 1 - (x[0] ^ x[1])
            elif op == "NOT": y = 1 - x[0]
            elif op == "BUF": y = x[0]
            else: raise ValueError(f"Unsupported operation {op}")
            vals[gate.name] = int(forced[gate.name]) if gate.name in forced else y
        return vals

    def vectors(self):
        for bits in product((0, 1), repeat=len(self.inputs)):
            yield dict(zip(self.inputs, bits))

    def truth_table(self, fault=None):
        rows = []
        for vec in self.vectors():
            outs, nodes = self.evaluate(vec, fault)
            rows.append({**vec, **{f"GOLDEN_{k}": v for k, v in self.evaluate(vec)[0].items()},
                         **{f"ACTUAL_{k}": v for k, v in outs.items()},
                         "MISMATCH": int(any(outs[k] != self.evaluate(vec)[0][k] for k in outs))})
        return rows

    def all_faults(self, include_bridges=True):
        faults = []
        for node in self.nodes:
            faults.extend((Fault("stuck_at", node=node, value=0),
                           Fault("stuck_at", node=node, value=1)))
        for gate in self.gates:
            for op in MUTATIONS.get(gate.op, ()):
                if op != gate.op:
                    faults.append(Fault("mutation", node=gate.name, replacement=op))
        if include_bridges:
            # Keep only pairs that are independent in the dataflow graph.
            ancestors = self.ancestors()
            for a, b in combinations(self.nodes, 2):
                if a in self.inputs and b in self.inputs:
                    pass
                if a in ancestors.get(b, set()) or b in ancestors.get(a, set()):
                    continue
                for kind in ("bridge_and", "bridge_or"):
                    faults.append(Fault(kind, nodes=(a, b)))
        return faults

    def ancestors(self):
        direct = {g.name: set(g.inputs) for g in self.gates}
        result = {}
        for node in self.nodes:
            seen, stack = set(), list(direct.get(node, ()))
            while stack:
                cur = stack.pop()
                if cur not in seen:
                    seen.add(cur)
                    stack.extend(direct.get(cur, ()))
            result[node] = seen
        return result

def make_circuit(name: str) -> Circuit:
    key = name.strip().lower().replace("-", "").replace(" ", "")
    if key in ("fulladder", "1bitfulladder", "fa"):
        gates = [
            Gate("XOR1", "XOR", ("A", "B")),
            Gate("SUM", "XOR", ("XOR1", "Cin")),
            Gate("AND1", "AND", ("A", "B")),
            Gate("AND2", "AND", ("XOR1", "Cin")),
            Gate("COUT", "OR", ("AND1", "AND2")),
        ]
        return Circuit("1-bit Full Adder", ("A", "B", "Cin"), gates, {"Sum": "SUM", "Cout": "COUT"})
    if key in ("ripplecarryadder", "4bitripplecarryadder", "rca4", "rca"):
        gates = []
        inputs = tuple([f"A{i}" for i in range(4)] + [f"B{i}" for i in range(4)] + ["Cin"])
        carry = "Cin"
        for i in range(4):
            gates += [
                Gate(f"XOR1_{i}", "XOR", (f"A{i}", f"B{i}")),
                Gate(f"SUM_{i}", "XOR", (f"XOR1_{i}", carry)),
                Gate(f"AND1_{i}", "AND", (f"A{i}", f"B{i}")),
                Gate(f"AND2_{i}", "AND", (f"XOR1_{i}", carry)),
                Gate(f"COUT_{i}", "OR", (f"AND1_{i}", f"AND2_{i}")),
            ]
            carry = f"COUT_{i}"
        outputs = {f"Sum{i}": f"SUM_{i}" for i in range(4)}
        outputs["Cout"] = carry
        return Circuit("4-bit Ripple Carry Adder", inputs, gates, outputs)
    if key in ("mux4to1", "4to1mux", "4x1mux", "4:1mux", "mux"):
        gates = [
            Gate("NS0", "NOT", ("S0",)), Gate("NS1", "NOT", ("S1",)),
            Gate("T0", "AND", ("D0", "NS0")), Gate("T1", "AND", ("D1", "S0")),
            Gate("L0", "OR", ("T0", "T1")),
            Gate("T2", "AND", ("D2", "NS0")), Gate("T3", "AND", ("D3", "S0")),
            Gate("L1", "OR", ("T2", "T3")),
            Gate("SEL0", "AND", ("L0", "NS1")), Gate("SEL1", "AND", ("L1", "S1")),
            Gate("Y", "OR", ("SEL0", "SEL1")),
        ]
        return Circuit("4:1 Multiplexer", ("D0", "D1", "D2", "D3", "S0", "S1"),
                       gates, {"Y": "Y"})
    raise ValueError("Unsupported circuit. Choose Full Adder, 4-bit Ripple Carry Adder, or 4:1 MUX.")
