`timescale 1ns/1ps
module traffic_fsm_structural(
 input wire clk,reset_n,ped_req,timer_long,timer_short,
 output wire Main_R,Main_Y,Main_G,Ped_Walk,Ped_DontWalk,
 output wire [1:0] state_dbg, output wire ped_pending_dbg
);
 wire q1,q0,d1,d0,nq1,nq0,G,Y,W,C,P;
 wire T_GY,T_YW,T_WC,T_CG,H_G,H_Y,H_W,H_C;
 assign nq1=~q1; assign nq0=~q0;
 assign G=nq1&nq0; assign Y=nq1&q0; assign W=q1&nq0; assign C=q1&q0;
 ped_latch u_latch(.clk(clk),.reset_n(reset_n),.ped_req_async(ped_req),
                   .clear_req(W),.ped_pending(P));
 assign T_GY=G&timer_long&P; assign T_YW=Y&timer_short;
 assign T_WC=W&timer_long; assign T_CG=C&timer_short;
 assign H_G=G&~(timer_long&P); assign H_Y=Y&~timer_short;
 assign H_W=W&~timer_long; assign H_C=C&~timer_short;
 assign d1=T_YW|T_WC|H_W|H_C;
 assign d0=T_GY|H_Y|T_WC|H_C;
 dff_async_reset ff1(.clk(clk),.reset_n(reset_n),.d(d1),.q(q1));
 dff_async_reset ff0(.clk(clk),.reset_n(reset_n),.d(d0),.q(q0));
 assign Main_R=q1; assign Main_Y=Y; assign Main_G=G;
 assign Ped_Walk=W; assign Ped_DontWalk=~W;
 assign state_dbg={q1,q0}; assign ped_pending_dbg=P;
endmodule
module dff_async_reset(input wire clk,reset_n,d,output reg q);
 always @(posedge clk or negedge reset_n)
   if(!reset_n) q<=1'b0; else q<=d;
endmodule
