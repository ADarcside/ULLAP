# Research Results: Adaptive Noise Cancellation (ANC)
**Target Hardware:** Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7) | **Pipeline:** Python Software Simulation & Verification
N=16000 samples @ 8000 Hz, Filter Length L=32, Scenarios: stationary, amp_steps, path_switch, wav, feedback; WAV: `acoustic_chord.wav`
Eval seeds [1, 2, 3]; tuning seed 100.

## 1. Tuned Step Sizes (Optimal shared parameter per algorithm)

| Algorithm | mu | Grid Points Evaluated |
|---|---|---|
| lms | 0.5009 | 14 |
| nlms | 0.1468 | 13 |
| nlms_shift | 0.25 | 9 |

## 2. Floating-Point Performance Across Scenarios

| Scenario | Algorithm | NR Final (dB) | NR Whole-Run (dB) | Settling Time (ms) | Tracking Time (ms) | Misalignment (dB) | Diverged |
|---|---|---|---|---|---|---|---|
| stationary | lms | 20.3 ± 0.6 | 15.2 | 1784 | n/a | -26.2 | 0 |
| stationary | nlms | 21.3 ± 0.6 | 14.8 | 1786 | n/a | -26.7 | 0 |
| stationary | nlms_shift | 20.4 ± 0.7 | 15.1 | 1784 | n/a | -26.2 | 0 |
| amp_steps | lms | 18.9 ± 0.7 | 18.5 | 484 | 74 | -25.8 | 0 |
| amp_steps | nlms | 18.7 ± 0.2 | 18.9 | 465 | 198 | -25.5 | 0 |
| amp_steps | nlms_shift | 19.2 ± 0.2 | 19.4 | 484 | 197 | -26.2 | 0 |
| path_switch | lms | 20.6 ± 0.3 | 12.0 | 722 | 706 | -17.3 | 0 |
| path_switch | nlms | 20.6 ± 0.3 | 11.3 | 708 | 678 | -15.4 | 0 |
| path_switch | nlms_shift | 20.6 ± 0.3 | 11.9 | 722 | 705 | -17.2 | 0 |
| wav | lms | 5.4 ± 0.1 | 11.2 | 134 | n/a | -4.1 | 0 |
| wav | nlms | 5.2 ± 0.1 | 10.0 | 128 | n/a | -3.8 | 0 |
| wav | nlms_shift | 5.4 ± 0.1 | 10.3 | 128 | n/a | -3.9 | 0 |
| feedback | lms | 4.2 ± 0.1 | 4.1 | 0 | n/a | 3.3 | 0 |
| feedback | nlms | 4.3 ± 0.1 | 4.1 | 0 | n/a | 3.2 | 0 |
| feedback | nlms_shift | 4.2 ± 0.1 | 4.1 | 0 | n/a | 3.3 | 0 |

> [!NOTE]
> **WAV Scenario Confidence Intervals:** For the real WAV audio scenario (`acoustic_chord.wav`), the input recording is fixed across all runs. The random evaluation seeds vary only the background noise and secondary path perturbations, which naturally produces narrower variance and tighter confidence intervals than fully stochastic synthetic noise sequences.

## 3. Fixed-Point Precision Sweep (W = 8 to 24 bits)

| Word Length W | lms | nlms | nlms_shift |
|---|---|---|---|
| 8 | 6.7 dB / +7.36 deg / 0 ovf | 5.9 dB / +8.18 deg / 0 ovf | 6.9 dB / +7.15 deg / 0 ovf |
| 9 | 11.0 dB / +3.07 deg / 0 ovf | 10.8 dB / +3.34 deg / 0 ovf | 11.8 dB / +2.24 deg / 0 ovf |
| 10 | 12.9 dB / +1.21 deg / 0 ovf | 14.3 dB / -0.23 deg / 0 ovf | 14.0 dB / +0.08 deg / 0 ovf |
| 11 | 13.7 dB / +0.37 deg / 0 ovf | 14.3 dB / -0.22 deg / 0 ovf | 14.5 dB / -0.46 deg / 0 ovf |
| 12 | 13.6 dB / +0.45 deg / 0 ovf | 14.0 dB / +0.15 deg / 0 ovf | 13.5 dB / +0.53 deg / 0 ovf |
| 13 | 14.5 dB / -0.39 deg / 0 ovf | 14.6 dB / -0.47 deg / 0 ovf | 14.4 dB / -0.40 deg / 0 ovf |
| 14 | 14.5 dB / -0.38 deg / 0 ovf | 14.5 dB / -0.34 deg / 0 ovf | 14.5 dB / -0.41 deg / 0 ovf |
| 15 | 14.1 dB / -0.04 deg / 0 ovf | 14.2 dB / -0.04 deg / 0 ovf | 14.1 dB / -0.05 deg / 0 ovf |
| 16 | 14.1 dB / +0.01 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |
| 17 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / +0.00 deg / 0 ovf | 14.0 dB / +0.01 deg / 0 ovf |
| 18 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / +0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |
| 19 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / -0.01 deg / 0 ovf | 14.0 dB / -0.00 deg / 0 ovf |
| 20 | 14.1 dB / -0.00 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |
| 21 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |
| 22 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / -0.00 deg / 0 ovf |
| 23 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |
| 24 | 14.1 dB / +0.00 deg / 0 ovf | 14.1 dB / -0.00 deg / 0 ovf | 14.0 dB / +0.00 deg / 0 ovf |

