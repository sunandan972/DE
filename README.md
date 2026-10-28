# GenAI-Assisted 24-Hour Digital Clock Package

### Included
- `digital_clock_24h.v`: behavioral synthesizable HH:MM:SS counter with asynchronous active-low reset and manual setting.
- `digital_clock_structural.v`: DFF-bank structural-style implementation and explicit next-state network.
- `bcd_to_7seg.v`: active-low seven-segment BCD decoder.
- `tb_digital_clock.v`: reset, manual setting, minute carry, and full-day rollover self-checking testbench.
- `tb_digital_clock_structural.v`: structural-style reset and minute carry testbench.
- `logisim_clock.py`: Logisim-evolution XML schematic scaffold generator.
- `design_notes.md`: transition tables, D/T/JK excitation tables, equations, decoder table, and execution guide.

### Simulation
Install Icarus Verilog, then:
```bash
iverilog -g2012 -Wall -s tb_digital_clock -o simv digital_clock_24h.v tb_digital_clock.v
vvp simv
gtkwave digital_clock.vcd
```
Structural-style check:
```bash
iverilog -g2012 -Wall -s tb_digital_clock_structural -o simv digital_clock_structural.v tb_digital_clock_structural.v
vvp simv
```
Generate a Logisim XML scaffold:
```bash
python3 logisim_clock.py --out digital_clock_24h.circ
```

### Design assumptions and limitations
`tick_1hz` is an enable sampled by `clk`, not a generated clock. Manual increment advances once per rising edge while the button is sampled high; debouncing/edge detection is not included. The behavioral clock is the reference model. The structural-style version uses explicit DFF primitives, but its next-state logic remains in combinational procedural code and is not a primitive-by-primitive NAND-only netlist. The Logisim exporter creates labeled component placements but does not route every wire; inspect and finish the schematic in Logisim. The top-level has no digit-scan multiplexing output; the decoder is separate. This is a reproducible educational baseline, not a certified production ASIC/FPGA package.
