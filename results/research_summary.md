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

### Gate A Hybrid Finding (Structural Identity & Effective Step Size)
In Task 3, explicit hard thresholding ($P_{\text{low}}, P_{\text{high}}$) was investigated. Analysis and profiling revealed that the hybrid power switch is structurally identical to eps-only for thresholds below eps: because $P + \epsilon$ is lower-bounded by $\epsilon = 0.25$, the leading-one position / bit_length of $(P + \epsilon)$ is strictly constant ($s = 13$) for all $P < 0.25$. Consequently, the filter naturally operates with a constant step size in the quiet regime without requiring any explicit mode-switching logic.

Furthermore, cancellation results in this regime depend directly on the effective regularised step size:
$$\mu_{\text{eff}} = 2^{\text{EPS\_EXP} - K}$$
This relationship is verified by the sweep rows where configurations with equal $(\text{EPS\_EXP} - K)$ achieve equivalent steady-state tracking behavior (e.g. $\text{EPS\_EXP}=2, K=3$ vs $\text{EPS\_EXP}=3, K=4$ both having $\text{EPS\_EXP}-K = -1$). Hence, eps-regularised NLMS-Shift intrinsically implements the optimal soft LMS-to-NLMS transition.

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

## 3. End-to-End Latency & Budget Share (48 kHz Codec Operation)

From the WM8731 autonomous configuration (`quartus/wm8731_i2c_init.v`), Register 8 (`SR[3:0]=0000`, Normal mode, 256$f_s$) and the $12.5\text{ MHz}$ master clock (`AUD_XCK` = 50 MHz / 4) configure the codec for $f_s = 48.828\text{ kHz}$ (nominal **48 kHz**), corresponding to an audio sample period of $T_{\text{sample}} = 20.83\,\mu\text{s}$ (1,041 cycles @ 50 MHz, or exactly 1,024 cycles at $12.5\text{ MHz} / 256$).

| Parameter | LMS (W=12) | NLMS (W=12) | NLMS-Shift (W=12) | Notes / Datasheet Source |
|---|---|---|---|---|
| **Core Output Latency (Cycles)** | 35 cycles ($L+3$) | 37 cycles ($L+5$) | **37 cycles** ($L+5$) | Clock cycles from `in_valid` strobe to `out_valid` |
| **FPGA Processing Latency @ 50 MHz** | **700.0 ns** (0.700 $\mu\text{s}$) | **740.0 ns** (0.740 $\mu\text{s}$) | **740.0 ns** (0.740 $\mu\text{s}$) | Hardware measured via Questa testbench |
| **Total Busy Cycles per Sample** | 70 cycles | 91 cycles | **73 cycles** | Cycles until `busy=0` (serial MAC + weight update) |
| **Execution Time per Sample @ 50 MHz** | 1.40 $\mu\text{s}$ | 1.82 $\mu\text{s}$ | **1.46 $\mu\text{s}$** | Time processing core is active |
| **Busy Share of 48 kHz Budget** | **6.72%** (70 / 1041) | **8.74%** (91 / 1041) | **7.01%** (73 / 1041) | At nominal 48.0 kHz ($20.83\,\mu\text{s}$ window) |
| **Busy Share of 48.83 kHz Budget** | **6.84%** (70 / 1024) | **8.89%** (91 / 1024) | **7.13%** (73 / 1024) | At 50 MHz / 1024 ($20.48\,\mu\text{s}$ exact window) |
| **WM8731 ADC Decimation Filter Delay** | ~12 samples (250.0 $\mu\text{s}$) | ~12 samples (250.0 $\mu\text{s}$) | ~12 samples (250.0 $\mu\text{s}$) | **Cited: WM8731 Datasheet Rev 4.9**, Table "Digital Filter Characteristics" ($12/f_s$) |
| **WM8731 DAC Interpolation Filter Delay** | ~11 samples (229.2 $\mu\text{s}$) | ~11 samples (229.2 $\mu\text{s}$) | ~11 samples (229.2 $\mu\text{s}$) | **Cited: WM8731 Datasheet Rev 4.9**, Table "Digital Filter Characteristics" ($11/f_s$) |
| **I2S Serial Framing Overhead** | 2 samples (41.67 $\mu\text{s}$) | 2 samples (41.67 $\mu\text{s}$) | 2 samples (41.67 $\mu\text{s}$) | 1 sample frame shift in ADC receiver + 1 sample in DAC transmitter |
| **Total End-to-End System Delay** | **521.6 $\mu\text{s}$** (~0.52 ms) | **521.6 $\mu\text{s}$** (~0.52 ms) | **521.6 $\mu\text{s}$** (~0.52 ms) | Codec filters (479.2 $\mu\text{s}$) + I2S (41.7 $\mu\text{s}$) + FPGA core (0.74 $\mu\text{s}$) |
| **FPGA Processing Latency Share** | **0.13%** | **0.14%** | **0.14%** | FPGA core accounts for < 0.15% of total end-to-end latency |

---

## 4. Input Level Robustness & Saturation Classification (Task 5 & Task 8)

Evaluated with reference input scaled across $[0.25\times, 0.5\times, 1.0\times, 2.0\times, 4.0\times]$ for LMS ($\mu=0.5$), standard NLMS ($\mu=0.5$), and NLMS-Shift ($W=12, K=3, \text{EPS\_EXP}=2$) across all 4 scenarios and 3 seeds (192,000 samples per point):