## 4. Hardware Candidates for DE2-115 Cyclone IV E

| Algorithm | W (bits) | mu | Fixed NR (dB) | Float NR (dB) | Degradation (dB) | Overflows | Arithmetic Architecture |
|---|---|---|---|---|---|---|---|
| nlms | 10 | 0.1468 | 14.3 | 14.1 | -0.23 | 0 | 2L+3 mult + 1 divider (or reciprocal) |
| nlms_shift | 10 | 0.25 | 14.0 | 14.0 | +0.08 | 0 | 2L mult, leading-one detect + barrel shift, no divider/mu-mult |
| lms | 11 | 0.5009 | 13.7 | 14.1 | +0.37 | 0 | 2L+1 mult, no divider |

## 5. Accumulator Ablation

| Algorithm | W | Accumulator Bits | Mean NR (dB) | Accumulator Saturations | Total Overflows |
|---|---|---|---|---|---|
| nlms | 10 | 25 | 14.3 | 0 | 0 |
| nlms | 10 | 20 | 14.3 | 0 | 0 |
| nlms | 10 | 18 | 14.4 | 9 | 9 |
| nlms | 10 | 16 | 7.6 | 10058 | 13064 |
| nlms_shift | 10 | 25 | 14.0 | 0 | 0 |
| nlms_shift | 10 | 20 | 14.0 | 0 | 0 |
| nlms_shift | 10 | 18 | 14.0 | 9 | 9 |
| nlms_shift | 10 | 16 | 7.2 | 10580 | 14277 |
| lms | 11 | 27 | 13.7 | 0 | 0 |
| lms | 11 | 22 | 13.7 | 0 | 0 |
| lms | 11 | 20 | 13.8 | 12 | 12 |
| lms | 11 | 18 | 7.4 | 10935 | 16839 |

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
- **LMS (W=11):** 1,775 LEs (1.55%), 1,069 registers, Fmax = 60.05 MHz, Setup Slack = +3.347 ns (PASS)
- **NLMS (W=11):** 2,542 LEs (2.22%), 1,331 registers, Fmax = 58.87 MHz, Setup Slack = +3.014 ns (PASS)
- **NLMS-Shift (W=12):** 2,690 LEs (2.35%), 1,213 registers, Fmax = 61.98 MHz, Setup Slack = +3.867 ns (PASS)
- **Gate B Timing Closure:** PASSED (all worst-case slow 85°C setup slacks >= +3.0 ns, exceeding +0.5 ns target).

## 8. Latency and Execution Budget Analysis

### Measured RTL Processing Latency ($L=32, 50\text{ MHz}$)
*Source: Hardware testbench simulation in Questa (`tb/tb_anc_core.v`, `results/metrics/questa_regression_summary.txt`):*

| Algorithm | Bit-Width ($W$) | Output Latency (`lat_seen`) | Output Latency ($\mu\text{s}$) | Busy Cycles (`bmax`) | Total Processing ($\mu\text{s}$) | Busy Share ($48\text{ kHz}, T_s = 20.83\,\mu\text{s}$) |
|---|---|---|---|---|---|---|
| **LMS** | 12 (or 11) | 35 cycles | $0.70\,\mu\text{s}$ | 73 cycles | $1.46\,\mu\text{s}$ | **7.01%** |
| **NLMS** | 12 | 37 cycles | $0.74\,\mu\text{s}$ | 127 cycles | $2.54\,\mu\text{s}$ | **12.20%** |
| **NLMS** | 11 | 37 cycles | $0.74\,\mu\text{s}$ | 124 cycles | $2.48\,\mu\text{s}$ | **11.90%** |
| **NLMS-Shift** | 12 | 37 cycles | $0.74\,\mu\text{s}$ | 72 cycles | $1.44\,\mu\text{s}$ | **6.91%** |

### Questa Log Verification Lines
- `shipped_lms_W11_stationary`: `# TB_RESULT PASS vec=vectors/lms_W11_stationary ALGO=0 W=11 L=32 ... lat=35 busy_cycles=73`
- `shipped_nlms_W11_stationary`: `# TB_RESULT PASS vec=vectors/nlms_W11_stationary ALGO=1 W=11 L=32 ... lat=37 busy_cycles=124`
- `shift_e2_k3_W12_stationary`: `# TB_RESULT PASS vec=vectors/rtl/shift_e2_k3_W12_stationary ALGO=2 W=12 L=32 ... lat=37 busy_cycles=72`

