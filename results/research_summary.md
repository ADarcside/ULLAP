# Research Results: Adaptive Noise Cancellation (ANC)
**Target Hardware:** Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7) | **Pipeline:** Python Software Simulation & Verification
N=16000 samples @ 8000 Hz, Filter Length L=32, Scenarios: stationary, amp_steps, path_switch, wav; WAV: `acoustic_chord.wav`
Eval seeds [1, 2, 3]; tuning seed 100.

## 1. Tuned Step Sizes (Optimal shared parameter per algorithm)

| Algorithm | mu | Grid Points Evaluated |
|---|---|---|
| lms | 0.5009 | 14 |
| nlms | 0.04642 | 13 |
| nlms_shift | 0.0625 | 9 |

## 2. Floating-Point Performance Across Scenarios

| Scenario | Algorithm | NR Final (dB) | NR Whole-Run (dB) | Settling Time (ms) | Tracking Time (ms) | Misalignment (dB) | Diverged |
|---|---|---|---|---|---|---|---|
| stationary | lms | 20.3 ± 0.6 | 15.2 | 1784 | n/a | -26.2 | 0 |
| stationary | nlms | 20.7 ± 0.4 | 15.7 | 1791 | n/a | -26.6 | 0 |
| stationary | nlms_shift | 20.8 ± 0.5 | 15.5 | 1791 | n/a | -26.6 | 0 |
| amp_steps | lms | 18.9 ± 0.7 | 18.5 | 484 | 74 | -25.8 | 0 |
| amp_steps | nlms | 9.4 ± 0.5 | 19.7 | 476 | 463 | -15.7 | 0 |
| amp_steps | nlms_shift | 9.5 ± 0.4 | 19.5 | 469 | 462 | -15.9 | 0 |
| path_switch | lms | 20.6 ± 0.3 | 12.0 | 722 | 706 | -17.3 | 0 |
| path_switch | nlms | 20.7 ± 0.2 | 11.8 | 698 | 690 | -16.5 | 0 |
| path_switch | nlms_shift | 20.6 ± 0.3 | 11.6 | 694 | 674 | -16.3 | 0 |
| wav | lms | 5.4 ± 0.1 | 11.2 | 134 | n/a | -4.1 | 0 |
| wav | nlms | -10.9 ± 0.1 | 8.0 | 0 | n/a | -1.4 | 0 |
| wav | nlms_shift | -11.3 ± 0.1 | 7.9 | 0 | n/a | -1.3 | 0 |

## 3. Fixed-Point Precision Sweep (W = 8 to 24 bits)

| Word Length W | lms | nlms | nlms_shift |
|---|---|---|---|
| 8 | 7.4 dB / +9.19 deg / 0 ovf | 4.5 dB / +5.53 deg / 0 ovf | 3.2 dB / +6.74 deg / 0 ovf |
| 9 | 12.7 dB / +3.82 deg / 0 ovf | 8.8 dB / +1.25 deg / 0 ovf | 8.4 dB / +1.55 deg / 0 ovf |
| 10 | 15.1 dB / +1.51 deg / 0 ovf | 9.8 dB / +0.22 deg / 0 ovf | 9.8 dB / +0.11 deg / 0 ovf |
| 11 | 16.1 dB / +0.46 deg / 0 ovf | 9.9 dB / +0.11 deg / 0 ovf | 9.7 dB / +0.20 deg / 0 ovf |
| 12 | 16.0 dB / +0.56 deg / 0 ovf | 10.0 dB / -0.00 deg / 0 ovf | 10.0 dB / -0.04 deg / 0 ovf |
| 13 | 17.1 dB / -0.49 deg / 0 ovf | 9.9 dB / +0.06 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 14 | 17.0 dB / -0.48 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 15 | 16.6 dB / -0.05 deg / 0 ovf | 10.0 dB / +0.02 deg / 0 ovf | 9.9 dB / -0.01 deg / 0 ovf |
| 16 | 16.6 dB / +0.01 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 17 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |
| 18 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |
| 19 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 20 | 16.6 dB / -0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |
| 21 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 22 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / +0.00 deg / 0 ovf |
| 23 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |
| 24 | 16.6 dB / +0.00 deg / 0 ovf | 10.0 dB / +0.03 deg / 0 ovf | 9.9 dB / -0.00 deg / 0 ovf |

## 4. Hardware Candidates for DE2-115 Cyclone IV E

| Algorithm | W (bits) | mu | Fixed NR (dB) | Float NR (dB) | Degradation (dB) | Overflows | Arithmetic Architecture |
|---|---|---|---|---|---|---|---|
| lms | 11 | 0.5009 | 16.1 | 16.6 | +0.46 | 0 | 2L+1 mult, no divider |

## 5. Accumulator Ablation

| Algorithm | W | Accumulator Bits | Mean NR (dB) | Accumulator Saturations | Total Overflows |
|---|---|---|---|---|---|
| lms | 11 | 27 | 16.1 | 0 | 0 |
| lms | 11 | 22 | 16.1 | 0 | 0 |
| lms | 11 | 20 | 16.2 | 12 | 12 |
| lms | 11 | 18 | 8.4 | 4952 | 9430 |

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
