# State and excitation reference

## State transitions
| Present state | Condition | Next state |
|---|---|---|
| GREEN (00) | `timer_long & ped_pending` | YELLOW (01) |
| GREEN (00) | otherwise | GREEN (00) |
| YELLOW (01) | `timer_short` | PED_WALK (10) |
| YELLOW (01) | otherwise | YELLOW (01) |
| PED_WALK (10) | `timer_long` | PED_CLEAR (11) |
| PED_WALK (10) | otherwise | PED_WALK (10) |
| PED_CLEAR (11) | `timer_short` | GREEN (00) |
| PED_CLEAR (11) | otherwise | PED_CLEAR (11) |

## Compact excitation table
| State | Q1Q0 | Condition | Q1+Q0+ | D1D0 |
|---|---|---|---|---|
| GREEN | 00 | `L P=0` | 00 | 00 |
| GREEN | 00 | `L P=1` | 01 | 01 |
| YELLOW | 01 | `S=0` | 01 | 01 |
| YELLOW | 01 | `S=1` | 10 | 10 |
| PED_WALK | 10 | `L=0` | 10 | 10 |
| PED_WALK | 10 | `L=1` | 11 | 11 |
| PED_CLEAR | 11 | `S=0` | 11 | 11 |
| PED_CLEAR | 11 | `S=1` | 00 | 00 |

`D1=Q1+`, `D0=Q0+`. State outputs are in README.md. Since `timer_long` and `timer_short` are state-qualified, unspecified timer combinations do not cause transitions outside their listed states.
