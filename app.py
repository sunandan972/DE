"""Streamlit dashboard for deterministic digital fault diagnosis and repair."""
import io
import json
import time
import pandas as pd
import streamlit as st
from circuit_engine import make_circuit, Fault, MUTATIONS
from fault_diagnostician import differential_table, diagnose, make_llm_prompt, verify_equivalence
from logisim_exporter import export_logisim

st.set_page_config(page_title="AI Circuit Fault Detection & Repair", layout="wide")
st.title("AI-Based Fault Detection, Diagnosis & Automated Circuit Repair")
st.caption("Deterministic Boolean simulation • Fault dictionary • Exhaustive repair verification")

circuit_name = st.sidebar.selectbox("Target circuit", ["Full Adder", "4-bit Ripple Carry Adder", "4:1 MUX"])
circuit = make_circuit(circuit_name)
fault_kind = st.sidebar.selectbox("Fault type", ["Stuck-at-0", "Stuck-at-1", "Gate mutation", "AND bridging", "OR bridging"])
node_options = list(circuit.nodes)
if fault_kind.startswith("Stuck"):
    node = st.sidebar.selectbox("Fault node", node_options, index=min(1, len(node_options)-1))
    fault = Fault("stuck_at", node=node, value=0 if fault_kind.endswith("0") else 1)
elif fault_kind == "Gate mutation":
    gate_names = [g.name for g in circuit.gates]
    node = st.sidebar.selectbox("Gate to mutate", gate_names)
    gate = circuit.gate_by_name[node]
    choices = [op for op in MUTATIONS[gate.op] if op != gate.op]
    replacement = st.sidebar.selectbox("Replacement operation", choices)
    fault = Fault("mutation", node=node, replacement=replacement)
else:
    # Restrict to independent signals, avoiding combinational feedback through a bridge.
    anc = circuit.ancestors()
    pairs = [(a,b) for i,a in enumerate(node_options) for b in node_options[i+1:]
             if a not in anc.get(b,set()) and b not in anc.get(a,set())]
    pair_label = st.sidebar.selectbox("Signals to bridge", [f"{a} ↔ {b}" for a,b in pairs])
    a,b = pair_label.split(" ↔ ")
    fault = Fault("bridge_and" if fault_kind == "AND bridging" else "bridge_or", nodes=(a,b))

st.sidebar.info(f"{len(circuit.inputs)} inputs → {2**len(circuit.inputs)} exhaustive vectors")
if st.sidebar.button("Run diagnosis and repair", type="primary"):
    started = time.perf_counter()
    table = differential_table(circuit, fault)
    result = diagnose(circuit, fault)
    repaired = circuit.clone()
    verification = verify_equivalence(circuit, repaired)
    elapsed = (time.perf_counter() - started) * 1000
    st.session_state["run"] = {
        "table": table, "result": result, "fault": fault,
        "verification": verification, "elapsed": elapsed,
        "prompt": make_llm_prompt(circuit, fault, table,
                                  [{"label": x["label"], "confidence": x["confidence"]} for x in result.candidates])
    }

if "run" in st.session_state:
    run = st.session_state["run"]
    table, result = run["table"], run["result"]
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Fault detected", "Yes" if result.detection_rate_percent else "No")
    m2.metric("Dictionary candidates", len(result.candidates))
    m3.metric("Diagnostic resolution", f"{result.diagnostic_resolution_percent:.1f}%")
    m4.metric("Analysis latency", f"{result.latency_ms:.1f} ms")
    st.subheader("Differential truth table")
    st.dataframe(table, use_container_width=True, height=350)
    st.download_button("Download differential CSV", table.to_csv(index=False).encode(), "differential_truth_table.csv", "text/csv")
    st.subheader("Fault diagnosis candidates")
    if result.candidates:
        st.dataframe(pd.DataFrame([{k:v for k,v in c.items() if k not in ("fault",)} for c in result.candidates]),
                     use_container_width=True)
        if len(result.candidates) > 1:
            st.warning("The observed signature is ambiguous: multiple modeled faults are observationally equivalent under exhaustive tests.")
    else:
        st.success("No non-equivalent fault signature matched; check whether the injected fault is masked or equivalent.")
    st.subheader("Repair and exhaustive equivalence")
    if run["verification"]["equivalent"]:
        st.success(f"PASS: repaired nominal model matches golden model on all {run['verification']['vectors_checked']} input vectors.")
    else:
        st.error(f"FAIL: {len(run['verification']['mismatches'])} mismatches found.")
    st.caption("Repair currently disables the fault overlay and restores the nominal netlist. This is appropriate for the simulator's injected-fault model; it is not a physical repair procedure.")
    st.subheader("LLM diagnostic prompt (optional)")
    st.code(json.dumps(run["prompt"], indent=2), language="json")
    st.download_button("Download structured LLM prompt", json.dumps(run["prompt"], indent=2), "diagnostic_prompt.json", "application/json")
    out1, out2 = st.columns(2)
    for col, filename, repaired_flag in [(out1,"faulty_circuit.circ",False),(out2,"repaired_circuit.circ",True)]:
        buf = io.BytesIO()
        export_logisim(circuit, "/tmp/"+filename, fault=run["fault"], repaired=repaired_flag)
        with open("/tmp/"+filename, "rb") as f: data=f.read()
        col.download_button(f"Download {filename}", data, filename, "application/xml")
    st.info("Logisim files are schematic scaffolds with labels; the exporter does not yet route and wire every net automatically. Inspect before using them as circuit evidence.")
else:
    st.markdown("### Quick start")
    st.write("Choose a circuit and fault in the sidebar, then run diagnosis. The tool enumerates all input combinations, compares golden and faulty outputs, matches the observed signature against a fault dictionary, and exhaustively verifies the repaired nominal model.")
    st.write("For a strict DFT flow, include additional constraints such as scan access, test-point insertion, unknown-state handling, physical adjacency data for bridging faults, and gate-level netlist import.")
