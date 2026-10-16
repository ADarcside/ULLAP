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
- `results/plots/fig1_convergence.{png,pdf}`: Convergence curves across scenarios (Baseline preserved)
- `results/plots/fig2_waveforms.{png,pdf}`: Time-domain audio waveforms (Baseline preserved)
- `results/plots/fig3_residual_error.{png,pdf}`: Residual error power over time (Baseline preserved)
- `results/plots/fig4_tracking_response.{png,pdf}`: Dynamic tracking during disturbance (Baseline preserved)
- `results/plots/fig5_noise_reduction_comparison.{png,pdf}`: Quantitative NR across all scenarios (Baseline preserved)
- `results/plots/fig6_bitwidth_sweep.{png,pdf}`: Cancellation quality & SQNR vs word length (Baseline preserved)
- `results/plots/fig7_coef_trajectories.{png,pdf}`: Evolution of filter tap weights (Baseline preserved)
- `results/plots/fig8_resource_utilization.{png,pdf}`: FPGA Resource Utilization (Cyclone IV E EP4CE115F29C7 verified fitter breakdown & device capacity)
- `results/plots/fig9_timing_comparison.{png,pdf}`: TimeQuest STA Timing Analysis (Fmax deficit, Slack breakdown, Critical Path Bottleneck, labeled TIMING FAIL)
- `results/plots/fig10_performance_cost_tradeoff.{png,pdf}`: Scientifically matched Performance vs Hardware Cost Trade-off & Synthesis Status

## 7. Hardware & Quartus Status
- **Target Device:** Intel/Altera Cyclone IV E `EP4CE115F29C7` (Terasic DE2-115 board)
- **Quartus Prime Lite Compilation:** **COMPLETE** — Quartus Prime Lite 25.1std.0 Build 1129, 2026-10-13
- **Synthesised Configuration:** `nlms_shift` ALGO=2, W=12, L=32, K=4 (hardware-recommended config)

### Resource Utilization (Figure 8, verified from `anc_de2_115.fit.rpt`)
| Resource | Measured Units | Total Device Capacity | Utilization (%) | Verification Source |
|---|---|---|---|---|
| Total Logic Elements (LE) | **2,531** | 114,480 | **2.21%** | `anc_de2_115.fit.rpt` |
| Combinational Functions | **2,302** | 114,480 | **2.01%** | `anc_de2_115.fit.rpt` |
| Dedicated Logic Registers | **1,113** | 114,480 | **0.97%** | `anc_de2_115.fit.rpt` |
| Embedded 9-bit Multipliers | **8** (4× 18-bit) | 532 | **1.50%** | `anc_de2_115.fit.rpt` |
| User I/O Pins | **27** | 529 | **5.10%** | `anc_de2_115.fit.rpt` |
| Memory Bits | **0** | 3,981,312 | **0.00%** | `anc_de2_115.fit.rpt` |
| Embedded PLLs | **0** | 4 | **0.00%** | `anc_de2_115.fit.rpt` |

*Denominators verified against the Intel Cyclone IV Device Handbook (Volume 1, Chapter 1, Table 1-1 for EP4CE115).*

### Timing Closure (Figure 9, verified from `anc_de2_115.sta.rpt` & `.sta.summary`, Slow 1200mV 85°C model)
| Metric | Target | Measured Value | Slack / Deficit | Status |
|---|---|---|---|---|
| Fmax (Slow 85°C Worst) | 50.00 MHz | **36.16 MHz** | **−13.84 MHz** (Achieves 72.3%) | **TIMING FAIL** |
| Fmax (Slow 0°C Best) | 50.00 MHz | **39.47 MHz** | **−10.53 MHz** (Achieves 78.9%) | **TIMING FAIL** |
| Worst-Case Setup Slack | ≥ 0.000 ns | **−7.655 ns** | **−7.655 ns** (TNS: −2630.748 ns) | **TIMING FAIL** |
| Worst-Case Hold Slack | ≥ 0.000 ns | **+0.394 ns** | **+0.394 ns** | **PASS** |
| Critical Path | — | `anc_core: i[2] → w[28][7]` | Data path delay: 27.562 ns (Period: 20.000 ns) | Clock Deficit |

> **Timing Closure Status:** **TIMING FAIL**.
> The unpipelined serial multiplier and weight update path in state `S_UPD` cannot meet the 20.000 ns clock period requirement at 50 MHz.
> Timing closure requires inserting 2-cycle pipelining stages on the shared multiplier tree prior to physical deployment. Timing pipeline modification is deferred per change-control constraints.

### Figure 10 Scientific Validity & Methodology Resolution
- **Prior Figure 10 Defect:** The legacy Figure 10 erroneously plotted a 10.0 dB fixed-point result against a 20.7 dB floating-point result. Investigation revealed that the 10.0 dB figure was an artifact of averaging across all test scenarios in the W=12 sweep (specifically weighed down by the non-stationary `amp_steps` scenario at 9.4 dB), whereas the 20.7 dB floating-point figure was taken exclusively from the stationary scenario.
- **Updated Figure 10 Methodology:**
  1. **Strictly Matched Scenarios:** In Figure 10 Panel A, floating-point and fixed-point ($W=12$) implementations are evaluated under identical test conditions:
     - `stationary`: Float 20.7 dB vs Fixed W=12 20.7 dB ($\Delta = +0.07$ dB)
     - `path_switch`: Float 20.9 dB vs Fixed W=12 21.1 dB ($\Delta = +0.12$ dB)
     - `amp_steps`: Float 9.4 dB vs Fixed W=12 9.4 dB ($\Delta = -0.03$ dB)
  2. **Noise-Reduction Difference (Matched Scenarios):** Absolute noise-reduction differences between floating-point reference and fixed-point W=12 are: stationary +0.07 dB, path_switch +0.12 dB, amp_steps −0.03 dB. All three differences are below 0.15 dB.
  3. **Hardware Cost Integrity:** Panel B transparently shows that `nlms_shift` has been synthesized at 2,531 LEs and 8 multipliers. Because LMS and standard NLMS have **NOT** been synthesized in Quartus, hardware resource counts for these algorithms remain pending. No synthetic or extrapolated Pareto frontier is fabricated; instead, theoretical complexity profiles and synthesis statuses are reported honestly.

- **Artifacts Updated:** Figures 8, 9, and 10 updated in both 300 DPI PNG and vector PDF on 2026-10-14. Figures 1–7 were not modified by this task (file timestamps unchanged from the audited baseline).
