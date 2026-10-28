`timescale 1ns/1ps
module ped_latch(input wire clk, reset_n, ped_req_async, clear_req, output reg ped_pending);
  (* ASYNC_REG="TRUE" *) reg ped_meta, ped_sync;
  always @(posedge clk or negedge reset_n)
    if (!reset_n) begin ped_meta<=0; ped_sync<=0; end
    else begin ped_meta<=ped_req_async; ped_sync<=ped_meta; end
  always @(posedge clk or negedge reset_n)
    if (!reset_n) ped_pending<=0;
    else if (clear_req) ped_pending<=0;
    else if (ped_sync) ped_pending<=1;
endmodule
