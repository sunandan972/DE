import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from nl_parser import DEMO_SCENARIOS, parse_natural_language, expression_to_sympy
from logic_engine import build_truth_table, minimize_function, verify_spec
from logisim_exporter import build_logisim_circuit

@pytest.mark.parametrize("name", list(DEMO_SCENARIOS))
def test_demo_truth_tables_and_equivalence(name):
    spec=DEMO_SCENARIOS[name]
    table=build_truth_table(spec)
    assert len(table)==2**len(spec["inputs"])
    for output in [o["name"] for o in spec["outputs"]]:
        result=minimize_function(spec,output,"SOP")
        check=verify_spec(spec,output,result["expression"])
        assert check["equivalent"]
        assert check["tested"]==2**len(spec["inputs"])

def test_offline_expression_parse():
    spec=parse_natural_language("Y = (A AND B) OR NOT C")
    assert len(spec["inputs"])==3

def test_unknown_offline_text_fails_closed():
    with pytest.raises(ValueError):
        parse_natural_language("A very complicated vague industrial scenario with no explicit rule")

def test_circ_xml_well_formed():
    from xml.etree import ElementTree as ET
    spec=DEMO_SCENARIOS["Chemical Tank Overflow & Temperature Alarm (4 inputs)"]
    result=minimize_function(spec,"Y")
    xml=build_logisim_circuit(result["expression"],[x["name"] for x in spec["inputs"]],"Y")
    root=ET.fromstring(xml)
    assert root.tag=="project"
