"""CLI wrapper for Logisim export."""
import argparse
from circuit_engine import make_circuit, Fault
from logisim_exporter import export_logisim

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuit", default="Full Adder",
                        choices=["Full Adder", "4-bit Ripple Carry Adder", "4:1 MUX"])
    parser.add_argument("--out", default="faulty_circuit.circ")
    parser.add_argument("--node", default="SUM")
    parser.add_argument("--stuck", type=int, choices=[0, 1], default=0)
    args = parser.parse_args()
    c = make_circuit(args.circuit)
    fault = Fault("stuck_at", node=args.node, value=args.stuck)
    export_logisim(c, args.out, fault=fault)
    print(f"Wrote {args.out}; inspect the schematic in Logisim before relying on it.")
if __name__ == "__main__":
    main()
