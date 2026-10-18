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

> [!NOTE]
> Note that the earlier single-seed tuning (seed 100) shown in this section was superseded by the multi-seed fair hyperparameter tuning across unseen seeds 101–103 (LMS: $\mu=0.25$, NLMS: $\mu=0.25, \text{EPS\_EXP}=0$, NLMS-Shift: $K=3, \text{EPS\_EXP}=2$), evaluated across seeds 1–20 in Section 9.

## Noise Reduction Metric Definitions

All noise reduction (NR) metrics evaluate cancellation relative to known clean signal $s[n]$, primary noise $nz[n] = d[n] - s[n]$, and filter residual error $r[n] = e[n] - s[n]$:

1. **`nr_final` (Final-Window Steady-State NR, dB):**
   - **Exact Window:** Final 25% of the run ($\text{samples } [0.75N, N)$).
   - **Definition:** Linear power ratio of noise to residual in the steady-state window, converted to dB:
     $$\text{NR}_{\text{final}} = 10 \log_{10} \left( \frac{\frac{1}{0.25 N} \sum_{n=0.75N}^{N-1} nz^2[n]}{\frac{1}{0.25 N} \sum_{n=0.75N}^{N-1} r^2[n] + 10^{-20}} \right)$$
   - **Usage:** Primary benchmark metric reported across all scenario evaluations in `results/paper_numbers.csv` to measure settled adaptive filter performance.

2. **`nr_all` (Full-Run Linear Energy NR, dB):**
   - **Exact Window:** 100% of the run ($\text{samples } [0, N)$).
   - **Definition:** Ratio of total accumulated noise energy to total residual error energy across the entire run in the linear domain, converted to dB:
     $$\text{NR}_{\text{all}} = 10 \log_{10} \left( \frac{\frac{1}{N} \sum_{n=0}^{N-1} nz^2[n]}{\frac{1}{N} \sum_{n=0}^{N-1} r^2[n] + 10^{-20}} \right)$$
   - **Usage:** Measures overall energy attenuation across the full signal, including initial transient convergence and disturbance tracking bursts. Because linear squared error is summed, large transient or clipping spikes dominate the denominator.

3. **`nr_avg` (Full-Run Smoothed Curve Time-Average, dB):**
   - **Exact Window:** 100% of the run ($\text{samples } [0, N)$), with a 256-sample moving-average smoothing window.
   - **Definition:** Arithmetic time-average of the 256-sample smoothed NR curve evaluated sample-by-sample in the logarithmic (dB) domain:
     $$\text{NR}_{\text{avg}} = \frac{1}{N} \sum_{n=0}^{N-1} 10 \log_{10} \left( \frac{\text{smooth}(nz^2[n], 256) + 10^{-20}}{\text{smooth}(r^2[n], 256) + 10^{-20}} \right)$$
   - **Usage:** Historically used in hyperparameter tuning grids. Unlike `nr_all`, computing the mean in the log (dB) domain prevents single massive error spikes from dominating the entire metric.

> [!IMPORTANT]
> **Distinction Between `nr_avg` and `nr_all`:** Text must not conflate `nr_avg` with `nr_all` as they are fundamentally distinct mathematical operations (mean of smoothed dB curve vs. ratio of total linear energies). For example, at 4.0x input level in Section 10, LMS produces heavy clipping that drives total linear energy ratio $\text{NR}_{\text{all}}$ down to $-0.47\text{ dB}$, while the logarithmic time-average $\text{NR}_{\text{avg}}$ evaluates to $6.00\text{ dB}$; they are not equivalent.

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

All publication figures (Figures 1–11) have been regenerated directly from committed code using the fair-tuned hardware parameters ($W=12, L=32$):
- **LMS:** $\mu = 0.25$
- **NLMS:** $\mu = 0.25, \text{EPS\_EXP} = 0$
- **NLMS-Shift:** $K = 3 (\mu = 0.125), \text{EPS\_EXP} = 2$

