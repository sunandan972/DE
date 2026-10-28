// Active-low output order {a,b,c,d,e,f,g}. Invalid BCD codes blank the display.
module bcd_to_7seg(input wire [3:0] bcd, output reg [6:0] seg_n);
 always @* begin
  case (bcd)
   0: seg_n=7'b0000001; 1: seg_n=7'b1001111;
   2: seg_n=7'b0010010; 3: seg_n=7'b0000110;
   4: seg_n=7'b1001100; 5: seg_n=7'b0100100;
   6: seg_n=7'b0100000; 7: seg_n=7'b0001111;
   8: seg_n=7'b0000000; 9: seg_n=7'b0000100;
   default: seg_n=7'b1111111;
  endcase
 end
endmodule
