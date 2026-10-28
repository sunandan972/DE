`timescale 1ns/1ps
module tb_digital_clock;
 reg clk=0,rst_n=1,tick_1hz=0,set_mode=0,inc_min=0,inc_hr=0;
 wire [3:0] su,mu,hu; wire [2:0] st,mt; wire [1:0] ht;
 wire tc_sec,tc_min,tc_hour;
 integer i;
 digital_clock_24h dut(clk,rst_n,tick_1hz,set_mode,inc_min,inc_hr,
   su,st,mu,mt,hu,ht,tc_sec,tc_min,tc_hour);
 always #5 clk=~clk;
 task tick; begin @(negedge clk); tick_1hz=1; @(negedge clk); tick_1hz=0; end endtask
 task min_press; begin @(negedge clk); set_mode=1; inc_min=1; @(negedge clk); inc_min=0; set_mode=0; end endtask
 task hr_press; begin @(negedge clk); set_mode=1; inc_hr=1; @(negedge clk); inc_hr=0; set_mode=0; end endtask
 task check_zero; begin
  if ({ht,hu,mt,mu,st,su} !== 24'd0) $fatal(1,"Expected 00:00:00");
 end endtask
 initial begin
  $dumpfile("digital_clock.vcd"); $dumpvars(0,tb_digital_clock);
  #1 rst_n=0; #1; check_zero(); $display("PASS reset to 00:00:00");
  @(negedge clk); rst_n=1;
  min_press();
  if (mu!==1 || mt!==0) $fatal(1,"Manual minute increment failed");
  hr_press();
  if (hu!==1 || ht!==0) $fatal(1,"Manual hour increment failed");
  $display("PASS manual minute/hour setting");
  #1 rst_n=0; #1; @(negedge clk); rst_n=1;
  for(i=0;i<60;i=i+1) tick();
  if ({mt,mu,st,su} !== {3'd0,4'd1,3'd0,4'd0}) $fatal(1,"Minute carry at 60 ticks failed");
  $display("PASS seconds 59 -> 00 and minutes 00 -> 01");
  #1 rst_n=0; #1; @(negedge clk); rst_n=1;
  for(i=0;i<86400;i=i+1) tick();
  check_zero();
  $display("PASS full 24-hour rollover after 86400 ticks");
  $display("ALL TESTS PASSED"); $finish;
 end
 initial begin #20000000; $fatal(1,"Timeout"); end
endmodule
