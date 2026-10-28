from __future__ import annotations
import json, os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sympy import symbols
from sympy.logic.boolalg import SOPform, POSform, simplify_logic
from nl_parser import DEMO_SCENARIOS, parse_natural_language, expression_to_sympy
from logic_engine import (build_truth_table, canonical_forms, minimize_function, verify_spec,
                          complexity_metrics, expression_to_verilog, variable_symbols)
from logisim_exporter import build_logisim_circuit

st.set_page_config(page_title="Natural Language → Logic Circuit", page_icon="⚡", layout="wide")
st.title("⚡ Natural Language to Logic Circuit Generator")
st.caption("Translate a decision rule into Boolean logic, inspect the truth table, simulate inputs, and export design artifacts.")
with st.sidebar:
    st.header("Configuration")
    use_llm=st.toggle("Use OpenAI parser", value=False, help="Requires OPENAI_API_KEY in the environment.")
    st.info("LLM output is treated as a draft specification and must pass validation and exhaustive logic checks.")
    st.markdown("**Pipeline**")
    st.markdown("1. Extract variables and rules\n2. Build truth table\n3. Minimize SOP/POS\n4. Verify all input states\n5. Export Verilog and Logisim")

tab_build, tab_demos, tab_help = st.tabs(["Build a circuit", "Demo scenarios", "Help & assumptions"])
with tab_build:
    default_text="The alarm triggers when both the key is valid and the code is correct, or when motion is detected while night mode is active."
    text=st.text_area("Describe the decision problem in plain English",value=default_text,height=120,
                      placeholder="Example: Enable the motor when the guard is closed AND start is pressed, unless emergency stop is active.")
    c1,c2=st.columns([1,3])
    with c1:
        parse_clicked=st.button("Extract logic specification",type="primary",use_container_width=True)
    with c2:
        st.caption("Offline mode supports the included demo patterns and explicit expressions such as `Y = (A AND B) OR NOT C`.")
    if parse_clicked:
        try:
            st.session_state["spec"]=parse_natural_language(text,use_llm=use_llm)
            st.session_state.pop("parse_error",None)
        except Exception as exc:
            st.session_state["parse_error"]=str(exc)
    if "parse_error" in st.session_state:
        st.error(st.session_state["parse_error"])
    if "spec" in st.session_state:
        spec=st.session_state["spec"]
        st.subheader("Intermediate JSON specification")
        st.json(spec,expanded=True)
        input_names=[v["name"] for v in spec["inputs"]]
        output_names=[v["name"] for v in spec["outputs"]]
        output_name=st.selectbox("Output to analyze",output_names)
        form=st.radio("Minimization form",["SOP","POS"],horizontal=True)
        try:
            table=build_truth_table(spec)
            result=minimize_function(spec,output_name,form)
            verify=verify_spec(spec,output_name,result["expression"])
            original_expr=expression_to_sympy(spec["rules"][output_name],input_names)
            before=complexity_metrics(original_expr,len(input_names))
            after=complexity_metrics(result["expression"],len(input_names))
            st.subheader("Reduced Boolean expression")
            st.latex(str(result["expression"]).replace("~","\\neg ").replace("&","\\land ").replace("|","\\lor "))
            st.code(f"Canonical SOP: {result['sop_canonical']}\nCanonical POS: {result['pos_canonical']}",language="text")
            v1,v2,v3,v4=st.columns(4)
            v1.metric("Input combinations",f"{2**len(input_names)}")
            v2.metric("Gate count",f"{before['gate_count']} → {after['gate_count']}")
            v3.metric("Logic levels",f"{before['logic_levels']} → {after['logic_levels']}")
            v4.metric("Est. CMOS transistors",f"{before['estimated_transistors_cmos']} → {after['estimated_transistors_cmos']}")
            st.caption("Delay is an educational estimate based on 5 ns per logic level, not device-level timing.")
            metrics=pd.DataFrame([
                {"Metric":"Gate count","Before":before["gate_count"],"After":after["gate_count"]},
                {"Metric":"Logic levels","Before":before["logic_levels"],"After":after["logic_levels"]},
                {"Metric":"Estimated CMOS transistors","Before":before["estimated_transistors_cmos"],"After":after["estimated_transistors_cmos"]},
                {"Metric":"Estimated delay (ns)","Before":before["estimated_delay_ns"],"After":after["estimated_delay_ns"]},
            ])
            st.dataframe(metrics,use_container_width=True,hide_index=True)
            st.subheader("Exhaustive equivalence verification")
            if verify["equivalent"]:
                st.success(f"PASS — reduced expression matches the original rule for all {verify['tested']} input combinations.")
            else:
                st.error(f"FAIL — {len(verify['failures'])} mismatches.")
                st.dataframe(pd.DataFrame(verify["failures"]),use_container_width=True)
            st.subheader("Truth table")
            st.dataframe(table,use_container_width=True,hide_index=True)
            st.download_button("Download truth table CSV",table.to_csv(index=False).encode(),file_name="truth_table.csv",mime="text/csv")
            st.subheader("Interactive simulator")
            st.caption("Toggle input bits to evaluate the original and reduced expressions live.")
            cols=st.columns(min(6,len(input_names)))
            bits=[]
            for i,var in enumerate(spec["inputs"]):
                with cols[i % len(cols)]:
                    bits.append(st.toggle(f"{var['name']} · {var['label']}",value=False,key=f"sim_{var['name']}"))
            bit_values=[int(b) for b in bits]
            syms=variable_symbols(input_names)
            env=dict(zip(syms,[bool(b) for b in bit_values]))
            original_value=int(bool(original_expr.subs(env)))
            reduced_value=int(bool(result["expression"].subs(env)))
            s1,s2,s3=st.columns(3)
            s1.metric("Input vector", "".join(map(str,bit_values)))
            s2.metric("Original output",str(original_value))
            s3.metric("Reduced output",str(reduced_value))
            if original_value==reduced_value: st.success("Live simulation agrees.")
            else: st.error("Mismatch detected.")
            st.subheader("Gate-level schematic")
            try:
                from graphviz import Digraph
                dot=Digraph("logic",format="svg")
                dot.attr(rankdir="LR",splines="ortho",nodesep="0.35",ranksep="0.65")
                for name in input_names:
                    dot.node(name,f"{name}\\n{next(v['label'] for v in spec['inputs'] if v['name']==name)}",shape="box")
                def add_node(node,parent=None,edge_label=""):
                    from sympy.logic.boolalg import And, Or, Not, Xor
                    if getattr(node,"is_Symbol",False):
                        if parent: dot.edge(str(node),parent,label=edge_label)
                        return str(node)
                    nid=f"n{len(dot.body)}"
                    label=("NOT" if isinstance(node,Not) else "AND" if isinstance(node,And) else "OR" if isinstance(node,Or) else "XOR" if isinstance(node,Xor) else str(node))
                    dot.node(nid,label,shape="ellipse")
                    if parent: dot.edge(nid,parent,label=edge_label)
                    for child in node.args:
                        cid=add_node(child)
                        dot.edge(cid,nid)
                    return nid
                root=add_node(result["expression"])
                dot.node("OUT",f"{output_name}\\n{next((o['label'] for o in spec['outputs'] if o['name']==output_name),output_name)}",shape="box",style="filled",fillcolor="lightgoldenrod1")
                dot.edge(root,"OUT")
                st.graphviz_chart(dot, use_container_width=True)
                st.download_button("Download schematic SVG",dot.pipe(format="svg"),file_name="logic_schematic.svg",mime="image/svg+xml")
            except Exception as exc:
                st.warning(f"Schematic rendering unavailable: {exc}")
            st.subheader("Download design files")
            verilog_expr=expression_to_verilog(result["expression"],input_names,output_name)
            verilog=f"module logic_circuit(input {', '.join(input_names)}, output {output_name});\n  assign {output_name} = {verilog_expr};\nendmodule\n"
            circ=build_logisim_circuit(result["expression"],input_names,output_name)
            d1,d2=st.columns(2)
            with d1: st.download_button("Download Verilog (.v)",verilog,file_name="logic_circuit.v",mime="text/plain",use_container_width=True)
            with d2: st.download_button("Download Logisim (.circ)",circ,file_name="logic_circuit.circ",mime="application/xml",use_container_width=True)
            st.subheader("Architectural analysis")
            st.markdown(
                "- **Boolean reduction:** the minimized expression is computed with SymPy's exact Boolean minimization routines for the declared input set.\n"
                "- **Universal gates:** NAND-only or NOR-only conversion can be added as a technology-mapping stage; a smaller Boolean expression does not always mean the fastest physical circuit.\n"
                "- **Hazards:** exhaustive truth-table equivalence does not prove hazard-free timing behavior. Static hazards require path-delay analysis and, where appropriate, consensus terms.\n"
                "- **Safety:** generated logic is a design aid, not a certified safety controller. Independent review and hardware validation are mandatory for industrial systems."
            )
        except Exception as exc:
            st.exception(exc)
