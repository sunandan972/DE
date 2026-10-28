"""Minimal Logisim-evolution .circ XML exporter.

The generated file is a schematic scaffold containing named pins and gates.
It is XML-well-formed, but component placement/import compatibility can vary by
Logisim/Logisim-evolution version. Open and visually inspect before submission.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from circuit_engine import Circuit, Fault

def _loc(node, index, output_nodes, input_nodes):
    if node in input_nodes:
        return (40, 80 + 50 * input_nodes.index(node))
    if node in output_nodes:
        return (650, 80 + 50 * output_nodes.index(node))
    return (180 + 95 * (index // 5), 80 + 50 * (index % 5))

def export_logisim(circuit: Circuit, path, fault: Fault = None, repaired=False):
    root = ET.Element("project", {"version": "1.0", "source": "AI Circuit Fault Diagnosis"})
    ET.SubElement(root, "lib", {"name": "0", "desc": "Wiring"})
    ET.SubElement(root, "lib", {"name": "1", "desc": "Gates"})
    ET.SubElement(root, "lib", {"name": "2", "desc": "Plexers"})
    ET.SubElement(root, "main", {"name": "main"})
    circuit_el = ET.SubElement(root, "circuit", {"name": "main"})
    ET.SubElement(circuit_el, "a", {"name": "appearance", "val": "logisim_evolution"})
    ET.SubElement(circuit_el, "a", {"name": "circuit", "val": "main"})
    inputs, outputs = list(circuit.inputs), list(circuit.outputs.keys())
    # Standard Logisim XML pin/gate component conventions. Wires are intentionally
    # omitted where pin/gate geometry is version-specific; node labels preserve mapping.
    for i, name in enumerate(inputs):
        x, y = 40, 80 + 50*i
        comp = ET.SubElement(circuit_el, "comp", {"lib": "0", "name": "Pin", "loc": f"({x},{y})"})
        ET.SubElement(comp, "a", {"name": "facing", "val": "east"})
        ET.SubElement(comp, "a", {"name": "output", "val": "false"})
        ET.SubElement(comp, "a", {"name": "label", "val": name})
    for i, gate in enumerate(circuit.gates):
        x, y = 180 + 100*(i//5), 80 + 50*(i%5)
        comp = ET.SubElement(circuit_el, "comp", {"lib": "1", "name": gate.op.title(), "loc": f"({x},{y})"})
        ET.SubElement(comp, "a", {"name": "facing", "val": "east"})
        ET.SubElement(comp, "a", {"name": "label", "val": gate.name + (" [FAULT]" if fault and fault.node == gate.name and not repaired else "")})
        ET.SubElement(comp, "a", {"name": "inputs", "val": str(len(gate.inputs))})
    for i, (out, node) in enumerate(circuit.outputs.items()):
        x, y = 650, 80 + 50*i
        comp = ET.SubElement(circuit_el, "comp", {"lib": "0", "name": "Pin", "loc": f"({x},{y})"})
        ET.SubElement(comp, "a", {"name": "facing", "val": "west"})
        ET.SubElement(comp, "a", {"name": "output", "val": "true"})
        ET.SubElement(comp, "a", {"name": "label", "val": out})
    ET.SubElement(circuit_el, "appear")
    ET.indent(root, space="  ")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    # Parse again to ensure well-formed XML.
    ET.parse(path)
    return path