- `results/plots/fig1_convergence.{png,pdf}`: Convergence curves across all 5 scenarios (LMS $\mu=0.25$, NLMS $\mu=0.25, \text{eps}=0$, NLMS-Shift $K=3, \text{eps}=2$, $W=12, L=32$, Seed 1)
- `results/plots/fig2_waveforms.{png,pdf}`: Time-domain audio waveforms (Primary $d[n]$, Reference $x[n]$, Clean $s[n]$, and Filter Residuals $e[n]$ for stationary scenario)
- `results/plots/fig3_residual_error.{png,pdf}`: Residual error power $10\log_{10}(e^2[n])$ over time vs input noise power baseline (stationary scenario)
- `results/plots/fig4_tracking_response.{png,pdf}`: Dynamic tracking during amplitude step disturbance ($0.7\text{ s}$ burst and $1.2\text{ s}$ decay) with coefficient misalignment norm
- `results/plots/fig5_noise_reduction_comparison.{png,pdf}`: Final and whole-run noise reduction comparison bar chart across all 5 scenarios
- `results/plots/fig6_bitwidth_sweep.{png,pdf}`: Word-length precision sweep ($W = 8$ to $24$ bits) showing final NR, degradation vs $W=24$ reference, and SQNR
- `results/plots/fig7_coef_trajectories.{png,pdf}`: Adaptive filter weight trajectories over time for representative taps ($w_0, w_1, w_4, w_8, w_{15}$)
- `results/plots/fig8_resource_utilization.{png,pdf}`: Cyclone IV E EP4CE115 Logic Elements (1,885 / 2,697 / 2,690) and Dedicated Registers (1,148 / 1,425 / 1,213) from Quartus synthesis
- `results/plots/fig9_timing_comparison.{png,pdf}`: Fmax ($59.90 / 61.72 / 61.98\text{ MHz}$) and Setup Slack ($+3.305 / +3.798 / +3.867\text{ ns}$) across Slow 85°C corner
- `results/plots/fig10_performance_cost_tradeoff.{png,pdf}`: Performance-cost trade-off (Noise reduction vs Logic Elements) across scenarios
- `results/plots/fig11_latency_comparison.{png,pdf}`: Busy cycles per sample ($73 / 127 / 72$ cycles) and processing budget headroom at $48\text{ kHz}$
- `results/plots/fig12_pareto_stationary_amp_steps.{png,pdf}`: Pareto frontier (Stationary vs Amplitude-Step Noise Reduction across seeds 1–20) for LMS (all $\mu$ in grid), NLMS (all $\mu \times \text{EPS\_EXP}$), and NLMS-Shift (all $K \times \text{EPS\_EXP}$), demonstrating that zero LMS settings achieve both $\ge 22.0\text{ dB}$ stationary and $\ge 24.0\text{ dB}$ amp_steps simultaneously.

## 7. Hardware & Quartus Status
- **Target Device:** Intel/Altera Cyclone IV E `EP4CE115F29C7` (Terasic DE2-115 board, Speed Grade 7)
- **Quartus Prime Lite 25.1std Compilation:** Complete & Verified across all 3 architectures at $W=12$.
- **LMS (W=12):** 1,885 LEs (1.65%), 1,148 registers, 4 multipliers, Fmax = 59.90 MHz, Setup Slack = +3.305 ns (PASS)
- **NLMS (W=12):** 2,697 LEs (2.36%), 1,425 registers, 4 multipliers, Fmax = 61.72 MHz, Setup Slack = +3.798 ns (PASS)
- **NLMS-Shift (W=12):** 2,690 LEs (2.35%), 1,213 registers, 4 multipliers, Fmax = 61.98 MHz, Setup Slack = +3.867 ns (PASS)
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

