import pytest
from simplifier import minimize, verify_equivalence, parse_minterm_notation, parse_boolean_expression

@pytest.mark.parametrize("n,on", [(4,[0,1,2,3]), (5,[0,1,2,3,16,17,18,19]), (6,[0,1,2,3,32,33,34,35])])
def test_minimize_sop_equivalence(n,on):
    result=minimize(on,n,form="SOP")
    checked=verify_equivalence(on,result.expression,n,"SOP")
    assert checked["equivalent"]
    assert checked["tested_rows"] == 2**n
@pytest.mark.parametrize("form", ["SOP","POS"])
def test_constant_functions(form):
    result=minimize([],4,form=form)
    assert result.expression in ("0","1")

def test_parse_minterm_notation():
    on,dc=parse_minterm_notation("Σm(0, 2, 5, 7) + d(1, 3)",4)
    assert on == [0,2,5,7]
    assert dc == [1,3]

def test_expression_parser():
    on,dc,_=parse_boolean_expression("A'B'C'D + AB'C'D + A'B'CD",4)
    assert not dc
    assert on

@pytest.mark.parametrize("n,on", [(4,[0,1,4,5,10,11]), (5,[0,1,2,3,8,9,16,17]), (6,[0,1,2,3,8,9,32,33])])
def test_minimize_pos_equivalence(n,on):
    result=minimize(on,n,form="POS")
    checked=verify_equivalence(on,result.expression,n,"POS")
    assert checked["equivalent"]
