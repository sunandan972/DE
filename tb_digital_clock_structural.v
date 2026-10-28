`timescale 1ns/1ps
module tb_digital_clock_structural;
 reg clk=0,rst_n=1,tick_1hz=0,set_mode=0,inc_min=0,inc_hr=0;
 wire [3:0] su,mu,hu; wire [2:0] st,mt; wire [1:0] ht; wire tc_sec,tc_min,tc_hour;
 integer i;
 digital_clock_structural dut(clk,rst_n,tick_1hz,set_mode,inc_min,inc_hr,su,st,mu,mt,hu,ht,tc_sec,tc_min,tc_hour);
 always #5 clk=~clk;
 initial begin
  #1 rst_n=0; #1;
  if({ht,hu,mt,mu,st,su}!==24'd0) $fatal(1,"Reset failure");
  @(negedge clk); rst_n=1;
  for(i=0;i<60;i=i+1) begin @(negedge clk); tick_1hz=1; @(negedge clk); tick_1hz=0; end
  if({mt,mu,st,su}!=={3'd0,4'd1,3'd0,4'd0}) $fatal(1,"Minute carry failure");
  $display("PASS structural-style reset and 60-tick carry"); $finish;
 end
endmodule
