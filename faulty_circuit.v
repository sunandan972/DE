// Fault-injectable 1-bit full adder reference model.
// FAULT_ENABLE=0 gives golden behavior.
// FAULT_MODE: 0 none, 1 Sum SA0, 2 Sum SA1, 3 Cout SA0, 4 Cout SA1,
//             5 XOR1 mutation XOR->OR, 6 AND1 mutation AND->NAND.
module faulty_circuit #(
    parameter integer FAULT_ENABLE = 1,
    parameter integer FAULT_MODE = 1
) (
    input wire A, B, Cin,
    output wire Sum, Cout
);
    wire xor1_nom, xor1_faulty, and1_nom, and1_faulty, and2;
    wire sum_nom, cout_nom;
    assign xor1_nom = A ^ B;
    assign xor1_faulty = (FAULT_ENABLE && FAULT_MODE == 5) ? (A | B) : xor1_nom;
    assign sum_nom = xor1_faulty ^ Cin;
    assign and1_nom = A & B;
    assign and1_faulty = (FAULT_ENABLE && FAULT_MODE == 6) ? ~(A & B) : and1_nom;
    assign and2 = xor1_faulty & Cin;
    assign cout_nom = and1_faulty | and2;
    assign Sum = (FAULT_ENABLE && FAULT_MODE == 1) ? 1'b0 :
                 (FAULT_ENABLE && FAULT_MODE == 2) ? 1'b1 : sum_nom;
    assign Cout = (FAULT_ENABLE && FAULT_MODE == 3) ? 1'b0 :
                  (FAULT_ENABLE && FAULT_MODE == 4) ? 1'b1 : cout_nom;
endmodule
