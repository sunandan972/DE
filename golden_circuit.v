// Reference 1-bit full adder; synthesizable Verilog-2001.
module golden_circuit (
    input wire A, B, Cin,
    output wire Sum, Cout
);
    wire xor1, and1, and2;
    assign xor1 = A ^ B;
    assign Sum  = xor1 ^ Cin;
    assign and1 = A & B;
    assign and2 = xor1 & Cin;
    assign Cout = and1 | and2;
endmodule
