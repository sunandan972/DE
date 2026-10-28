// Structural-style register bank: explicit asynchronous-reset DFF primitive plus next-state logic.
// The combinational next-state logic is expressed behaviorally; this is not a NAND-only gate netlist.
module dff_async_n #(parameter W=1)(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk or negedge rst_n) if(!rst_n) q<={W{1'b0}}; else q<=d;
endmodule
module digital_clock_structural(
 input wire clk,rst_n,tick_1hz,set_mode,inc_min,inc_hr,
 output wire [3:0] sec_units,output wire [2:0] sec_tens,
 output wire [3:0] min_units,output wire [2:0] min_tens,
 output wire [3:0] hr_units,output wire [1:0] hr_tens,
 output wire tc_sec,tc_min,tc_hour
);
 wire run_tick=tick_1hz & ~set_mode;
 wire manual_min=set_mode & inc_min;
 wire manual_hr=set_mode & ~inc_min & inc_hr;
 assign tc_sec=(sec_units==9)&&(sec_tens==5);
 assign tc_min=(min_units==9)&&(min_tens==5);
 assign tc_hour=(hr_tens==2)&&(hr_units==3);
 reg [3:0] su_d,mu_d,hu_d;
 reg [2:0] st_d,mt_d;
 reg [1:0] ht_d;
 always @* begin
  su_d=sec_units; st_d=sec_tens; mu_d=min_units; mt_d=min_tens; hu_d=hr_units; ht_d=hr_tens;
  if(run_tick) begin
   if(sec_units==9) begin
    su_d=0;
    if(sec_tens==5) begin
     st_d=0;
     if(min_units==9) begin
      mu_d=0;
      if(min_tens==5) begin
       mt_d=0;
       if(hr_tens==2 && hr_units==3) begin ht_d=0; hu_d=0; end
       else if(hr_units==9) begin hu_d=0; ht_d=hr_tens+1'b1; end
       else hu_d=hr_units+1'b1;
      end else mt_d=min_tens+1'b1;
     end else mu_d=min_units+1'b1;
    end else st_d=sec_tens+1'b1;
   end else su_d=sec_units+1'b1;
  end else if(manual_min) begin
   if(min_units==9) begin mu_d=0; if(min_tens==5) mt_d=0; else mt_d=min_tens+1'b1; end
   else mu_d=min_units+1'b1;
  end else if(manual_hr) begin
   if(hr_tens==2 && hr_units==3) begin ht_d=0; hu_d=0; end
   else if(hr_units==9) begin hu_d=0; ht_d=hr_tens+1'b1; end
   else hu_d=hr_units+1'b1;
  end
 end
 dff_async_n #(4) u0(clk,rst_n,su_d,sec_units);
 dff_async_n #(3) u1(clk,rst_n,st_d,sec_tens);
 dff_async_n #(4) u2(clk,rst_n,mu_d,min_units);
 dff_async_n #(3) u3(clk,rst_n,mt_d,min_tens);
 dff_async_n #(4) u4(clk,rst_n,hu_d,hr_units);
 dff_async_n #(2) u5(clk,rst_n,ht_d,hr_tens);
endmodule
