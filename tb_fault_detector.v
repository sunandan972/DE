`timescale 1ns/1ps
module tb_fault_detector;
    reg A, B, Cin;
    wire gSum, gCout, fSum, fCout;
    integer i, errors, detected;
    reg expected_sum, expected_cout;

    golden_circuit golden(.A(A), .B(B), .Cin(Cin), .Sum(gSum), .Cout(gCout));
    // Default injected fault: Sum stuck-at-0. Change FAULT_MODE to test other modes.
    faulty_circuit #(.FAULT_ENABLE(1), .FAULT_MODE(1)) faulty(
        .A(A), .B(B), .Cin(Cin), .Sum(fSum), .Cout(fCout)
    );

    initial begin
        errors = 0;
        detected = 0;
        $display("A B Cin | GSum GCout | FSum FCout | mismatch");
        for (i = 0; i < 8; i = i + 1) begin
            {A, B, Cin} = i[2:0];
            #1;
            expected_sum = A ^ B ^ Cin;
            expected_cout = (A & B) | ((A ^ B) & Cin);
            if (gSum !== expected_sum || gCout !== expected_cout) begin
                $display("ERROR: golden mismatch for vector %0d", i);
                errors = errors + 1;
            end
            if ((fSum !== gSum) || (fCout !== gCout))
                detected = detected + 1;
            $display("%b %b  %b  |  %b    %b   |  %b    %b   | %b",
                     A, B, Cin, gSum, gCout, fSum, fCout,
                     ((fSum !== gSum) || (fCout !== gCout)));
        end
        if (errors == 0) $display("PASS: golden circuit matches reference equation on all 8 vectors.");
        else $fatal(1, "FAIL: golden circuit has %0d mismatch(es).", errors);
        if (detected == 0) $fatal(1, "FAIL: selected injected fault was not detected.");
        else $display("PASS: fault detected on %0d of 8 vectors.", detected);
        $finish;
    end
endmodule
