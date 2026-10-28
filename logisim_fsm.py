#!/usr/bin/env python3
"""Create a Logisim XML visual scaffold for the traffic FSM.
The emitted file is a scaffold; validate component pin geometry and wire it in your
installed Logisim version. Verilog remains the executable reference implementation.
"""
import argparse, xml.etree.ElementTree as ET
from pathlib import Path
def generate_circ(output="traffic_fsm.circ"):
 root=ET.Element("project",{"version":"1.0","source":"Traffic FSM Generator"})
 for i,name in enumerate(("Wiring","Gates","Base")): ET.SubElement(root,"lib",{"name":str(i),"desc":name})
 ET.SubElement(root,"main",{"name":"main"}); ET.SubElement(root,"options")
 ET.SubElement(root,"mappings"); c=ET.SubElement(root,"circuit",{"name":"main"})
 ET.SubElement(c,"a",{"name":"circuit","val":"main"}); ET.SubElement(c,"appear")
 for name,x,y,out in [("clk",40,60,"false"),("reset_n",40,120,"false"),("ped_req",40,180,"false"),("timer_long",40,240,"false"),("timer_short",40,300,"false")]:
  p=ET.SubElement(c,"comp",{"lib":"2","name":"Pin","loc":f"({x},{y})"})
  ET.SubElement(p,"a",{"name":"label","val":name}); ET.SubElement(p,"a",{"name":"facing","val":"east"}); ET.SubElement(p,"a",{"name":"output","val":out})
 for name,x,y in [("Q1",280,140),("Q0",280,260)]:
  p=ET.SubElement(c,"comp",{"lib":"4","name":"D Flip-Flop","loc":f"({x},{y})"})
  ET.SubElement(p,"a",{"name":"label","val":name}); ET.SubElement(p,"a",{"name":"trigger","val":"rising"})
 for name,x,y in [("Main_R",650,80),("Main_Y",650,140),("Main_G",650,200),("Ped_Walk",650,260),("Ped_DontWalk",650,320)]:
  p=ET.SubElement(c,"comp",{"lib":"2","name":"LED","loc":f"({x},{y})"}); ET.SubElement(p,"a",{"name":"label","val":name})
 ET.indent(root,space="  "); Path(output).write_bytes(ET.tostring(root,encoding="utf-8",xml_declaration=True))
 return output
if __name__=="__main__":
 ap=argparse.ArgumentParser(); ap.add_argument("-o","--output",default="traffic_fsm.circ"); args=ap.parse_args()
 print("Wrote",generate_circ(args.output))
