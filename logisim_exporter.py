"""Generate a basic Logisim-compatible .circ project from a Boolean expression.

The exporter intentionally uses a conservative gate-level subset. Always open and simulate
exports in the target Logisim/Logisim-evolution version before relying on them.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from sympy.logic.boolalg import And, Or, Not, Xor, BooleanTrue, BooleanFalse

def _walk(expr):
    if expr is True or expr == BooleanTrue(): return ("CONST",1,[])
    if expr is False or expr == BooleanFalse(): return ("CONST",0,[])
    if getattr(expr,"is_Symbol",False): return ("INPUT",str(expr),[])
    if isinstance(expr,Not): return ("NOT",None,[_walk(expr.args[0])])
    if isinstance(expr,And): return ("AND",None,[_walk(x) for x in expr.args])
    if isinstance(expr,Or): return ("OR",None,[_walk(x) for x in expr.args])
    if isinstance(expr,Xor): return ("XOR",None,[_walk(x) for x in expr.args])
    raise ValueError(f"Unsupported SymPy node for circuit export: {expr!s}")

def build_logisim_circuit(expr, input_names, output_name="Y", project_name="NaturalLanguageLogic"):
    """Return XML bytes. Layout is layered and wires connect component anchor coordinates."""
    root=ET.Element("project", {"version":"1.0","source":"Natural Language Logic Generator"})
    ET.SubElement(root,"lib",{"name":"0","desc":"Wiring"})
    ET.SubElement(root,"lib",{"name":"1","desc":"Gates"})
    ET.SubElement(root,"lib",{"name":"2","desc":"Base"})
    main=ET.SubElement(root,"main",{"name":"main"})
    options=ET.SubElement(root,"options")
    ET.SubElement(options,"a",{"name":"gateUndefined","val":"ignore"})
    ET.SubElement(options,"a",{"name":"simlimit","val":"1000"})
    ET.SubElement(root,"mappings")
    circuit=ET.SubElement(root,"circuit",{"name":"main"})
    ET.SubElement(circuit,"a",{"name":"circuit","val":"main"})
    ET.SubElement(circuit,"appear")
    # Build a DAG with coordinates. Inputs are positioned at left; gates by depth.
    components=[]
    wires=[]
    input_coords={}
    for i,name in enumerate(input_names):
        x,y=80,80+i*60
        comp=ET.Element("comp",{"lib":"2","name":"Pin","loc":f"({x},{y})"})
        ET.SubElement(comp,"a",{"name":"label","val":name})
        ET.SubElement(comp,"a",{"name":"facing","val":"east"})
        ET.SubElement(comp,"a",{"name":"output","val":"false"})
        components.append(comp); input_coords[name]=(x,y)
    node_counter=[0]
    def place(node, depth=1):
        kind,val,children=node
        if kind=="INPUT": return {"coord":input_coords[val],"kind":"INPUT","name":val}
        if kind=="CONST":
            # Constants are represented by a dedicated constant component.
            x,y=100,500+node_counter[0]*40; node_counter[0]+=1
            comp=ET.Element("comp",{"lib":"0","name":"Constant","loc":f"({x},{y})"})
            ET.SubElement(comp,"a",{"name":"value","val":str(val)})
            components.append(comp)
            return {"coord":(x,y),"kind":"CONST","name":str(val)}
        children_placed=[place(child,depth+1) for child in node[2]]
        idx=node_counter[0]; node_counter[0]+=1
        x=220+depth*130; y=80+idx*60
        logisim_name={"AND":"AND Gate","OR":"OR Gate","NOT":"NOT Gate","XOR":"XOR Gate"}[kind]
        comp=ET.Element("comp",{"lib":"1","name":logisim_name,"loc":f"({x},{y})"})
        if kind in ("AND","OR","XOR"):
            ET.SubElement(comp,"a",{"name":"inputs","val":str(max(2,len(children_placed)))})
        ET.SubElement(comp,"a",{"name":"facing","val":"east"})
        components.append(comp)
        for pin,child in enumerate(children_placed):
            # Logisim gate input pin geometry varies by gate and version. Use explicit wires
            # to the gate's left-side anchor, with a short vertical bus for multiple inputs.
            cx,cy=child["coord"]
            target=(x-30,y+(pin-(len(children_placed)-1)/2)*20)
            wires.append((cx,cy,target[0],target[1]))
        return {"coord":(x,y),"kind":kind,"name":f"g{idx}"}
    root_node=_walk(expr)
    out=place(root_node)
    ox,oy=out["coord"]
    xout=max(ox+160,650); yout=oy
    pin=ET.Element("comp",{"lib":"2","name":"Pin","loc":f"({xout},{yout})"})
    ET.SubElement(pin,"a",{"name":"label","val":output_name})
    ET.SubElement(pin,"a",{"name":"facing","val":"west"})
    ET.SubElement(pin,"a",{"name":"output","val":"true"})
    components.append(pin)
    wires.append((ox,oy,xout,yout))
    for comp in components: circuit.append(comp)
    for x1,y1,x2,y2 in wires:
        if x1==x2:
            ET.SubElement(circuit,"wire",{"from":f"({x1},{y1})","to":f"({x2},{y2})"})
        else:
            bend=x2 if x2<x1 else x1
            ET.SubElement(circuit,"wire",{"from":f"({x1},{y1})","to":f"({x2},{y1})"})
            if y1!=y2:
                ET.SubElement(circuit,"wire",{"from":f"({x2},{y1})","to":f"({x2},{y2})"})
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)

def export_logisim(expr,input_names,output_name="Y",path=None):
    data=build_logisim_circuit(expr,input_names,output_name)
    if path:
        Path(path).write_bytes(data)
    return data
