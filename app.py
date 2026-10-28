from __future__ import annotations
import io
import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from simplifier import (minimize, parse_minterm_notation, parse_boolean_expression,
                        parse_truth_table, truth_table_for_minterms, verify_equivalence,
                        complexity_metrics, algebraic_steps)
from logisim_builder import build_logisim_circuit

st.set_page_config(page_title="Boolean Logic Workbench", page_icon="⚡", layout="wide")
st.title("⚡ AI-Assisted Boolean Simplifier & Logisim Generator")
st.caption("Exact Quine–McCluskey minimization · Petrick cover selection · K-maps · Verilog · Logisim XML · exhaustive verification")

with st.sidebar:
    st.header("Function setup")
    n_vars = st.selectbox("Number of variables", [4,5,6], index=0)
    input_mode = st.radio("Input method", ["Minterm / maxterm notation", "Boolean expression", "Truth table"], index=0)
    form = st.radio("Reduction form", ["SOP", "POS"], horizontal=True)
    st.info("Variable order is A (MSB), then B, C, D, E, F (LSB). Don't-cares are allowed for minterm notation.")

if input_mode == "Minterm / maxterm notation":
    raw = st.text_input("Function", value="Σm(0, 2, 5, 7, 8, 10, 13, 15) + d(1, 3)")
    parse_button = st.button("Simplify function", type="primary")
    if parse_button:
        try:
            on_set, dont_cares = parse_minterm_notation(raw, n_vars)
            st.session_state["function_data"] = {"on":on_set,"dc":dont_cares,"source":raw}
        except Exception as exc: st.error(str(exc))
elif input_mode == "Boolean expression":
    raw = st.text_input("Boolean expression", value="A'B'C'D + AB'C'D + A'B'CD")
    parse_button = st.button("Simplify function", type="primary")
    if parse_button:
        try:
            on_set, dont_cares, _ = parse_boolean_expression(raw, n_vars)
            st.session_state["function_data"] = {"on":on_set,"dc":dont_cares,"source":raw}
        except Exception as exc: st.error(str(exc))
else:
    st.write("Enter output values in ascending binary input order. Rows are generated for the selected variable count.")
    count = 1 << n_vars
    if "truth_editor" not in st.session_state or len(st.session_state["truth_editor"]) != count:
        st.session_state["truth_editor"] = pd.DataFrame(truth_table_for_minterms([], n_vars), columns=[*list("ABCDEF")[:n_vars],"F"])
    edited = st.data_editor(st.session_state["truth_editor"], num_rows="fixed", use_container_width=True, key=f"truth_{n_vars}")
    if st.button("Simplify truth table", type="primary"):
        try:
            on_set = parse_truth_table(edited.astype(int).values.tolist(), n_vars)
            st.session_state["function_data"] = {"on":on_set,"dc":[],"source":"Truth table"}
        except Exception as exc: st.error(str(exc))

