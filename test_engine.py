import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from circuit_engine import make_circuit, Fault
from fault_diagnostician import differential_table, diagnose, verify_equivalence

class EngineTests(unittest.TestCase):
    def test_full_adder_equation(self):
        c = make_circuit("Full Adder")
        for v in c.vectors():
            out, _ = c.evaluate(v)
            self.assertEqual(out["Sum"], v["A"] ^ v["B"] ^ v["Cin"])
            self.assertEqual(out["Cout"], (v["A"] & v["B"]) | ((v["A"] ^ v["B"]) & v["Cin"]))

    def test_rca_has_512_vectors(self):
        c = make_circuit("4-bit Ripple Carry Adder")
        self.assertEqual(sum(1 for _ in c.vectors()), 512)

    def test_mux(self):
        c = make_circuit("4:1 MUX")
        for v in c.vectors():
            out, _ = c.evaluate(v)
            idx = (v["S1"] << 1) | v["S0"]
            self.assertEqual(out["Y"], v[f"D{idx}"])

    def test_stuck_fault_detected(self):
        c = make_circuit("Full Adder")
        f = Fault("stuck_at", node="SUM", value=0)
        table = differential_table(c, f)
        self.assertGreater(int(table["Any_Error"].sum()), 0)
        d = diagnose(c, f, include_bridges=False)
        self.assertGreaterEqual(len(d.candidates), 1)

    def test_equivalence(self):
        c = make_circuit("Full Adder")
        self.assertTrue(verify_equivalence(c, c.clone())["equivalent"])

if __name__ == "__main__":
    unittest.main()