- **Stationary Noise:** NLMS-Shift achieves a mean final NR of $22.37\text{ dB}$ ($95\%\text{ CI: } [22.11, 22.63]\text{ dB}$), which ties fair-tuned LMS at $22.39\text{ dB}$ ($[22.12, 22.66]\text{ dB}$) and fair-tuned NLMS at $22.28\text{ dB}$ ($[22.01, 22.54]\text{ dB}$) within overlapping confidence intervals.
- **Amplitude Steps:** NLMS-Shift achieves $24.33\text{ dB}$ ($[23.88, 24.78]\text{ dB}$), tying fair-tuned NLMS at $24.16\text{ dB}$ ($[23.58, 24.73]\text{ dB}$) as their 95% confidence intervals overlap, while both outperform LMS at $22.36\text{ dB}$ ($[21.72, 23.00]\text{ dB}$) by $\sim 2.0\text{ dB}$. Crucially, an exhaustive Pareto frontier evaluation across all settings in the hyperparameter grids (evaluated across seeds 1–20, Figure 12) confirms that normalised algorithms (NLMS and NLMS-Shift) reach $\ge 22.0\text{ dB}$ stationary and $\ge 24.0\text{ dB}$ amp_steps at a single setting, whereas LMS cannot: aggressive tracking ($\mu=0.10$) degrades stationary cancellation to $16.17\text{ dB}$ due to high steady-state excess MSE, while conservative tracking ($\mu=0.25$) limits amp_steps cancellation to $22.36\text{ dB}$. Note that the $22/24\text{ dB}$ thresholds were chosen post hoc and refer to the frontier figure (Figure 12). While both normalised algorithms satisfy this joint frontier at a single operating point, NLMS-Shift's distinct advantage over NLMS is the divider-free 72 vs 127 busy cycles per sample (a 43.3% reduction in execution cycles, eliminating the multi-cycle restoring hardware divider).
- **Acoustic Path Switch:** NLMS-Shift reaches $18.91\text{ dB}$ ($[18.76, 19.06]\text{ dB}$), tying fair-tuned LMS at $18.95\text{ dB}$ ($[18.81, 19.09]\text{ dB}$) and fair-tuned NLMS at $18.53\text{ dB}$ ($[18.39, 18.67]\text{ dB}$) within overlapping confidence intervals.
- **Real WAV Audio:** NLMS-Shift delivers $5.46\text{ dB}$ ($[5.42, 5.50]\text{ dB}$), losing to both fair-tuned NLMS at $5.73\text{ dB}$ ($[5.69, 5.76]\text{ dB}$) and LMS at $5.69\text{ dB}$ ($[5.66, 5.73]\text{ dB}$) by $0.23$–$0.27\text{ dB}$. Across all evaluated hyperparameter configurations in the tuning grids, no setting in any algorithm reached the $10\text{ dB}$ target on `acoustic_chord.wav`. Rather than an absolute algorithmic limitation, the lower cancellation on the tonal WAV benchmark represents an operating-point trade-off: tuning parameters can be selected to maximize WAV performance (reaching 8.58–8.72 dB), but doing so imposes a significant penalty on synthetic tracking performance, degrading stationary noise cancellation by ~4.1 to 4.3 dB and path-switch cancellation by ~4.0 to 4.2 dB. At the balanced fair-tuned settings optimized for robust all-around performance, all three algorithms yield 5.46–5.73 dB on WAV audio.

### Operating-Point Trade-off: Best WAV Settings (Selected on Tuning Seeds 101–103)

| Algorithm | WAV-Best Setting | WAV Final NR | Stationary Final NR | Amp Steps Final NR | Path Switch Final NR | Trade-off / Cost vs Balanced (Seeds 101–103) |
|---|---|:---:|:---:|:---:|:---:|---|
| **LMS** | $\mu = 0.125$ | **8.72 dB** | 17.86 dB | 23.42 dB | 14.58 dB | Stationary $-4.53\text{ dB}$, Path Switch $-4.37\text{ dB}$ |
| **NLMS** | $\text{EPS\_EXP}=-2, \mu=0.50$ | **8.58 dB** | 17.50 dB | 24.02 dB | 14.33 dB | Stationary $-4.78\text{ dB}$, Path Switch $-4.20\text{ dB}$ |
| **NLMS-Shift** | $\text{EPS\_EXP}=0, K=2$ | **8.70 dB** | 17.86 dB | 23.87 dB | 14.58 dB | Stationary $-4.51\text{ dB}$, Path Switch $-4.33\text{ dB}$ |

### Evaluation of WAV-Best Settings Across Evaluation Seeds 1–20 (Mean, 95% CI, and Penalty vs. Balanced Setting on Same Seeds)

*Source: `scratch/eval_wav_best_seeds1_20.py` evaluated across seeds 1–20 ($W=12, L=32, N=16{,}000$); baseline values from `results/paper_numbers.csv`:*