if "function_data" in st.session_state:
    data = st.session_state["function_data"]
    on_set, dc_set = data["on"], data["dc"]
    st.divider()
    st.subheader("Exact minimization results")
    try:
        result = minimize(on_set, n_vars, dc_set, form)
        other = minimize(on_set, n_vars, dc_set, "POS" if form == "SOP" else "SOP")
        c1,c2,c3 = st.columns(3)
        c1.metric("Variables", n_vars)
        c2.metric("ON-set minterms", len(on_set))
        c3.metric("Don't-cares", len(dc_set))
        st.markdown(f"### Minimal {form}: `{result.expression}`")
        st.caption(f"Selected implicants: {len(result.selected_implicants)} · Prime implicants: {len(result.prime_implicants)} · Equally minimal covers found: {len(result.all_minimum_covers)}")
        with st.expander("Quine–McCluskey prime implicants and Petrick cover"):
            st.write("Prime implicants (dash means the variable is eliminated):")
            st.dataframe(pd.DataFrame([{"Pattern":p.pattern,"Literals":p.literals,"Covers ON-set":sorted(set(p.covered)&set(on_set)),"Selected":p in result.selected_implicants} for p in result.prime_implicants]), use_container_width=True)
            st.write("Other form:", other.expression)
        st.subheader("Truth table and equivalence verification")
        table = truth_table_for_minterms(on_set, n_vars)
        df = pd.DataFrame(table, columns=[*list("ABCDEF")[:n_vars],"F_original"])
        st.dataframe(df, use_container_width=True, height=260)
        verification = verify_equivalence(on_set, result.expression, n_vars, form)
        if verification["equivalent"]: st.success(f"PASS — exact equivalence verified for all {verification['tested_rows']} input combinations.")
        else: st.error(f"FAIL — {len(verification['mismatches'])} mismatches detected.")
        st.subheader("Karnaugh map")
        # Gray code ordering for each 4x4 plane. 5-var uses 2 planes; 6-var uses 4.
        gray = [0,1,3,2]
        plane_vars = n_vars - 4
        plane_count = 1 << plane_vars
        cols = st.columns(plane_count)
        for plane in range(plane_count):
            grid = np.zeros((4,4), dtype=int)
            labels = []
            for ri,r in enumerate(gray):
                for ci,c in enumerate(gray):
                    idx = (plane << 4) | (r << 2) | c
                    grid[ri,ci] = 2 if idx in dc_set else (1 if idx in on_set else 0)
            fig, ax = plt.subplots(figsize=(3.6,3.2))
            ax.imshow(grid, vmin=0, vmax=2, cmap="YlGnBu")
            ax.set_xticks(range(4), [format(x, "02b") for x in gray])
            ax.set_yticks(range(4), [format(x, "02b") for x in gray])
            for ri in range(4):
                for ci in range(4):
                    idx = (plane << 4) | (gray[ri] << 2) | gray[ci]
                    value = "X" if idx in dc_set else str(int(idx in on_set))
                    ax.text(ci,ri,value,ha="center",va="center",color="black",fontsize=11)
            ax.set_xlabel("CD (Gray order)"); ax.set_ylabel("AB (Gray order)")
            prefix = "" if n_vars == 4 else f"{''.join(list('EF')[:plane_vars])} = {format(plane, f'0{plane_vars}b')}"
            ax.set_title(f"K-map {prefix}".strip())
            fig.tight_layout()
            with cols[plane]: st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        st.caption("Cells are displayed in Gray-code order. X denotes a don't-care. Group-loop overlays are not drawn in this version; implicant patterns are listed above.")
        st.subheader("Circuit complexity estimates")
        before_expr = " + ".join("".join((list("ABCDEF")[:n_vars][j] if bit=="1" else list("ABCDEF")[:n_vars][j]+"'") for j,bit in enumerate(format(m,f'0{n_vars}b'))) for m in on_set) or "0"
        before = complexity_metrics(before_expr,"SOP",n_vars)
        after = complexity_metrics(result.expression,form,n_vars)
        st.dataframe(pd.DataFrame([{"Metric":"Gate count","Before":before['gate_count'],"After":after['gate_count']},{"Metric":"Input pins (approx.)","Before":before['input_pins'],"After":after['input_pins']},{"Metric":"Logic depth (levels)","Before":before['logic_depth'],"After":after['logic_depth']},{"Metric":"CMOS transistors (estimate)","Before":before['transistors_est'],"After":after['transistors_est']}]), use_container_width=True)
        st.caption("Before is represented as canonical SOP; after follows the selected form. Estimates use basic multi-input gate assumptions and are not transistor-level synthesis results.")
        st.subheader("Verilog output")
        names = list("ABCDEF")[:n_vars]
        verilog = f"module boolean_simplified({', '.join(names)}, F_out);\n  input {', '.join(names)};\n  output F_out;\n  assign F_out = {result.expression.replace(chr(39), '').replace('+',' | ').replace('(','(').replace(')',' )').replace('A','A').replace('B','B')};\nendmodule\n"
        # Render the expression using explicit Verilog operators safely from implicant patterns.
        if result.expression in ("0","1"): verilog_rhs = result.expression
        elif form == "SOP":
            terms=[]
            for imp in result.selected_implicants:
                factors=[(v if bit=='1' else '~'+v) for v,bit in zip(names,imp.pattern) if bit!='-']
                terms.append("("+" & ".join(factors)+")" if factors else "1'b1")
            verilog_rhs=" | ".join(terms) if terms else "1'b0"
        else:
            clauses=[]
            for imp in result.selected_implicants:
                factors=[(v if bit=='0' else '~'+v) for v,bit in zip(names,imp.pattern) if bit!='-']
                clauses.append("("+" | ".join(factors)+")" if factors else "1'b0")
            verilog_rhs=" & ".join(clauses) if clauses else "1'b1"
        verilog = f"module boolean_simplified({', '.join(names)}, F_out);\n  input {', '.join(names)};\n  output F_out;\n  assign F_out = {verilog_rhs};\nendmodule\n"
        st.code(verilog, language="verilog")
        st.download_button("Download Verilog (.v)", verilog, file_name="boolean_simplified.v", mime="text/plain")
        st.subheader("Logisim circuit export")
        st.warning("Logisim component attributes and pin coordinates vary between versions. Open the exported file in your installed Logisim / Logisim-evolution and validate the wiring before relying on it for hardware work.")
        if st.button("Generate Logisim .circ file"):
            try:
                out = build_logisim_circuit(result.expression, form, n_vars, "/tmp/boolean_simplified.circ")
                st.session_state["circ_bytes"] = out.read_bytes()
                st.success("Circuit XML generated and parsed successfully.")
            except Exception as exc: st.error(f"Circuit generation failed: {exc}")
        if "circ_bytes" in st.session_state:
            st.download_button("Download Logisim .circ file", st.session_state["circ_bytes"], file_name="boolean_simplified.circ", mime="application/xml")
        st.subheader("Reduction explanation")
        st.write("The minimizer uses exact implicant combination and Petrick cover selection. SymPy's simplifier is shown as a supplementary algebraic check, not as the source of the selected cover.")
        for step in algebraic_steps(result.expression, form): st.write("• " + step)
        st.subheader("AI explanation prompt")
        prompt = f"Act as a digital logic tutor. Explain the exact {form} minimization of this {n_vars}-variable Boolean function. Original ON-set: {on_set}. Don't-cares: {dc_set}. Reduced expression: {result.expression}. Explain applicable De Morgan, absorption, and consensus laws only when they genuinely apply; compare AND-OR / OR-AND with NAND-NAND / NOR-NOR implementation; mention fan-in, fan-out, logic depth, and that physical delay depends on the target library. Do not invent intermediate algebraic steps."
        st.text_area("Copy this prompt into your preferred LLM", prompt, height=150)
        st.download_button("Download verification report (CSV)", pd.DataFrame(verification["mismatches"]).to_csv(index=False) if verification["mismatches"] else "equivalent,tested_rows\nTrue,"+str(verification["tested_rows"])+"\n", file_name="verification_report.csv", mime="text/csv")
    except Exception as exc:
        st.exception(exc)
else:
    st.info("Choose an input method, enter a function, and select Simplify to begin.")
