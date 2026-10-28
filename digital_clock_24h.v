`timescale 1ns/1ps
// Single-clock 24-hour HH:MM:SS counter. tick_1hz is a clock enable, not a generated clock.
// rst_n is active-low asynchronous reset. set_mode pauses normal ticks.
module digital_clock_24h(
 input wire clk, rst_n, tick_1hz, set_mode, inc_min, inc_hr,
 output reg [3:0] sec_units, output reg [2:0] sec_tens,
 output reg [3:0] min_units, output reg [2:0] min_tens,
 output reg [3:0] hr_units, output reg [1:0] hr_tens,
 output wire tc_sec, tc_min, tc_hour
);
 wire run_tick = tick_1hz & ~set_mode;
 wire manual_min = set_mode & inc_min;
 wire manual_hr = set_mode & ~inc_min & inc_hr;
 assign tc_sec = (sec_units==9) && (sec_tens==5);
 assign tc_min = (min_units==9) && (min_tens==5);
 assign tc_hour = (hr_tens==2) && (hr_units==3);

 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
   sec_units<=0; sec_tens<=0; min_units<=0; min_tens<=0; hr_units<=0; hr_tens<=0;
  end else if (run_tick) begin
   if (sec_units==9) begin
    sec_units<=0;
    if (sec_tens==5) begin
     sec_tens<=0;
     if (min_units==9) begin
      min_units<=0;
      if (min_tens==5) begin
       min_tens<=0;
       if (hr_tens==2 && hr_units==3) begin hr_tens<=0; hr_units<=0; end
       else if (hr_units==9) begin hr_units<=0; hr_tens<=hr_tens+1'b1; end
       else hr_units<=hr_units+1'b1;
      end else min_tens<=min_tens+1'b1;
     end else min_units<=min_units+1'b1;
    end else sec_tens<=sec_tens+1'b1;
   end else sec_units<=sec_units+1'b1;
  end else if (manual_min) begin
   if (min_units==9) begin
    min_units<=0;
    if (min_tens==5) min_tens<=0; else min_tens<=min_tens+1'b1;
   end else min_units<=min_units+1'b1;
  end else if (manual_hr) begin
   if (hr_tens==2 && hr_units==3) begin hr_tens<=0; hr_units<=0; end
   else if (hr_units==9) begin hr_units<=0; hr_tens<=hr_tens+1'b1; end
   else hr_units<=hr_units+1'b1;
  end
 end
endmodule
