"""Generate a native-style Logisim .circ XML circuit from a minimized expression.

The generated circuit uses primitive Pin, NOT, AND, OR components and explicit
wires. Logisim / Logisim-evolution XML schemas can differ by release; always
open and inspect the generated file in the target version before submission.
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def _parse_terms(expression: str, form: str) -> list[list[tuple[str, bool]]]:
    if expression in ("0", "1"):
        return []
    if form.upper() == "SOP":
        raw_terms = expression.split("+")
        return [[(v, bool(neg)) for v, neg in re.findall(r"([A-F])('?)(?:$)?", term)] for term in raw_terms]
    raw_terms = re.findall(r"\(([^()]*)\)", expression)
    return [[(v, bool(neg)) for v, neg in re.findall(r"([A-F])('?)(?:$)?", term)] for term in raw_terms]


def build_logisim_circuit(expression: str, form: str, n_vars: int, output_path: str | Path, circuit_name: str = "BooleanSimplified") -> Path:
    if n_vars not in (4, 5, 6):
        raise ValueError("Only 4, 5, or 6 variables are supported.")
    form = form.upper()
    if form not in ("SOP", "POS"):
        raise ValueError("form must be SOP or POS")
    names = ["A", "B", "C", "D", "E", "F"][:n_vars]
    terms = _parse_terms(expression, form)
    root = ET.Element("project", {"source": "logisim-evolution", "version": "1.0"})
    ET.SubElement(root, "lib", {"name": "0", "desc": "Wiring"})
    ET.SubElement(root, "lib", {"name": "1", "desc": "Gates"})
    ET.SubElement(root, "lib", {"name": "2", "desc": "Plexers"})
    ET.SubElement(root, "lib", {"name": "3", "desc": "Arithmetic"})
    ET.SubElement(root, "main", {"name": circuit_name})
    options = ET.SubElement(root, "options", {" name": "options"})
    ET.SubElement(options, "a", {"name": "gateUndefined", "val": "ignore"})
    ET.SubElement(options, "a", {"name": "simlimit", "val": "1000"})
    circuit = ET.SubElement(root, "circuit", {"name": circuit_name})
    ET.SubElement(circuit, "a", {"name": "appearance", "val": "classic"})
    ET.SubElement(circuit, "a", {"name": "circuit", "val": "true"})

    # Geometry uses a 40-pixel grid and unique junction coordinates.
    wires: set[tuple[tuple[int,int], tuple[int,int]]] = set()
    def wire(a: tuple[int,int], b: tuple[int,int]) -> None:
        if a == b: return
        wires.add((a,b) if a <= b else (b,a))
    def comp(lib: str, name: str, x: int, y: int, attrs: dict[str,str] | None = None) -> ET.Element:
        el = ET.SubElement(circuit, "comp", {"lib": lib, "name": name, "loc": f"({x},{y})"})
        for k,v in (attrs or {}).items(): ET.SubElement(el, "a", {"name": k, "val": v})
        return el

    # Input pins in a left column. Pin output location is the component coordinate.
    input_xy: dict[str,tuple[int,int]] = {}
    for i, name in enumerate(names):
        x,y = 80, 80 + i*80
        comp("0", "Pin", x, y, {"facing":"east", "output":"false", "tristate":"false", "label":name, "labelloc":"west", "labelfont":"SansSerif plain 12"})
        input_xy[name] = (x+20,y)

    # Each polarity needed by the expression gets one inverter in the second column.
    needs_not = sorted({v for term in terms for v,neg in term if neg})
    source_xy = dict(input_xy)
    for i, name in enumerate(needs_not):
        x,y = 240, 80 + i*80
        comp("1", "NOT Gate", x, y, {"facing":"east", "size":"20", "label":""})
        # Input pin -> NOT gate input; gate input assumed at x-20, y.
        wire(input_xy[name], (x-20,y))
        source_xy[name+"'"] = (x+20,y)

    stage_x = 440
    term_outputs: list[tuple[int,int]] = []
    if not terms:
        # Constant output: tie the output pin to a constant component.
        const_val = "0" if expression == "0" else "1"
        comp("0", "Constant", 440, 160, {"value":const_val, "width":"1"})
        const_out = (460,160)
        comp("0", "Pin", 760, 160, {"facing":"west", "output":"true", "tristate":"false", "label":"F_out", "labelloc":"east", "labelfont":"SansSerif plain 12"})
        wire(const_out, (740,160))
    else:
        # Stage-1 gates. SOP: AND terms. POS: OR clauses.
        stage_gate = "AND Gate" if form == "SOP" else "OR Gate"
        for ti, term in enumerate(terms):
            gy = 100 + ti*100
            gx = stage_x
            comp("1", stage_gate, gx, gy, {"facing":"east", "size":"30", "inputs":str(max(2,len(term))), "label":""})
            # Explicit input branches are drawn to the conventional left-side gate edge.
            for li, (var, neg) in enumerate(term):
                src = source_xy[var+"'"] if neg else source_xy[var]
                target = (gx-30, gy + (li-(len(term)-1)/2)*20)
                target = (int(target[0]), int(target[1]))
                elbow_x = gx-70
                wire(src, (elbow_x, src[1])); wire((elbow_x,src[1]), (elbow_x,target[1])); wire((elbow_x,target[1]), target)
            term_outputs.append((gx+30,gy))
        final_gate = "OR Gate" if form == "SOP" else "AND Gate"
        final_x, final_y = 640, 180
        comp("1", final_gate, final_x, final_y, {"facing":"east", "size":"30", "inputs":str(max(2,len(term_outputs))), "label":""})
        for ti, src in enumerate(term_outputs):
            target = (final_x-30, final_y + (ti-(len(term_outputs)-1)/2)*20)
            target = (int(target[0]), int(target[1]))
            elbow_x = 590
            wire(src, (elbow_x,src[1])); wire((elbow_x,src[1]), (elbow_x,target[1])); wire((elbow_x,target[1]), target)
        comp("0", "Pin", 760, final_y, {"facing":"west", "output":"true", "tristate":"false", "label":"F_out", "labelloc":"east", "labelfont":"SansSerif plain 12"})
        wire((final_x+30,final_y),(740,final_y))

    for a,b in sorted(wires):
        ET.SubElement(circuit, "wire", {"from":f"({a[0]},{a[1]})", "to":f"({b[0]},{b[1]})"})
    # Logisim projects commonly use tool definitions and toolbar data.
    ET.SubElement(root, "mappings")
    ET.SubElement(root, "toolbar")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    try: ET.indent(tree, space="  ")
    except AttributeError: pass
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    # Parse it back so malformed XML is never silently delivered.
    ET.parse(out)
    return out
