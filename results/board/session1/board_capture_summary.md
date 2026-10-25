# On-board Signal Tap captures

| Algorithm | Scenario | Samples after reset | Seconds | T9 | NR_final (dB) |
|---|---|---|---|---|---|
| LMS | amp_steps | 28673 | 3.52 | bit-exact | 28.74 |
| LMS | path_switch | 28672 | 3.52 | bit-exact | 7.03 |
| LMS | stationary | 32768 | 4.03 | bit-exact | 18.14 |
| LMS | wav | 28674 | 3.52 | bit-exact | 18.15 |
| NLMS | amp_steps | 28672 | 3.52 | bit-exact | 27.77 |
| NLMS | path_switch | 28672 | 3.52 | bit-exact | 5.06 |
| NLMS | stationary | 28672 | 3.52 | bit-exact | 17.84 |
| NLMS | wav | 28674 | 3.52 | bit-exact | 17.09 |
| NLMS-Shift | amp_steps | 28672 | 3.52 | bit-exact | 25.69 |
| NLMS-Shift | path_switch | 28672 | 3.52 | bit-exact | 5.45 |
| NLMS-Shift | stationary | 32768 | 4.03 | bit-exact | 17.7 |
| NLMS-Shift | wav | 28672 | 3.52 | bit-exact | 14.05 |

## timing_lms.csv

- in_valid period (cycles): 6144
- sample rate (Hz): 8138.02
- in_valid to out_valid (cycles): 36
- busy high (cycles): 73

## timing_nlms.csv

- in_valid period (cycles): 6144
- sample rate (Hz): 8138.02
- in_valid to out_valid (cycles): 38
- busy high (cycles): 130

## timing_shift.csv

- in_valid period (cycles): 6144
- sample rate (Hz): 8138.02
- in_valid to out_valid (cycles): 38
- busy high (cycles): 72
