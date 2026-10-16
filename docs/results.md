# Research Results: Adaptive Noise Cancellation (ANC)
**Target Hardware:** Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7) | **Pipeline:** Python Software Simulation & Verification
N=16000 samples @ 8000 Hz, Filter Length L=32, Scenarios: stationary, amp_steps, path_switch, wav; WAV: `acoustic_chord.wav`
Eval seeds [1]; tuning seed 100.

## 1. Tuned Step Sizes (Optimal shared parameter per algorithm)

| Algorithm | mu | Grid Points Evaluated |
|---|---|---|
| lms | 0.3159 | 7 |
| nlms | 0.04642 | 7 |
| nlms_shift | 0.0625 | 5 |

## 2. Floating-Point Performance Across Scenarios

| Scenario | Algorithm | NR Final (dB) | NR Whole-Run (dB) | Settling Time (ms) | Tracking Time (ms) | Misalignment (dB) | Diverged |
|---|---|---|---|---|---|---|---|
| stationary | lms | 22.3 ± 0.0 | 14.0 | 1525 | n/a | -25.9 | 0 |
| stationary | nlms | 20.6 ± 0.0 | 15.8 | 1791 | n/a | -26.9 | 0 |
| stationary | nlms_shift | 20.7 ± 0.0 | 15.6 | 1791 | n/a | -26.9 | 0 |
| amp_steps | lms | 21.2 ± 0.0 | 17.7 | 435 | 109 | -28.7 | 0 |
| amp_steps | nlms | 9.4 ± 0.0 | 19.8 | 472 | 463 | -16.0 | 0 |
| amp_steps | nlms_shift | 9.4 ± 0.0 | 19.6 | 469 | 462 | -16.2 | 0 |
| path_switch | lms | 20.4 ± 0.0 | 10.4 | 668 | 646 | -13.7 | 0 |
| path_switch | nlms | 20.9 ± 0.0 | 12.0 | 640 | 690 | -17.1 | 0 |
| path_switch | nlms_shift | 21.0 ± 0.0 | 11.8 | 643 | 674 | -17.1 | 0 |
| wav | lms | 4.5 ± 0.0 | 10.8 | 134 | n/a | -3.9 | 0 |
| wav | nlms | -10.9 ± 0.0 | 8.0 | 0 | n/a | -1.4 | 0 |
| wav | nlms_shift | -11.3 ± 0.0 | 7.9 | 0 | n/a | -1.3 | 0 |

## 3. Fixed-Point Precision Sweep (W = 8 to 24 bits)

| Word Length W | lms | nlms | nlms_shift |
|---|---|---|---|
| 8 | 5.3 dB / +11.79 deg / 0 ovf | 4.5 dB / +5.53 deg / 0 ovf | 3.2 dB / +6.74 deg / 0 ovf |
| 10 | 15.3 dB / +1.80 deg / 0 ovf | 9.8 dB / +0.22 deg / 0 ovf | 9.8 dB / +0.11 deg / 0 ovf |
| 12 | 17.0 dB / +0.08 deg / 0 ovf | 10.0 dB / -0.00 deg / 0 ovf | 10.0 dB / -0.04 deg / 0 ovf |
| 14 | 17.3 dB / -0.18 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 16 | 17.1 dB / -0.04 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 20 | 17.1 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |
| 24 | 17.1 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |

## 4. Hardware Candidates for DE2-115 Cyclone IV E

| Algorithm | W (bits) | mu | Fixed NR (dB) | Float NR (dB) | Degradation (dB) | Overflows | Arithmetic Architecture |
|---|---|---|---|---|---|---|---|
| lms | 12 | 0.3159 | 17.0 | 17.1 | +0.08 | 0 | 2L+1 mult, no divider |

## 5. Accumulator Ablation

| Algorithm | W | Accumulator Bits | Mean NR (dB) | Accumulator Saturations | Total Overflows |
|---|---|---|---|---|---|
| lms | 12 | 29 | 17.0 | 0 | 0 |
| lms | 12 | 24 | 17.0 | 0 | 0 |
| lms | 12 | 22 | 17.0 | 11 | 11 |
| lms | 12 | 20 | 8.6 | 4710 | 8955 |

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

## 7. Hardware & Quartus Status
- **Target Device:** Intel/Altera Cyclone IV E `EP4CE115F29C7` (Terasic DE2-115 board)
- **Quartus Prime Lite Compilation:** Pending local tool installation. Hardware figures marked UNAVAILABLE without fabrication.
- **Import Template:** `results/quartus/quartus_reports_template.csv` available for automated import via `py/import_quartus.py`.
