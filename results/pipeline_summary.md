# Research Results: Adaptive Noise Cancellation (ANC)
**Target Hardware:** Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7) | **Pipeline:** Python Software Simulation & Verification
N=16000 samples @ 8000 Hz, Filter Length L=32, Scenarios: stationary, amp_steps, path_switch, wav, feedback; WAV: `acoustic_chord.wav`
Eval seeds [1]; tuning seed 100.

## 1. Tuned Step Sizes (Optimal shared parameter per algorithm)

| Algorithm | mu | Grid Points Evaluated |
|---|---|---|
| lms | 0.25 | 7 |
| nlms | 0.25 | 7 |
| nlms_shift | 0.125 | 5 |

## 2. Floating-Point Performance Across Scenarios

| Scenario | Algorithm | NR Final (dB) | NR Whole-Run (dB) | Settling Time (ms) | Tracking Time (ms) | Misalignment (dB) | Diverged |
|---|---|---|---|---|---|---|---|
| stationary | lms | 22.8 ± 0.0 | 13.3 | 1462 | n/a | -23.2 | 0 |
| stationary | nlms | 19.0 ± 0.0 | 15.7 | 1782 | n/a | -25.0 | 0 |
| stationary | nlms_shift | 22.8 ± 0.0 | 13.2 | 1462 | n/a | -23.1 | 0 |
| amp_steps | lms | 22.0 ± 0.0 | 17.1 | 398 | 137 | -29.7 | 0 |
| amp_steps | nlms | 16.9 ± 0.0 | 20.0 | 486 | 446 | -24.1 | 0 |
| amp_steps | nlms_shift | 22.4 ± 0.0 | 17.0 | 397 | 176 | -26.6 | 0 |
| path_switch | lms | 19.6 ± 0.0 | 9.6 | 635 | 590 | -12.2 | 0 |
| path_switch | nlms | 20.4 ± 0.0 | 12.9 | 554 | 787 | -21.1 | 0 |
| path_switch | nlms_shift | 19.6 ± 0.0 | 9.6 | 635 | 590 | -12.2 | 0 |
| wav | lms | 3.9 ± 0.0 | 10.4 | 133 | n/a | -3.8 | 0 |
| wav | nlms | 3.0 ± 0.0 | 10.6 | 123 | n/a | -4.0 | 0 |
| wav | nlms_shift | 3.8 ± 0.0 | 8.9 | 117 | n/a | -3.5 | 0 |
| feedback | lms | 4.3 ± 0.0 | 4.0 | 0 | n/a | 2.8 | 0 |
| feedback | nlms | 4.2 ± 0.0 | 4.1 | 0 | n/a | 3.2 | 0 |
| feedback | nlms_shift | 4.3 ± 0.0 | 4.0 | 0 | n/a | 2.8 | 0 |

## 3. Fixed-Point Precision Sweep (W = 8 to 24 bits)

| Word Length W | lms | nlms | nlms_shift |
|---|---|---|---|
| 8 | 4.3 dB / +10.19 deg / 0 ovf | 4.0 dB / +8.75 deg / 0 ovf | 4.3 dB / +10.29 deg / 0 ovf |
| 10 | 11.8 dB / +2.76 deg / 0 ovf | 12.0 dB / +0.66 deg / 0 ovf | 12.4 dB / +2.16 deg / 0 ovf |
| 12 | 14.8 dB / -0.23 deg / 0 ovf | 15.4 dB / -2.65 deg / 0 ovf | 15.3 dB / -0.75 deg / 0 ovf |
| 14 | 14.6 dB / -0.11 deg / 0 ovf | 14.6 dB / -1.94 deg / 0 ovf | 14.6 dB / -0.07 deg / 0 ovf |
| 16 | 14.6 dB / -0.04 deg / 0 ovf | 14.6 dB / -1.89 deg / 0 ovf | 14.6 dB / -0.06 deg / 0 ovf |
| 20 | 14.5 dB / -0.00 deg / 0 ovf | 14.5 dB / -1.84 deg / 0 ovf | 14.6 dB / -0.00 deg / 0 ovf |
| 24 | 14.5 dB / -0.00 deg / 0 ovf | 14.5 dB / -1.84 deg / 0 ovf | 14.6 dB / -0.00 deg / 0 ovf |

