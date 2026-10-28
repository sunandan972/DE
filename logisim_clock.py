"""Create an XML-well-formed Logisim-evolution schematic scaffold.
Component attributes and pin routing can vary by Logisim version; inspect and finish wiring.
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

def attr(parent,name,val): ET.SubElement(parent,"a",{"name":name,"val":str(val)})
def export(path):
 root=ET.Element("project",{"version":"1.0","source":"24-hour digital clock"})
 ET.SubElement(root,"lib",{"name":"0","desc":"Wiring"})
 ET.SubElement(root,"lib",{"name":"1","desc":"Gates"})
 ET.SubElement(root,"lib",{"name":"2","desc":"Memory"})
 ET.SubElement(root,"lib",{"name":"3","desc":"Input/Output"})
 ET.SubElement(root,"main",{"name":"main"})
 c=ET.SubElement(root,"circuit",{"name":"main"})
 for i,n in enumerate(["CLK","RESET_N","TICK_1HZ","SET_MODE","INC_MIN","INC_HR"]):
  x=ET.SubElement(c,"comp",{"lib":"0","name":"Pin","loc":f"(40,{50+i*40})"})
  attr(x,"facing","east"); attr(x,"output","false"); attr(x,"label",n)
 x_positions={"SEC":180,"MIN":360,"HR":540}
 groups=[("SEC_UNITS",4,180,70),("SEC_TENS",3,180,190),("MIN_UNITS",4,360,70),("MIN_TENS",3,360,190),("HR_UNITS",4,540,70),("HR_TENS",2,540,190)]
 for name,width,x,y in groups:
  for bit in range(width):
   d=ET.SubElement(c,"comp",{"lib":"2","name":"D Flip-Flop","loc":f"({x},{y+bit*25})"})
   attr(d,"label",f"{name}[{bit}]")
 for i,name in enumerate(["H10","H1","M10","M1","S10","S1"]):
  x=680+i*95
  d=ET.SubElement(c,"comp",{"lib":"1","name":"Decoder","loc":f"({x},80)"})
  attr(d,"label","BCD7SEG_"+name)
  s=ET.SubElement(c,"comp",{"lib":"3","name":"7-Segment Display","loc":f"({x},180)"})
  attr(s,"label",name)
 for i,name in enumerate(["TC_SEC","TC_MIN","TC_HOUR"]):
  p=ET.SubElement(c,"comp",{"lib":"0","name":"Pin","loc":f"(850,{320+i*35})"})
  attr(p,"facing","west"); attr(p,"output","true"); attr(p,"label",name)
 ET.SubElement(c,"appear"); ET.indent(root,space="  ")
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 ET.ElementTree(root).write(path,encoding="utf-8",xml_declaration=True)
 ET.parse(path)
 return path
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--out",default="digital_clock_24h.circ")
 a=p.parse_args(); print("Created",export(a.out),"- inspect/finish wiring in Logisim.")
