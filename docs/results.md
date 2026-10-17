# Research Results: Adaptive Noise Cancellation (ANC)
**Target Hardware:** Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7, Speed Grade 7)  
**Pipeline:** Python Model (py/fixedpoint.py), SystemVerilog RTL (rtl/anc_core.v), Questa 25.2 Simulation, Quartus Prime Lite 25.1std Synthesis  
**Parameters:** N=16000 samples @ 8000 Hz, Filter Length L=32, Word Length W=12 (Q1.11 signed), Regulariser EPS_EXP=2 ($\epsilon=0.25$), Shift Step K=3 ($\mu=0.125$).

---

## 1. Operating Point Selection & Precision (W=12, EPS_EXP=2, K=3)

Following the Task 1 audit and Task 2 sweep across $\text{EPS\_EXP} \in \{0..4\}$ and $K \in \{2..4\}$, the operating point $\text{EPS\_EXP}=2, K=3$ at $W=12$ was selected as the optimal implementation point meeting all performance and stability criteria:
- **Stationary Noise:** Final NR = **22.22 dB** (Mean Whole-Run = 13.17 dB, Margin = +11.22 dB over 10 dB target)
- **Amplitude Steps:** Final NR = **24.15 dB** (Mean Whole-Run = 16.94 dB, Margin = +13.15 dB over 10 dB target)
- **Acoustic Path Switch:** Final NR = **18.99 dB** (Mean Whole-Run = 9.54 dB, Margin = +7.99 dB over 10 dB target)
- **Real Audio WAV (`acoustic_chord.wav`):** Final NR = **5.51 dB** (Mean Whole-Run = 8.87 dB)
- **Arithmetic Overflows at Nominal Level:** **0 Overflows** across all seeds and scenarios.

### Gate A Hybrid Finding (Soft LMS-to-NLMS Transition)
In Task 3, explicit hard thresholding ($P_{\text{low}}, P_{\text{high}}$) with hysteresis was evaluated. When $P_{\text{low}}$ was chosen from the 25th percentile ($0.0826$) and 50th percentile ($0.1081$) of reference power, fixed-shift mode was active for 45%–75% of execution time. However, cancellation performance remained bit-identical ($\Delta = 0.00\text{ dB}$) to $\text{EPS\_EXP}=2$.  
**Scientific Conclusion:** With $\epsilon = 0.25$, the regularisation term inherently dominates during quiet periods ($P < 0.25$), causing the effective shift $s = \text{bitlen}(P + \epsilon) - F + K$ to remain constant ($s = 13$), smoothly transitioning to fixed-step LMS without requiring extra hardware comparators or state machines. The hybrid was rejected per Gate A rules, establishing eps-regularised NLMS-Shift as an optimal, continuous soft LMS-to-NLMS transition.

---

## 2. Fair Three-Way Hardware Comparison (Cyclone IV E EP4CE115F29C7, W=12)

All three architectures were compiled in Quartus Prime Lite 25.1std using the exact same top-level wrapper (`quartus/anc_de2_115_top.v`), timing constraints (`quartus/de2_115.sdc`), and Speed Grade 7 silicon models.

| Architecture | Word Length W | Logic Elements (LEs) | Dedicated Regs | 9-Bit Mults | Fmax (Slow 85°C) | Setup Slack (Slow 85°C) | Setup Slack (Slow 0°C) | Setup Slack (Fast 0°C) | Worst Hold Slack | Critical Path (Slow 85°C) |
|---|---|---|---|---|---|---|---|---|---|---|
| **LMS** | 12 | 1,885 (1.65%) | 1,148 | 4 (0.75%) | 59.90 MHz | **+3.305 ns** | +4.819 ns | +11.654 ns | +0.182 ns | `u_core\|i3[0]` $\to$ `w[0][11]` (16.598 ns) |
| **NLMS** | 12 | 2,697 (2.36%) | 1,425 | 4 (0.75%) | 61.72 MHz | **+3.798 ns** | +5.115 ns | +11.707 ns | +0.181 ns | `u_core\|i3[0]` $\to$ `w[20][5]` (16.088 ns) |
| **NLMS-Shift** | 12 | 2,690 (2.35%) | 1,213 | 4 (0.75%) | **61.98 MHz** | **+3.867 ns** | **+5.177 ns** | +11.688 ns | +0.181 ns | `u_core\|sh_r[4]` $\to$ `upd_q[25]` (16.061 ns) |
| *LMS (Ref)* | 11 | 1,775 (1.55%) | 1,069 | 4 (0.75%) | 60.05 MHz | +3.347 ns | +4.862 ns | +11.691 ns | +0.182 ns | `u_core\|i3[0]` $\to$ `w[3][10]` (16.556 ns) |
| *NLMS (Ref)* | 11 | 2,542 (2.22%) | 1,331 | 4 (0.75%) | 58.87 MHz | +3.014 ns | +4.511 ns | +11.528 ns | +0.181 ns | `u_core\|rem_r[35]` $\to$ `m[3]` (16.889 ns) |

