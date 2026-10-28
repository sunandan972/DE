`timescale 1ns/1ps
module tb_traffic_fsm;
 reg clk=0,reset_n=0,ped_req=0,timer_long=0,timer_short=0;
 wire Main_R,Main_Y,Main_G,Ped_Walk,Ped_DontWalk;
 wire [1:0] state_dbg; wire ped_pending_dbg; integer errors=0;
 localparam GREEN=0,YELLOW=1,WALK=2,CLEAR=3;
 traffic_fsm_behavioral dut(.*);
 always #5 clk=~clk;
 task check(input condition,input [255:0] msg);
 begin if(!condition) begin $display("FAIL %0t %0s",$time,msg); errors=errors+1; end
 else $display("PASS %0t %0s",$time,msg); end endtask
 task tick; begin @(posedge clk); #1; end endtask
 initial begin
  $dumpfile("traffic_fsm.vcd"); $dumpvars(0,tb_traffic_fsm);
  #2; reset_n=0; #2;
  check(state_dbg==GREEN && Main_G && Ped_DontWalk,"active-low reset enters GREEN");
  repeat(2) tick(); reset_n=1; tick();
  timer_long=1; repeat(2) tick(); timer_long=0;
  check(state_dbg==GREEN && Main_G,"no pedestrian request holds GREEN");
  timer_short=1; tick(); timer_short=0;
  check(state_dbg==GREEN,"short timer alone does not leave GREEN");
  #2 ped_req=1; repeat(3) tick();
  check(ped_pending_dbg,"async request synchronizes and latches");
  timer_long=1; tick(); timer_long=0;
  check(state_dbg==YELLOW && Main_Y,"request plus long timer enters YELLOW");
  timer_short=1; tick(); timer_short=0;
  check(state_dbg==WALK && Main_R && Ped_Walk && !Ped_DontWalk,"yellow enters WALK");
  ped_req=0; tick(); check(!ped_pending_dbg,"request clears during WALK");
  timer_long=1; tick(); timer_long=0;
  check(state_dbg==CLEAR && Main_R && !Ped_Walk,"walk timeout enters clearance");
  timer_short=1; tick(); timer_short=0;
  check(state_dbg==GREEN && Main_G,"clearance timeout returns GREEN");
  check(!(Main_R&&Main_Y)&&!(Main_R&&Main_G)&&!(Main_Y&&Main_G),"vehicle lamps mutually exclusive");
  if(errors==0) $display("ALL TESTS PASSED"); else $display("FAILURES=%0d",errors);
  $finish;
 end
endmodule