with tab_demos:
    st.markdown("Choose one of three prepared scenarios. Click **Load demo** to place its requirement in the builder.")
    for name, demo in DEMO_SCENARIOS.items():
        with st.expander(name):
            st.write(demo["description"])
            st.json(demo)
            if st.button(f"Load demo: {name}",key=f"load_{name}"):
                st.session_state["spec"]=demo
                st.session_state.pop("parse_error",None)
                st.rerun()
with tab_help:
    st.markdown("""
### Supported behavior
- 1–6 Boolean inputs and up to 4 outputs in the validated JSON schema.
- Offline parser supports the included demo cases and explicit Boolean-expression syntax.
- Optional OpenAI parsing is enabled by setting `OPENAI_API_KEY` and switching on the parser toggle.
- The original rule is evaluated over every possible input vector before minimization is accepted.

### Important limits
Natural language is ambiguous. Always inspect the generated variable mapping and rules before exporting. The offline parser deliberately refuses unfamiliar prose rather than guessing. For high-stakes systems, translate requirements into a reviewed formal specification and verify against that specification; an LLM cannot guarantee the meaning of arbitrary English.

### Logisim
The exporter emits a `.circ` XML project using common gate and pin components. Logisim / Logisim-evolution component schemas can vary by version, so open the file in your target application, inspect all connections, and simulate every truth-table row before submitting or deploying it.
""")
