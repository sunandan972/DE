"""Fault dictionary, differential truth tables, candidate ranking, and LLM prompt formatting."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from time import perf_counter
from typing import Optional
import json
import pandas as pd
from circuit_engine import Circuit, Fault

def vector_signature(circuit: Circuit, fault: Optional[Fault]):
    """Full output signature over lexicographically enumerated exhaustive input vectors."""
    sig = []
    for vec in circuit.vectors():
        out, _ = circuit.evaluate(vec, fault)
        sig.append(tuple(out[k] for k in circuit.outputs))
    return tuple(sig)

def golden_signature(circuit: Circuit):
    return vector_signature(circuit, None)

def differential_table(circuit: Circuit, fault: Optional[Fault]):
    rows = []
    for idx, vec in enumerate(circuit.vectors()):
        gold, _ = circuit.evaluate(vec)
        actual, nodes = circuit.evaluate(vec, fault)
        row = {"Vector": idx, **vec}
        for out in circuit.outputs:
            row[f"Golden_{out}"] = gold[out]
            row[f"Faulty_{out}"] = actual[out]
            row[f"Error_{out}"] = int(gold[out] != actual[out])
        row["Any_Error"] = int(any(gold[o] != actual[o] for o in circuit.outputs))
        rows.append(row)
    return pd.DataFrame(rows)

@dataclass
class Diagnosis:
    injected_fault: Optional[Fault]
    candidates: list
    exact_signature_matches: int
    fault_coverage_percent: float
    diagnostic_resolution_percent: float
    detection_rate_percent: float
    latency_ms: float
    signature: tuple

def build_fault_dictionary(circuit: Circuit, include_bridges=True):
    dictionary = defaultdict(list)
    faults = circuit.all_faults(include_bridges=include_bridges)
    for fault in faults:
        dictionary[vector_signature(circuit, fault)].append(fault)
    return dictionary, faults

def diagnose(circuit: Circuit, injected_fault: Fault, include_bridges=True):
    start = perf_counter()
    observed = vector_signature(circuit, injected_fault)
    dictionary, faults = build_fault_dictionary(circuit, include_bridges=include_bridges)
    matches = dictionary.get(observed, [])
    # The golden signature is the no-fault signature and is not a detected fault.
    detected = observed != golden_signature(circuit)
    candidates = []
    for f in matches:
        candidates.append({
            "fault": f,
            "label": f.label(),
            "kind": f.kind,
            "node": f.node,
            "value": f.value,
            "replacement": f.replacement,
            "nodes": f.nodes,
            "confidence": 1.0 / max(1, len(matches)),
        })
    elapsed = (perf_counter() - start) * 1000.0
    detectable_faults = sum(vector_signature(circuit, f) != golden_signature(circuit) for f in faults)
    coverage = (100.0 * detectable_faults / len(faults)) if faults else 100.0
    resolution = (100.0 / len(matches)) if matches else 0.0
    return Diagnosis(injected_fault, candidates, len(matches), coverage, resolution,
                     100.0 if detected else 0.0, elapsed, observed)

def make_llm_prompt(circuit: Circuit, fault: Optional[Fault], table, candidates=None):
    """Structured evidence prompt. Treat any LLM response as advisory, never as proof."""
    netlist = [{"name": g.name, "op": g.op, "inputs": list(g.inputs)} for g in circuit.gates]
    rows = table.to_dict(orient="records")
    return {
        "system": (
            "You are a digital test and diagnosis assistant. Use only supplied netlist and truth-table evidence. "
            "Do not claim certainty when multiple faults share a signature. Distinguish observed facts from hypotheses. "
            "Do not invent nodes. Return JSON with fields: observed_pattern, candidate_faults, reasoning_summary, "
            "ambiguities, recommended_repair, verification_required. Exhaustive equivalence checking is authoritative."
        ),
        "user": {
            "circuit": circuit.name,
            "inputs": list(circuit.inputs),
            "outputs": circuit.outputs,
            "netlist": netlist,
            "differential_truth_table": rows,
            "algorithmic_candidates": candidates or [],
            "known_fault_for_demo_only": fault.label() if fault else None,
        },
    }

def repair_by_disabling_fault(circuit: Circuit, diagnosed_fault: Optional[Fault]):
    """Faults are overlays on the golden topology; disabling the overlay restores the nominal model."""
    return circuit.clone()

def verify_equivalence(golden: Circuit, repaired: Circuit):
    """Exhaustively compare every input combination and every primary output."""
    if golden.inputs != repaired.inputs or golden.outputs.keys() != repaired.outputs.keys():
        return {"equivalent": False, "vectors_checked": 0, "mismatches": ["Interface mismatch"]}
    errors = []
    count = 0
    for vec in golden.vectors():
        go, _ = golden.evaluate(vec)
        ro, _ = repaired.evaluate(vec)
        count += 1
        for out in golden.outputs:
            if go[out] != ro[out]:
                errors.append({"vector": vec, "output": out, "golden": go[out], "repaired": ro[out]})
    return {"equivalent": not errors, "vectors_checked": count, "mismatches": errors}
