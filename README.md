# Traffic Light Controller FSM with Pedestrian Request

## State encoding and outputs
| State | Q1Q0 | Main_R | Main_Y | Main_G | Ped_Walk | Ped_DontWalk |
|---|---|---:|---:|---:|---:|---:|
| S_GREEN | 00 | 0 | 0 | 1 | 0 | 1 |
| S_YELLOW | 01 | 0 | 1 | 0 | 0 | 1 |
| S_PED_WALK | 10 | 1 | 0 | 0 | 1 | 0 |
| S_PED_CLEAR | 11 | 1 | 0 | 0 | 0 | 1 |

Let P=ped_pending, L=timer_long, S=timer_short. Decodes:
G=~Q1~Q0, Y=~Q1 Q0, W=Q1~Q0, C=Q1Q0.
Transitions: T_GY=G L P; T_YW=Y S; T_WC=W L; T_CG=C S.
Holds: H_G=G ~(LP); H_Y=Y ~S; H_W=W ~L; H_C=C ~S.
D1=T_YW+T_WC+H_W+H_C.
D0=T_GY+H_Y+T_WC+H_C.
Outputs: Main_R=Q1; Main_Y=~Q1 Q0; Main_G=~Q1~Q0;
Ped_Walk=Q1~Q0; Ped_DontWalk=~Ped_Walk.

These are minimized sum-of-products using decoded state/transition terms. For JK FFs, use the excitation mapping per bit:
| Q | Q+ | J | K |
|---:|---:|---:|---:|
| 0 | 0 | 0 | X |
| 0 | 1 | 1 | X |
| 1 | 0 | X | 1 |
| 1 | 1 | X | 0 |

## Run with Icarus Verilog
```bash
iverilog -g2012 -Wall -s tb_traffic_fsm -o simv traffic_fsm_behavioral.v ped_latch.v tb_traffic_fsm.v
vvp simv
gtkwave traffic_fsm.vcd
```
For structural implementation:
```bash
iverilog -g2012 -Wall -s tb_traffic_fsm -o simv traffic_fsm_structural.v ped_latch.v tb_traffic_fsm.v
```
Note: change the testbench instance module name from `traffic_fsm_behavioral` to `traffic_fsm_structural` for that run.

## Logisim
```bash
python3 logisim_fsm.py -o traffic_fsm.circ
```
Open the file using File > Open in Logisim. It is a visual scaffold rather than a fully wired/validated schematic because component XML schemas and pin geometry vary by Logisim release. Inspect and wire it in your exact target version before simulation.

## Assumptions and safety
`timer_long` and `timer_short` are synchronous elapsed-timer indicators. GREEN holds until both timer_long and a latched request are true. The asynchronous request passes through a two-flop synchronizer; mechanical switch debouncing is not included. This example is educational and is not a certified traffic controller; real deployments need conflict monitoring, fail-safe modes, compliant timing and independent safety validation.