## 4. Hardware Candidates for DE2-115 Cyclone IV E

| Algorithm | W (bits) | mu | Fixed NR (dB) | Float NR (dB) | Degradation (dB) | Overflows | Arithmetic Architecture |
|---|---|---|---|---|---|---|---|
| nlms | 12 | 0.25 | 15.4 | 12.7 | -2.65 | 0 | 2L+3 mult + 1 divider (or reciprocal) |
| nlms_shift | 12 | 0.125 | 15.3 | 14.6 | -0.75 | 0 | 2L mult, leading-one detect + barrel shift, no divider/mu-mult |
| lms | 12 | 0.25 | 14.8 | 14.5 | -0.23 | 0 | 2L+1 mult, no divider |

## 5. Accumulator Ablation

| Algorithm | W | Accumulator Bits | Mean NR (dB) | Accumulator Saturations | Total Overflows |
|---|---|---|---|---|---|
| nlms | 12 | 29 | 15.4 | 0 | 0 |
| nlms | 12 | 24 | 15.4 | 0 | 0 |
| nlms | 12 | 22 | 15.4 | 10 | 10 |
| nlms | 12 | 20 | 8.0 | 9114 | 12669 |
| nlms_shift | 12 | 29 | 15.3 | 0 | 0 |
| nlms_shift | 12 | 24 | 15.3 | 0 | 0 |
| nlms_shift | 12 | 22 | 15.3 | 8 | 8 |
| nlms_shift | 12 | 20 | 8.2 | 9200 | 12000 |
| lms | 12 | 29 | 14.8 | 0 | 0 |
| lms | 12 | 24 | 14.8 | 0 | 0 |
| lms | 12 | 22 | 14.8 | 10 | 10 |
| lms | 12 | 20 | 7.8 | 9653 | 14360 |

## 6. Generated Publication Figures
- `results/plots/fig1_convergence.{png,pdf}`: Convergence curves across scenarios
- `results/plots/fig2_waveforms.{png,pdf}`: Time-domain audio waveforms
- `results/plots/fig3_residual_error.{png,pdf}`: Residual error power over time
- `results/plots/fig4_tracking_response.{png,pdf}`: Dynamic tracking during disturbance
- `results/plots/fig5_noise_reduction_comparison.{png,pdf}`: Quantitative NR across all scenarios
- `results/plots/fig6_bitwidth_sweep.{png,pdf}`: Cancellation quality & SQNR vs word length
- `results/plots/fig7_coef_trajectories.{png,pdf}`: Evolution of filter tap weights
- `results/plots/fig8_resource_utilization.{png,pdf}`: Cyclone IV E LEs & Multipliers
- `results/plots/fig9_timing_comparison.{png,pdf}`: Fmax & Timing Slack
- `results/plots/fig10_performance_cost_tradeoff.{png,pdf}`: Quality vs FPGA Resource Trade-off
- `results/plots/fig11_latency_comparison.{png,pdf}`: Processing latency & timing budget comparison

## 7. Hardware & Quartus Status
- **Target Device:** Intel/Altera Cyclone IV E `EP4CE115F29C7` (Terasic DE2-115 board, Speed Grade 7)
- **Quartus Prime Lite 25.1std Compilation:** Complete & Verified across all 3 architectures.
- **LMS (W=12):** 1,885 LEs (1.65%), 1,148 registers, Fmax = 59.90 MHz, Setup Slack = +3.305 ns (PASS)
- **NLMS (W=12):** 2,697 LEs (2.36%), 1,425 registers, Fmax = 61.72 MHz, Setup Slack = +3.798 ns (PASS)
- **NLMS-Shift (W=12):** 2,690 LEs (2.35%), 1,213 registers, Fmax = 61.98 MHz, Setup Slack = +3.867 ns (PASS)
- **Gate B Timing Closure:** PASSED (all worst-case slow 85°C setup slacks >= +3.0 ns, exceeding +0.5 ns target).