### Timing & SDC Completeness (Task 5)
- **Clocks Defined:** `CLOCK_50` (50.00 MHz, 20.0 ns period), `AUD_BCLK` (3.072 MHz, 325.52 ns period).
- **Asynchronous Clock Groups:** `set_clock_groups -asynchronous -group [get_clocks CLOCK_50] -group [get_clocks AUD_BCLK]` applied.
- **I/O False Paths:** Synchronizer inputs (`KEY`, `SW`, `AUD_ADCLRCK`, `AUD_DACLRCK`, `AUD_ADCDAT`) and slow/asynchronous outputs (`LEDR`, `I2C_SCLK`, `I2C_SDAT`, `AUD_XCK`, `AUD_DACDAT`) fully constrained.
- **TimeQuest STA Check:** 0 unconstrained clocks, 0 unconstrained input ports, 0 unconstrained output ports. Design is 100% fully constrained in setup and hold.
- **Gate B Verdict:** **PASSED** (Slow 85°C setup slack $\ge +3.305\text{ ns}$, well exceeding $+0.5\text{ ns}$ target).

---

## 3. End-to-End Latency & Budget Share (Task 6)

| Parameter | LMS (W=12) | NLMS (W=12) | NLMS-Shift (W=12) | Unit / Reference |
|---|---|---|---|---|
| **Core Output Latency (Cycles)** | 35 cycles ($L+3$) | 37 cycles ($L+5$) | **37 cycles** ($L+5$) | Clock cycles (sample strobe to `out_valid`) |
| **Output Latency @ 50 MHz** | 700.0 ns | 740.0 ns | **740.0 ns** (0.740 $\mu\text{s}$) | Measured in simulation |
| **Output Latency @ Achieved Fmax** | 584.3 ns (59.90 MHz) | 599.5 ns (61.72 MHz) | **596.9 ns** (61.98 MHz) | Theoretical minimum latency |
| **Total Busy Cycles per Sample** | 73 cycles | 124 cycles | **72 cycles** | Cycles until `busy=0` (serial MAC + update) |
| **Share of 8 kHz Audio Budget** | 1.17% (73 / 6250) | 1.98% (124 / 6250) | **1.15%** (72 / 6250) | 8 kHz sample period = 125.0 $\mu\text{s}$ (6,250 cycles @ 50 MHz) |
| **Share of 48 kHz Audio Budget** | 7.01% (73 / 1041) | 11.91% (124 / 1041) | **6.92%** (72 / 1041) | 48 kHz sample period = 20.83 $\mu\text{s}$ (1,041 cycles @ 50 MHz) |
| **Simulated End-to-End Digital Delay** | 1 sample + 700 ns | 1 sample + 740 ns | **1 sample + 740 ns** | From `tb_anc_de2_115_top.v` (I2S frame alignment + core) |
| **Unmodelled Codec Group Delay** | ~30 audio samples | ~30 audio samples | ~30 audio samples | WM8731 internal ADC decimation (~$250\,\mu\text{s}$) + DAC interpolation (~$375\,\mu\text{s}$) |
| **Unmodelled Acoustic Propagation** | ~$290\,\mu\text{s}$ (10 cm) | ~$290\,\mu\text{s}$ (10 cm) | ~$290\,\mu\text{s}$ (10 cm) | Speed of sound $c = 343\text{ m/s}$ |

---

## 4. Input Level Robustness & Saturation Classification (Task 8)

Evaluated with reference input scaled across $[0.25\times, 0.5\times, 1.0\times, 2.0\times, 4.0\times]$ for $W=12, K=3, \text{EPS\_EXP}=2$:

