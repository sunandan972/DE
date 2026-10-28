# Design Notes: 24-Hour HH:MM:SS Clock

## Register state encoding
Each digit is stored as a binary-coded decimal (BCD) value:
- seconds units SU: 4 bits, 0..9
- seconds tens ST: 3 bits, 0..5
- minutes units MU: 4 bits, 0..9
- minutes tens MT: 3 bits, 0..5
- hours units HU: 4 bits, 0..9
- hours tens HT: 2 bits, 0..2 (legal clock states 00..23 only)

## Mod-10 transition table
| Decimal | Q3 Q2 Q1 Q0 | Next Q3 Q2 Q1 Q0 |
|---:|:---:|:---:|
|0|0000|0001|
|1|0001|0010|
|2|0010|0011|
|3|0011|0100|
|4|0100|0101|
|5|0101|0110|
|6|0110|0111|
|7|0111|1000|
|8|1000|1001|
|9|1001|0000|

For a binary incrementer enabled by E, the toggle equations are:
`T0=E`, `T1=E·Q0`, `T2=E·Q1·Q0`, `T3=E·Q2·Q1·Q0`.
For a BCD decade counter, override the next-state word to 0000 at state 9. With D flip-flops, `D_i=Q_i(next)`. Invalid states 10..15 should be explicitly assigned recovery behavior in safety-critical designs.

## Mod-6 transition table
| Decimal | Q2 Q1 Q0 | Next Q2 Q1 Q0 |
|---:|:---:|:---:|
|0|000|001|
|1|001|010|
|2|010|011|
|3|011|100|
|4|100|101|
|5|101|000|

Enabled binary incrementer toggle terms: `T0=E`, `T1=E·Q0`, `T2=E·Q1·Q0`; override state 5 to 000. The compact modulo equations are best implemented by `next = (count==terminal) ? 0 : count+1` under enable. This avoids misleadingly applying a free-running binary incrementer at the terminal state.

## Flip-flop excitation tables

### D flip-flop
| Q | Q+ | D |
|---:|---:|---:|
|0|0|0|
|0|1|1|
|1|0|0|
|1|1|1|

`D=Q+`.

### T flip-flop
| Q | Q+ | T |
|---:|---:|---:|
|0|0|0|
|0|1|1|
|1|0|1|
|1|1|0|

`T=Q XOR Q+`.

### JK flip-flop
| Q | Q+ | J | K |
|---:|---:|---:|---:|
|0|0|0|X|
|0|1|1|X|
|1|0|X|1|
|1|1|X|0|

## K-map minimization guidance
Use the state tables above, place current-state bits in Gray-code order, and use invalid BCD states as don't-cares only if illegal-state recovery is not a requirement. For production/safety logic, do not use don't-cares unless the reset and fault-recovery assumptions justify them. The actual RTL uses explicit terminal comparisons rather than fragile hand-minimized equations.

## Hours rollover
The implemented clock transitions directly from 23:59:59 to 00:00:00. It does not need to represent 24. If decoding a hypothetical 24 state, the complete condition is `HT==2 && HU==4`; `HT[1] & HU[2]` alone is incomplete because it omits other bit constraints.

## Active-low seven-segment decoder
Output order `{a,b,c,d,e,f,g}`, where 0 turns a segment on:
| Digit | a b c d e f g |
|---:|:---:|
|0|0000001|
|1|1001111|
|2|0010010|
|3|0000110|
|4|1001100|
|5|0100100|
|6|0100000|
|7|0001111|
|8|0000000|
|9|0000100|
Codes 10..15 blank all segments. This truth-table implementation is synthesizable; separate minimized SOP equations depend on the chosen invalid-code behavior.

## Control table
| set_mode | inc_min | inc_hr | Action |
|---:|---:|---:|---|
|0|X|X|Normal progression when tick_1hz is high|
|1|1|X|Increment minutes on each sampled rising edge|
|1|0|1|Increment hours on each sampled rising edge|
|1|0|0|Hold time|
Manual setting pauses normal ticks. Minute increment has priority if both increment buttons are high.

## Build and simulate
```bash
iverilog -g2012 -Wall -s tb_digital_clock -o simv digital_clock_24h.v tb_digital_clock.v
vvp simv
gtkwave digital_clock.vcd
python3 logisim_clock.py --out digital_clock_24h.circ
```

## Limitations
The RTL top-level exposes digit values and terminal-count signals, not a multiplexed physical display scanner. `bcd_to_7seg.v` is a separate decoder. Add scan counter, digit-select outputs, and digit mux to drive a physical six-digit display. The Logisim generator is a labeled XML layout scaffold; it does not automatically route every wire and is not guaranteed to be simulation-ready without finishing the circuit in Logisim-evolution.
