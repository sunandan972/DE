"""Truth-table construction, exact Boolean minimization and exhaustive verification."""
from __future__ import annotations
from itertools import product
import pandas as pd
from sympy import symbols
from sympy.logic.boolalg import SOPform, POSform, simplify_logic, BooleanTrue, BooleanFalse
from nl_parser import expression_to_sympy

def variable_symbols(names):
    result = symbols(" ".join(names))
    return (result,) if len(names) == 1 else tuple(result)

def evaluate_expression(expr, variables, bits):
    env = dict(zip(variables, map(bool, bits)))
    value = bool(expr.subs(env))
    return int(value)

def build_truth_table(spec):
    names = [v["name"] for v in spec["inputs"]]
    syms = variable_symbols(names)
    rows = []
    for bits in product([0, 1], repeat=len(names)):
        row = {name: bit for name, bit in zip(names, bits)}
        for out in spec["outputs"]:
            expr = expression_to_sympy(spec["rules"][out["name"]], names)
            row[out["name"]] = evaluate_expression(expr, syms, bits)
        rows.append(row)
    return pd.DataFrame(rows)

def canonical_forms(spec, output_name):
    names = [v["name"] for v in spec["inputs"]]
    syms = variable_symbols(names)
    expr = expression_to_sympy(spec["rules"][output_name], names)
    on_set, off_set = [], []
    for index, bits in enumerate(product([0, 1], repeat=len(names))):
        val = evaluate_expression(expr, syms, bits)
        (on_set if val else off_set).append(index)
    def minterm(idx):
        return "".join(map(str, [(idx >> shift) & 1 for shift in range(len(names)-1, -1, -1)]))
    sop = "Σm(" + ", ".join(map(str, on_set)) + ")"
    pos = "ΠM(" + ", ".join(map(str, off_set)) + ")"
    return {"on_set":on_set,"off_set":off_set,"sop_canonical":sop,"pos_canonical":pos}

def minimize_function(spec, output_name, form="SOP"):
    names = [v["name"] for v in spec["inputs"]]
    syms = variable_symbols(names)
    forms = canonical_forms(spec, output_name)
    selected = forms["on_set"] if form.upper() == "SOP" else forms["off_set"]
    # SymPy SOPform/POSform are exact for these small truth tables; their minimizer uses
    # Boolean minimization algorithms and is used as a reference implementation here.
    if form.upper() == "SOP":
        reduced = SOPform(syms, forms["on_set"])
    elif form.upper() == "POS":
        reduced = POSform(syms, forms["on_set"])
    else:
        raise ValueError("form must be SOP or POS")
    reduced = simplify_logic(reduced, form=("dnf" if form.upper() == "SOP" else "cnf"), force=True)
    return {**forms,"expression":reduced,"expression_text":str(reduced),"form":form.upper()}

def verify_spec(spec, output_name, minimized_expr=None):
    names = [v["name"] for v in spec["inputs"]]
    syms = variable_symbols(names)
    original = expression_to_sympy(spec["rules"][output_name], names)
    target = minimized_expr if minimized_expr is not None else minimize_function(spec, output_name)["expression"]
    failures = []
    for bits in product([0,1], repeat=len(names)):
        a = evaluate_expression(original, syms, bits)
        b = evaluate_expression(target, syms, bits)
        if a != b:
            failures.append({"inputs":dict(zip(names,bits)),"original":a,"reduced":b})
    return {"equivalent":not failures,"tested":2**len(names),"failures":failures}

def expression_to_verilog(expr, variables, output="Y"):
    """Convert a SymPy Boolean expression to readable Verilog operators."""
    from sympy.logic.boolalg import And, Or, Not, Xor, BooleanTrue, BooleanFalse
    def walk(node):
        if node is True or node == BooleanTrue(): return "1'b1"
        if node is False or node == BooleanFalse(): return "1'b0"
        if getattr(node, "is_Symbol", False): return str(node)
        if isinstance(node, Not): return f"~({walk(node.args[0])})"
        if isinstance(node, And): return "(" + " & ".join(walk(x) for x in node.args) + ")"
        if isinstance(node, Or): return "(" + " | ".join(walk(x) for x in node.args) + ")"
        if isinstance(node, Xor): return "(" + " ^ ".join(walk(x) for x in node.args) + ")"
        return str(node)
    return walk(expr)

def complexity_metrics(expr, n_inputs, model="2-input gates"):
    """Technology-neutral rough estimate; CMOS transistor count uses 2-input gate equivalents."""
    from sympy.logic.boolalg import And, Or, Not, Xor
    def depth(node):
        if not getattr(node, "args", ()): return 0
        if isinstance(node, Not): return depth(node.args[0]) + 1
        if isinstance(node, (And, Or, Xor)):
            # A multi-input operation is implemented as a balanced tree of 2-input gates.
            import math
            return max(depth(x) for x in node.args) + math.ceil(math.log2(max(2,len(node.args))))
        return max((depth(x) for x in node.args), default=0)
    def count(node):
        if not getattr(node, "args", ()): return {"AND":0,"OR":0,"NOT":0,"XOR":0}
        acc={"AND":0,"OR":0,"NOT":0,"XOR":0}
        for child in node.args:
            c=count(child)
            for k,v in c.items(): acc[k]+=v
        if isinstance(node, And): acc["AND"] += max(1,len(node.args)-1)
        elif isinstance(node, Or): acc["OR"] += max(1,len(node.args)-1)
        elif isinstance(node, Not): acc["NOT"] += 1
        elif isinstance(node, Xor): acc["XOR"] += max(1,len(node.args)-1)
        return acc
    gates=count(expr)
    gate_count=sum(gates.values())
    # Simple textbook estimates: inverter 2, 2-input NAND 4, NOR 4, AND/OR 6, XOR 10.
    transistors=gates["NOT"]*2 + (gates["AND"]+gates["OR"])*6 + gates["XOR"]*10
    return {"gate_count":gate_count,"gate_breakdown":gates,
            "logic_levels":depth(expr),"estimated_transistors_cmos":transistors,
            "estimated_delay_ns":round(depth(expr)*5.0,2),
            "model":"Approximate 2-input gate model; assumed 5 ns per level. Not physical sign-off."}

def truth_table_from_expression(expr_text, names):
    expr=expression_to_sympy(expr_text,names)
    syms=variable_symbols(names)
    rows=[]
    for bits in product([0,1],repeat=len(names)):
        rows.append({**dict(zip(names,bits)),"Y":evaluate_expression(expr,syms,bits)})
    return pd.DataFrame(rows)