| Reference Scale | `amp_steps` Final NR | `amp_steps` Total Ovf | `amp_steps` Saturation Breakdown | `wav` Final NR | `wav` Total Ovf | `wav` Saturation Breakdown |
|---|---|---|---|---|---|---|
| **0.25x** | 7.03 dB | 6,490 | **6,490 `sat_w` (Weight Saturation)**, 0 other | 1.93 dB | 0 | None (0 overflows) |
| **0.50x** | 13.48 dB | 3,724 | **3,724 `sat_w` (Weight Saturation)**, 0 other | 7.42 dB | 0 | None (0 overflows) |
| **1.00x (Nominal)** | **24.15 dB** | **0** | **0 Overflows** | **5.51 dB** | **0** | **0 Overflows** |
| **2.00x** | 15.30 dB | 63 | 63 `sat_in` (Input clipping), 0 internal | 5.47 dB | 0 | None (0 overflows) |
| **4.00x** | 11.10 dB | 2,042 | 2,042 `sat_in` (Input clipping), 0 internal | -0.66 dB | 279 | 279 `sat_in` (Input clipping), 0 internal |

### Saturation Mechanism Analysis
- **Low-Level Overflows (0.25x and 0.50x):** Confirmed to be 100% **weight saturation (`sat_w`)**. When reference noise is quiet, synthesizing the acoustic transfer function requires amplifying filter coefficients ($\mathbf{w} \approx \mathbf{h} / s$). Because weights are clamped to $[-1.0, +1.0)$ in Q1.11 fixed-point, large weight values saturate cleanly, preventing overflow wraparound.
- **High-Level Overflows (2.0x and 4.0x):** Confirmed to be 100% **input clipping (`sat_in`)** due to the fixed-point ADC headroom limit ($\pm 1.0$). Zero internal accumulator or weight saturations occur.

---

## 5. Acoustic Feedback (Howling) Scenario Analysis (Task 7)

A closed-loop acoustic feedback scenario was evaluated where speaker output re-enters the primary microphone through a delayed acoustic path ($D=8$ samples, ~1 kHz resonance, loop gain $g_{\text{loop}}=0.88$ near unity):
- **LMS (W=12):** Final NR = 4.25 dB, Whole-Run NR = 4.11 dB, Overflows = 0, Diverged = NO (Stable)
- **NLMS (W=12):** Final NR = 4.08 dB, Whole-Run NR = 4.11 dB, Overflows = 19, Diverged = NO (Stable)
- **NLMS-Shift (W=12):** Final NR = 4.29 dB, Whole-Run NR = 3.99 dB, Overflows = 0, Diverged = NO (Stable)

### Fundamental Limitations of Open-Loop Reference-Noise ANC
1. In an open-loop feedforward ANC structure, the reference microphone $x[n]$ samples external environmental noise $v[n]$. It has zero correlation with speech reflections and howling recirculations originating from the speaker output.
2. The acoustic feedback loop transforms the primary path into an IIR transfer function with sharp resonant poles near the unit circle. A 32-tap FIR filter cannot synthesize the long impulse response tail of high-Q acoustic feedback modes.
3. **Documentation Integrity:** Open-loop reference-noise ANC cannot eliminate acoustic howling. Feedback cancellation requires a dedicated closed-loop Acoustic Feedback Cancellation (AFC) filter tapped directly from the speaker line.

---

## 6. Real Audio WAV Performance Evaluation (Task 8)

- **Acoustic Chord (`acoustic_chord.wav`):** Final NR = **5.51 dB**, Whole-Run NR = **8.87 dB**.
- **Explanation:** The WAV test file is a multi-tone acoustic chord. Tonal signals have discrete, sparse spectral lines that result in a high eigenvalue spread in the reference autocorrelation matrix $\mathbf{R}_{xx}$. During the sustained chord resonance, the residual error is bounded by harmonic intermodulation, limiting final cancellation to ~5.5 dB. Over the full temporal envelope, whole-run cancellation reaches 8.87 dB with 0 arithmetic overflows.

---

## 7. Verification Regression Summary (Task 9)

- **Unit & Model Tests:** 18/18 tests passed (`py/test_anc.py`, `py/test_extended_verification.py`, `py/test_rtl_model.py`).
- **Questa Simulation Suite:** 55/55 testbenches passed (`results/metrics/questa_regression_summary.txt`), covering all architectures (LMS, NLMS, NLMS-Shift), word lengths ($W \in \{8, 10, 11, 12, 14, 16, 20, 28, 30, 31\}$), tap lengths ($L \in \{2, 5, 8, 16, 32\}$), accumulator widths ($11$ to $62$ bits), and corner saturation stimulus.
- **Quartus Synthesis:** Verified on Intel/Altera Cyclone IV E EP4CE115F29C7 via Quartus Prime Lite 25.1std.
- **Physical Board Test:** Marked as **PENDING (manual)** per task specification.
