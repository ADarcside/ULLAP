# Phase 0 Baseline Record (`baseline-v0`)

**Freeze Date:** 2026-10-17  
**Git Tag:** `baseline-v0`  
**Target Hardware:** Terasic DE2-115 (Altera/Intel Cyclone IV E `EP4CE115F29C7`)  
**Quartus Prime Version:** 25.1std.0 Build 1129 Lite Edition  

---

## 1. Frozen Baseline Parameters

* **Algorithm Under Study:** NLMS-Shift (Dividerless power-of-2 normalization)
* **Word Length:** $W = 12$ bits ($F = 11$ fractional bits)
* **Filter Length:** $L = 32$ taps
* **Step Size:** $\mu = 2^{-4} = 0.0625$ ($K = 4$)
* **Original Regularizer:** $\epsilon = 2^{-10}$ (`EPS_EXP = 10`)
* **Core Latency:** $LAT = L + 3$ (LMS), $L + 5$ (NLMS / NLMS-Shift) cycles

---

## 2. Cancellation Performance Baseline (Float Reference & $W=12$ Fixed-Point)

| Scenario | Algorithm | Float NR Final (dB) | Fixed NR Final (dB) | Degradation (dB) | Overflows |
|---|---|---|---|---|---|
| **Stationary Noise** | NLMS-Shift | 20.8 | 20.7 | +0.10 | 0 |
| **Amplitude Steps** | NLMS-Shift | 9.5 | 9.4 | +0.10 | 0 |
| **Path Switch** | NLMS-Shift | 20.6 | 20.5 | +0.10 | 0 |
| **WAV Audio (`acoustic_chord.wav`)** | NLMS-Shift | -11.3 | -11.4 | +0.10 | 0 |
| **WAV Audio (`acoustic_chord.wav`)** | LMS | +5.4 | +5.3 | +0.10 | 0 |

---

## 3. Hardware Synthesis & Timing Baseline (From Unpipelined Synthesis)

* **Status:** SYNTHESIZED (Quartus Prime Lite 25.1, October 13, 2026)
* **Device:** Intel Cyclone IV E `EP4CE115F29C7`
* **Logic Elements (LEs):** 2,531 (2.21%)
* **Combinational Cells:** 2,302
* **Dedicated Logic Registers:** 1,113
* **Embedded 9-bit Multipliers:** 8
* **Hardware Dividers:** 0
* **Timing Constraint:** 50.00 MHz (`CLOCK_50`, period = 20.000 ns)
* **Setup Slack:** **-7.655 ns (FAIL)**
* **$F_{\max}$ (Slow 85°C):** **36.16 MHz**
* **$F_{\max}$ (Slow 0°C):** **39.47 MHz**
* **Total Negative Slack (TNS):** -2630.748 ns
* **Critical Path:** `anc_core|i[2] -> anc_core|w[28][7]` (Path delay = 27.562 ns: unpipelined tap read multiplexing, multiply, round, saturate, and write-back in a single clock cycle)
* **Hold Slack:** +0.394 ns (PASS)

*Note on Pipelined Timing:* The 3-stage multiplier pipeline (`operand regs` $\rightarrow$ `product reg` $\rightarrow$ `consume/writeback`) was implemented to break this 27.562 ns critical path. Local compilation of the pipelined core in the current workspace directory is blocked by OneDrive's filesystem minifilter lock (`Error 297009`); hence, post-pipeline timing is labeled PENDING.

---

## 4. Verification Baseline

* **Unit Tests:** `python -m unittest discover -s py -v` -> **23 / 23 PASS**
* **Questa Simulation Regression:** `python py/run_questa_regression.py` -> **55 / 55 PASS** (51 manifest configurations + 4 protocol corner-case tests)
* **Bit-Exactness:** RTL $y$, $e$, final weights $w$, and sticky saturation flags match `py/fixedpoint.py` / `py/rtl_model.py` with 0 mismatches.