### Busy-Cycle Reconciliation
- **LMS (70 vs 73 cycles):** Analytical pre-pipeline model assumed $2L + 6 = 70$ cycles. The actual 3-stage multiplier pipeline in `rtl/anc_core.v` introduces a 3-cycle drain in state `S_UPD` (`wc = 2`), giving exactly $70 + 3 = 73$ cycles.
- **NLMS (91 vs 124/127 cycles):** An earlier preliminary analytical estimate assumed a generic 18-cycle divider ($2L + 9 + 18 = 91$). The actual synthesizable restoring divider in `rtl/anc_core.v` uses dividend width $NW = W + MUW + 2F + 4 + CL$ (48 cycles for $W=11$, 50 cycles for $W=12$), running for $NW+1$ cycles and resulting in 124 cycles ($W=11$) and 127 cycles ($W=12$).

### End-to-End System Latency Budget (at $f_s = 48\text{ kHz}$)
- **Codec Sample Period:** $T_s = 1 / 48000 \approx 20.833\,\mu\text{s}$ (1041.67 system clock cycles at 50 MHz).
- **ADC Decimation Filter Delay:** 12 audio samples = $250.0\,\mu\text{s}$ (*estimate, unverified*).
- **DAC Interpolation Filter Delay:** 11 audio samples = $229.2\,\mu\text{s}$ (*estimate, unverified*).
- **I2S Word Serialization (Framing):** 2 audio samples = $41.7\,\mu\text{s}$.
- **FPGA Core Processing Latency (NLMS-Shift):** 37 cycles at 50 MHz = $0.74\,\mu\text{s}$.
- **Total Acoustic Loop Delay:** $\approx 521.6\,\mu\text{s}$ ($\sim 0.52\text{ ms}$). The FPGA processing delay constitutes only 0.14% of the acoustic latency.

## 9. Algorithm Trade-offs & Empirical Comparison

Based on the 20-seed Monte Carlo evaluation in `results/paper_numbers.csv` with each architecture evaluated at its fair-tuned operating point ($W=12, L=32$):

- **Stationary Noise:** NLMS-Shift achieves a mean final NR of $22.37\text{ dB}$ ($95\%\text{ CI: } [22.11, 22.63]\text{ dB}$), which is statistically indistinguishable from fair-tuned LMS at $22.39\text{ dB}$ ($[22.12, 22.66]\text{ dB}$) and fair-tuned NLMS at $22.28\text{ dB}$ ($[22.01, 22.54]\text{ dB}$).
- **Amplitude Steps:** NLMS-Shift achieves $24.33\text{ dB}$ ($[23.88, 24.78]\text{ dB}$), comparable to fair-tuned NLMS at $24.16\text{ dB}$ ($[23.58, 24.73]\text{ dB}$) and outperforming LMS at $22.36\text{ dB}$ ($[21.72, 23.00]\text{ dB}$) by $\sim 2.0\text{ dB}$. NLMS-Shift maintains a modest $+0.17\text{ dB}$ advantage over NLMS because power-of-two shift quantization provides an intrinsic floor during step transients, though the two algorithms overlap within their 95% confidence intervals.
- **Acoustic Path Switch:** NLMS-Shift reaches $18.91\text{ dB}$ ($[18.76, 19.06]\text{ dB}$), closely matching LMS at $18.95\text{ dB}$ ($[18.81, 19.09]\text{ dB}$) and exceeding fair-tuned NLMS at $18.53\text{ dB}$ ($[18.39, 18.67]\text{ dB}$). However, NLMS-Shift does not dominate this scenario: prior to fair re-tuning, when LMS and NLMS were operated with larger step sizes ($\mu=0.5$ and $\mu=0.1468$), NLMS-Shift lagged both by approximately $1.6\text{ dB}$ ($18.99\text{ dB}$ vs $20.57\text{ dB}$ and $20.48\text{ dB}$), reflecting the bounded tracking agility imposed by fixed power-of-two quantization.
- **Real WAV Audio:** NLMS-Shift delivers $5.46\text{ dB}$ ($[5.42, 5.50]\text{ dB}$), losing to both fair-tuned NLMS at $5.73\text{ dB}$ ($[5.69, 5.76]\text{ dB}$) and LMS at $5.69\text{ dB}$ ($[5.66, 5.73]\text{ dB}$) by $0.23$–$0.27\text{ dB}$. In all three algorithms, cancellation is fundamentally limited below $6\text{ dB}$ by the tonal nature and harmonic sparsity of the `acoustic_chord.wav` recording rather than filter arithmetic.
- **Acoustic Feedback:** All three algorithms yield an identical $4.35\text{ dB}$ ($[4.31, 4.39]\text{ dB}$ for NLMS/LMS, $[4.32, 4.39]\text{ dB}$ for NLMS-Shift), bounded by the closed-loop singing margin ($D=8, g=0.88$). This scenario does not separate the algorithms.

**Architectural Trade-off Summary:** NLMS-Shift is not uniformly superior across all metrics. While it eliminates the high cycle count and resource overhead of a multi-cycle restoring divider (achieving 72 busy cycles vs 127 cycles for NLMS, and $F_{\max} = 61.98\text{ MHz}$ vs $58.87\text{ MHz}$), it exhibits minor cancellation deficits on complex audio waveforms (losing $\sim 0.25\text{ dB}$ on WAV) and required specific regularisation tuning to avoid path-switch tracking penalties relative to full-precision dividers.