| Algorithm | Setting | Scenario | Mean Final NR (dB) | 95% Confidence Interval | Balanced Baseline NR (dB) | Penalty / Delta vs Balanced |
|---|---|---|:---:|:---:|:---:|:---:|
| **LMS** | $\mu = 0.125$ | **WAV Audio** | **8.69 dB** | $[8.64, 8.73]\text{ dB}$ | $5.69\text{ dB}$ | $+3.00\text{ dB}$ (WAV Gain) |
| | | Stationary | 18.29 dB | $[18.19, 18.40]\text{ dB}$ | $22.39\text{ dB}$ | **$-4.10\text{ dB}$** (Penalty) |
| | | Path Switch | 14.78 dB | $[14.68, 14.87]\text{ dB}$ | $18.95\text{ dB}$ | **$-4.17\text{ dB}$** (Penalty) |
| | | Amp Steps | 23.86 dB | $[23.22, 24.49]\text{ dB}$ | $22.36\text{ dB}$ | $+1.50\text{ dB}$ |
| **NLMS** | $\text{EPS\_EXP}=-2, \mu=0.50$ | **WAV Audio** | **8.55 dB** | $[8.51, 8.60]\text{ dB}$ | $5.73\text{ dB}$ | $+2.82\text{ dB}$ (WAV Gain) |
| | | Stationary | 18.03 dB | $[17.93, 18.14]\text{ dB}$ | $22.28\text{ dB}$ | **$-4.25\text{ dB}$** (Penalty) |
| | | Path Switch | 14.54 dB | $[14.44, 14.64]\text{ dB}$ | $18.53\text{ dB}$ | **$-3.99\text{ dB}$** (Penalty) |
| | | Amp Steps | 24.25 dB | $[23.67, 24.82]\text{ dB}$ | $24.16\text{ dB}$ | $+0.09\text{ dB}$ |
| **NLMS-Shift** | $\text{EPS\_EXP}=0, K=2$ | **WAV Audio** | **8.67 dB** | $[8.62, 8.71]\text{ dB}$ | $5.46\text{ dB}$ | $+3.21\text{ dB}$ (WAV Gain) |
| | | Stationary | 18.29 dB | $[18.19, 18.40]\text{ dB}$ | $22.37\text{ dB}$ | **$-4.08\text{ dB}$** (Penalty) |
| | | Path Switch | 14.78 dB | $[14.68, 14.87]\text{ dB}$ | $18.91\text{ dB}$ | **$-4.13\text{ dB}$** (Penalty) |
| | | Amp Steps | 24.49 dB | $[23.93, 25.05]\text{ dB}$ | $24.33\text{ dB}$ | $+0.16\text{ dB}$ |

- **Acoustic Feedback:** All three algorithms tie at $4.35\text{ dB}$ ($[4.31, 4.39]\text{ dB}$ for NLMS/LMS, $[4.32, 4.39]\text{ dB}$ for NLMS-Shift), bounded by the closed-loop singing margin ($D=8, g=0.88$). This scenario does not separate the algorithms.

**Architectural Trade-offs:** NLMS-Shift is not uniformly superior across all metrics. It ties fair-tuned NLMS and LMS in most scenarios (stationary, amp_steps vs NLMS, path_switch, and feedback), and loses slightly to both on real tonal audio ($5.46\text{ dB}$ vs $5.73\text{ dB}$ and $5.69\text{ dB}$). Normalised algorithms (NLMS and NLMS-Shift) reach $\ge 22.0\text{ dB}$ stationary and $\ge 24.0\text{ dB}$ amp_steps at a single setting, LMS cannot (the 22/24 thresholds were chosen post hoc; refer to the frontier figure, Figure 12). NLMS-Shift's distinct advantage over NLMS is the divider-free 72 vs 127 busy cycles per sample (a 43.3% reduction in busy cycles per sample compared to NLMS's 127-cycle restoring divider, leaving 93% throughput headroom at 48 kHz), while input-to-output core latency is 37 clock cycles ($0.74\,\mu\text{s}$) for both NLMS and NLMS-Shift, and 35 cycles ($0.70\,\mu\text{s}$) for LMS. It preserves the $\sim 2.0\text{ dB}$ amplitude-step tracking gain over LMS ($24.33\text{ dB}$ vs $22.36\text{ dB}$). Conversely, LMS is substantially cheaper in hardware resources (1,885 LEs vs 2,690 LEs for NLMS-Shift and 2,697 LEs for NLMS), making LMS the more economical choice where logic resources are strictly constrained and abrupt noise level surges are absent.

## 10. Dynamic Range & Level-Sweep Evaluation (0.25x to 4x)