| Scale | Algorithm | NR Avg (dB) | Total Overflows | Total Samples | Overflow Rate | Criterion ($< 10^{-3}$) |
|---|---|---|---|---|---|---|
| **0.25x** | LMS ($\mu=0.5$) | 5.28 dB | 23,913 | 192,000 | $1.25 \times 10^{-1}$ | FAIL |
| **0.25x** | NLMS ($\mu=0.5$) | 6.46 dB | 86,442 | 192,000 | $4.50 \times 10^{-1}$ | FAIL |
| **0.25x** | NLMS-Shift ($K=3, \epsilon=2$) | 3.60 dB | 7,589 | 192,000 | $3.95 \times 10^{-2}$ | FAIL |
| **0.50x** | LMS ($\mu=0.5$) | 10.65 dB | 16,821 | 192,000 | $8.76 \times 10^{-2}$ | FAIL |
| **0.50x** | NLMS ($\mu=0.5$) | 11.34 dB | 35,360 | 192,000 | $1.84 \times 10^{-1}$ | FAIL |
| **0.50x** | NLMS-Shift ($K=3, \epsilon=2$) | 8.83 dB | 6,393 | 192,000 | $3.33 \times 10^{-2}$ | FAIL |
| **1.00x (Nominal)** | LMS ($\mu=0.5$) | 15.00 dB | 0 | 192,000 | **$0.00$** | **PASS** |
| **1.00x (Nominal)** | NLMS ($\mu=0.5$) | 13.53 dB | 0 | 192,000 | **$0.00$** | **PASS** |
| **1.00x (Nominal)** | NLMS-Shift ($K=3, \epsilon=2$) | 15.07 dB | 0 | 192,000 | **$0.00$** | **PASS** |
| **2.00x** | LMS ($\mu=0.5$) | 9.30 dB | 3,932 | 192,000 | $2.05 \times 10^{-2}$ | FAIL |
| **2.00x** | NLMS ($\mu=0.5$) | 10.76 dB | 63 | 192,000 | **$3.28 \times 10^{-4}$** | **PASS** |
| **2.00x** | NLMS-Shift ($K=3, \epsilon=2$) | 14.89 dB | 63 | 192,000 | **$3.28 \times 10^{-4}$** | **PASS** |
| **4.00x** | LMS ($\mu=0.5$) | 2.54 dB | 37,314 | 192,000 | $1.94 \times 10^{-1}$ | FAIL |
| **4.00x** | NLMS ($\mu=0.5$) | 8.43 dB | 2,323 | 192,000 | $1.21 \times 10^{-2}$ | FAIL |
| **4.00x** | NLMS-Shift ($K=3, \epsilon=2$) | 12.59 dB | 2,323 | 192,000 | $1.21 \times 10^{-2}$ | FAIL |

### Operational Findings & Passing Range
- **Passing Input-Level Range:**
  - **LMS:** Passes only at nominal level $[1.0\times]$ ($\text{overflow rate} = 0$). Fails below $1.0\times$ due to coefficient saturation and above $1.0\times$ due to step divergence.
  - **NLMS and NLMS-Shift:** Pass across **$[1.0\times \text{ to } 2.0\times]$** (rate $< 10^{-3}$ at $2.0\times$ is purely input rail clipping `sat_in`; internal arithmetic has 0 overflows).
- **Failure Mechanisms:**
  - Below $1.0\times$ ($0.25\times, 0.5\times$): Overflows are 100% weight saturation (`sat_w`). When reference noise is quiet relative to primary sensor noise, synthesizing the acoustic transfer function requires weight amplitudes $|w| > 1.0$, which saturate at the Q1.11 range boundaries $[-1.0, +1.0)$.
  - Above $2.0\times$ ($4.0\times$): Overflows are 100% ADC input clipping (`sat_in`) where $x[n]$ exceeds the dynamic range.
- **Architectural Proposal (No RTL Change):**
  To support attenuated reference sensor scenarios ($< 0.5\times$) without weight saturation, future revisions can allocate 1 or 2 integer guard bits to filter coefficients (e.g., Q2.10 or Q3.9 weight representation). This increases coefficient dynamic range to $[-2.0, +2.0)$ or $[-4.0, +4.0)$ without altering internal multiplier width.

---

## 5. Acoustic Feedback Scenario & Metrics Reconciliation (Task 7)

Evaluation of open-loop feedforward ANC versus closed-loop acoustic feedback ($D=8$ samples, loop gain $g_{\text{loop}}=0.88$):

| Evaluation Mode | Algorithm | Settled NR (dB) | Total Power Ratio (dB) | Overflows | Stable? |
|---|---|---|---|---|---|
| **Open-Loop Feedforward ANC** | LMS | 4.25 dB | 4.11 dB | 0 | YES |
| **Open-Loop Feedforward ANC** | NLMS | 4.08 dB | 4.11 dB | 19 | YES |
| **Open-Loop Feedforward ANC** | NLMS-Shift | 4.29 dB | 3.99 dB | 0 | YES |
| **Closed-Loop Simulation** | NLMS-Shift | N/A | 10.05 dB | 0 | YES |

### Metrics Reconciliation & Acoustic Limitations
1. **Reconciliation of "4.25 dB Final NR" vs "10.05 dB Suppression":**
   - **4.25 dB Final NR** measures standard noise reduction of the external reference-correlated noise component in the settled window: $10 \log_{10}(\text{Var}(d - s) / \text{Var}(e - s))$. Because recirculating acoustic feedback is uncorrelated with the reference input $x[n]$, feedforward ANC can only cancel the linear reference portion.
   - **10.05 dB Total Suppression** measures the raw signal-to-residual power ratio: $10 \log_{10}(E[(s + nz)^2] / E[e_{\text{settled}}^2])$ in closed-loop operation.
2. **No Howling Suppression Claim:**
   Feedforward ANC cancels noise correlating with the reference microphone; it does **not** provide Acoustic Feedback Cancellation (AFC) or howling suppression. Howling elimination requires an internal adaptive feedback cancellation filter or phase-notch filter placed in the loudspeaker path.

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
