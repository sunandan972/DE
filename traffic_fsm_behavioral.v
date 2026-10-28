`timescale 1ns/1ps
module traffic_fsm_behavioral(
 input wire clk, reset_n, ped_req, timer_long, timer_short,
 output reg Main_R, Main_Y, Main_G, Ped_Walk, Ped_DontWalk,
 output wire [1:0] state_dbg, output wire ped_pending_dbg
);
 localparam [1:0] S_GREEN=2'b00,S_YELLOW=2'b01,S_PED_WALK=2'b10,S_PED_CLEAR=2'b11;
 reg [1:0] state,next_state; wire ped_pending;
 ped_latch u_latch(.clk(clk),.reset_n(reset_n),.ped_req_async(ped_req),
                   .clear_req(state==S_PED_WALK),.ped_pending(ped_pending));
 always @(posedge clk or negedge reset_n)
   if(!reset_n) state<=S_GREEN; else state<=next_state;
 always @* begin
   next_state=state;
   case(state)
    S_GREEN: if(timer_long && ped_pending) next_state=S_YELLOW;
    S_YELLOW: if(timer_short) next_state=S_PED_WALK;
    S_PED_WALK: if(timer_long) next_state=S_PED_CLEAR;
    S_PED_CLEAR: if(timer_short) next_state=S_GREEN;
    default: next_state=S_GREEN;
   endcase
 end
 always @* begin
   Main_R=0; Main_Y=0; Main_G=0; Ped_Walk=0; Ped_DontWalk=1;
   case(state)
    S_GREEN: Main_G=1;
    S_YELLOW: Main_Y=1;
    S_PED_WALK: begin Main_R=1; Ped_Walk=1; Ped_DontWalk=0; end
    S_PED_CLEAR: Main_R=1;
    default: Main_R=1;
   endcase
 end
 assign state_dbg=state; assign ped_pending_dbg=ped_pending;
endmodule
