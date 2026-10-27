# Board session 2

| Algorithm | Scenario | T9 | NR board (dB) | NR model, same signal (dB) | Difference | NR model at the board's input level (dB) | Difference |
|---|---|---|---|---|---|---|---|
| LMS | amp_steps | bit-exact | 17.13 | 27.71 | -10.58 | 25.23 | -8.1 |
| LMS | path_switch | bit-exact | 14.67 | 19.84 | -5.18 | 14.47 | 0.2 |
| LMS | stationary | bit-exact | 15.88 | 22.77 | -6.89 | 15.76 | 0.11 |
| LMS | wav | bit-exact | 5.99 | 9.11 | -3.12 | 7.78 | -1.78 |
| NLMS | amp_steps | bit-exact | 16.76 | 27.19 | -10.42 | 23.64 | -6.88 |
| NLMS | path_switch | bit-exact | 14.03 | 19.06 | -5.03 | 14.04 | -0.01 |
| NLMS | stationary | bit-exact | 15.65 | 21.6 | -5.95 | 15.53 | 0.12 |
| NLMS | wav | bit-exact | 5.8 | 8.72 | -2.92 | 7.45 | -1.65 |
| NLMS-Shift | amp_steps | bit-exact | 16.57 | 25.79 | -9.22 | 22.1 | -5.53 |
| NLMS-Shift | path_switch | bit-exact | 14.4 | 19.86 | -5.46 | 14.44 | -0.04 |
| NLMS-Shift | stationary | bit-exact | 15.8 | 22.68 | -6.87 | 15.78 | 0.02 |
| NLMS-Shift | wav | bit-exact | 5.46 | 8.63 | -3.18 | 7.32 | -1.87 |

- Freeze (NLMS-Shift, stationary): bit-exact with freeze on from sample 13703 (1.68 s after reset), 1.44 s into the scenario; NR 15.4 dB in the 0.25 s before the switch, 15.2 dB frozen from the switch to the end of the scenario (15.9 dB if adaptation had continued)
- DAC word, ANC (SW[0] = 0): = {e, 0000}: PASS, 1792 samples match, 0 differ
- DAC word, bypass (SW[0] = 1): top 12 bits = d: PASS, 1792 samples match, 0 differ
- GPIO timing at the end of the 10-minute soak: in_valid period (cycles) 6144, sample rate (Hz) 8138.02, in_valid to out_valid (cycles) 38, busy high (cycles) 72