*Source: Direct unedited execution of `py/exp_level_robustness.py` (W=12, L=32, seeds 1–3, evaluated across stationary, amp_steps, path_switch, wav, total 192,000 samples per test point). Pass criterion as coded: `ovf_rate = total_ovf / total_samples < 1e-3`. Reported NR is `nr_avg` (time-average of the 256-sample smoothed NR curve in dB over the full run; note that `nr_avg` is distinct from whole-run linear energy ratio `nr_all`, which evaluates to -0.47 dB for LMS at 4x vs 6.00 dB for `nr_avg`):*

| Scale | Algorithm | NR avg (time-avg smoothed dB, full run) | Total Ovf | Total Samples | Ovf Rate | Pass (< 1e-3)? |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **0.25x** | LMS ($\mu=0.25$) | 3.60 | 7,589 | 192,000 | 3.95e-02 | FAIL |
| **0.25x** | NLMS ($\mu=0.25, \text{eps}=0$) | 3.57 | 7,267 | 192,000 | 3.78e-02 | FAIL |
| **0.25x** | NLMS-Shift ($K=3, \text{eps}=2$) | 3.60 | 7,589 | 192,000 | 3.95e-02 | FAIL |
| **0.50x** | LMS ($\mu=0.25$) | 8.87 | 6,940 | 192,000 | 3.61e-02 | FAIL |
| **0.50x** | NLMS ($\mu=0.25, \text{eps}=0$) | 8.67 | 6,295 | 192,000 | 3.28e-02 | FAIL |
| **0.50x** | NLMS-Shift ($K=3, \text{eps}=2$) | 8.83 | 6,393 | 192,000 | 3.33e-02 | FAIL |
| **1.00x** | LMS ($\mu=0.25$) | 15.03 | 0 | 192,000 | 0.00e+00 | **PASS** |
| **1.00x** | NLMS ($\mu=0.25, \text{eps}=0$) | 14.93 | 0 | 192,000 | 0.00e+00 | **PASS** |
| **1.00x** | NLMS-Shift ($K=3, \text{eps}=2$) | 15.07 | 0 | 192,000 | 0.00e+00 | **PASS** |
| **2.00x** | LMS ($\mu=0.25$) | 13.97 | 68 | 192,000 | 3.54e-04 | **PASS** |
| **2.00x** | NLMS ($\mu=0.25, \text{eps}=0$) | 14.94 | 63 | 192,000 | 3.28e-04 | **PASS** |
| **2.00x** | NLMS-Shift ($K=3, \text{eps}=2$) | 14.89 | 63 | 192,000 | 3.28e-04 | **PASS** |
| **4.00x** | LMS ($\mu=0.25$) | 6.00 | 13,519 | 192,000 | 7.04e-02 | FAIL |
| **4.00x** | NLMS ($\mu=0.25, \text{eps}=0$) | 12.11 | 2,323 | 192,000 | 1.21e-02 | FAIL |
| **4.00x** | NLMS-Shift ($K=3, \text{eps}=2$) | 12.59 | 2,323 | 192,000 | 1.21e-02 | FAIL |

**Reconciliation Note:**
The previous table had manually rounded/approximated 4x overflows to 8,192 and omitted the small 2x overflows (68 / 63 / 63), whereas `py/exp_level_robustness.py` measures exact cumulative bit-level saturations (`sat_in` + `sat_w` + `sat_y` + `sat_e`) and reports full-run smoothed time-average noise reduction (`nr_avg`, distinct from whole-run linear energy ratio `nr_all`), with the pass criterion strictly evaluated as `ovf_rate = total_ovf / total_samples < 1e-3`.

**Key Findings:**
- All three algorithms pass the acceptance criteria only at nominal calibrated levels (1x–2x).
- At 0.25x and 0.5x, all three algorithms fail due to coefficient weight saturation (`sat_w`), as the adaptive weights scale inversely with signal amplitude ($\mathbf{w} \approx \mathbf{h}/s$); LMS and NLMS-Shift performance and overflow counts are identical at 0.25x.
- At 4.0x, the normalized algorithms maintain 12.1–12.6 dB cancellation (compared to LMS at 6.00 dB), but all three fail the strict zero-overflow criterion because the reference signal exceeds $\pm 1.0$, producing input clipping overflows (`sat_in`) at the simulated ADC converters.
- Level robustness is therefore **not** an NLMS-Shift advantage; all three fixed-point implementations require proper input gain staging within the calibrated 1x–2x operating window.
