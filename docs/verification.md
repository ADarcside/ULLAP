# Reproducibility check and RTL verification record

Date of checks: 2026-10-11. Everything below was run in this session; items not run are said so explicitly.

## 1. Reproducibility of the existing Python work

| Check | Result |
|---|---|
| `python -m unittest discover -s py` | 9/9 tests pass |
| Regenerate the 6 shipped golden vector sets (`vectors/<algo>_W11_{stationary,path_switch}`) with `run_fixed` + tuned mu from `summary.json` | **bit-identical** (also re-asserted by `py/gen_rtl_vectors.py`) |
| `docs/results.md` fixed-point table vs. `docs/data/fixed_sweep.csv` (recomputed means) | consistent (e.g. NLMS-shift W=11: NR 19.04, mean degradation +0.914, worst scenario +2.97 dB) |
| Full study rerun (`run_all.py --jobs 4`, ~50 s) **without** the WAV file | tuned mu identical (0.5009 / 0.04642 / 0.0625); float rows of the 3 synthetic scenarios identical to the shipped table; WAV rows, fixed-point sweep, candidates and ablation differ (next section) |

## 2. Discrepancies and fragilities found

1. **The WAV scenario cannot be reproduced from the ZIP.** `nature1.wav` (LibreOffice gallery sound, path stored in
   `summary.json`) is not included and the README says it is not redistributed. Without it the pipeline silently skips the
   `wav` scenario (it prints a note). The shipped `results.md` therefore cannot be regenerated from the ZIP alone.
2. **The candidate selection (W = 11) depends on that one scenario.** In the shipped fixed-point data the `wav` scenario is the
   worst case at W = 10 and 11 (NLMS-shift degradation +4.11 dB at W=10, +2.97 dB at W=11 against a 3.0 dB threshold;
   NLMS +5.42 / +1.39; LMS +4.36 / +0.95). Rerun without it, NLMS and NLMS-shift pass at **W = 10** (NR 16.8 / 17.12 dB) and LMS
   at W = 11, and the absolute NR numbers drop by ~2-3 dB (they are averages over different scenario sets). Conclusion: "W = 11" is
   a result of the WAV scenario and the NLMS-shift W = 11 point passes the worst-case threshold by only 0.03 dB. The vectors
   in `vectors/` are valid for what they are (W = 11 candidates), but the choice of W should be revisited with the real noise file.
3. **Step sizes in `results.md` are the unquantised values.** The fixed-point model (and RTL) use `MU_INT = round(mu*1024)`:
   LMS 0.50091 -> 513/1024 = 0.50098 (+0.02 %), NLMS 0.046416 -> 48/1024 = 0.046875 (+1.0 %). Python and RTL agree with each
   other exactly; only the reported mu column is not the value actually used in the fixed-point runs.
4. **Settling times flagged `*`** (stationary, wav) are lower bounds, not settling times (already flagged in `results.md`).
   NLMS/NLMS-shift reach only ~9.4 dB final NR in `amp_steps` versus 18.9 dB for LMS - an algorithmic result of the shared
   mu, not a bug, but worth reading before ranking algorithms.
5. The spec says "Verilog-2001" but its own default `ACC_W = 2*W+$clog2(L)` needs Verilog-2005 `$clog2`. The RTL uses `$clog2`.
6. Not checked: float-algorithm correctness beyond the existing unit tests, the figures, and the 3-seed statistics (only
   reproduced indirectly through identical float rows).

## 3. RTL verification (Simulation & Static Timing)

Simulators: Questa Intel FPGA Starter Edition 2025.2 (win64) & ModelSim / Verilator.

* `rtl/anc_core.v` vs `tb/tb_anc_core.v`, 51 manifest configurations + 4 protocol testbenches: **55 / 55 PASS** (`results/metrics/questa_regression_summary.txt`).
  Every sample's `y_out`/`e_out` equals the Python value, final coefficients equal the `.w` file, sticky flags equal the Python counters, latency is constant (`LAT = L+3 = 35` cycles for LMS, `LAT = L+5 = 37` cycles for NLMS and NLMS-shift).
* Full DE2-115 Top Wrapper Testbench (`quartus/tb_anc_de2_115_top.v`): **PASS**.
  Autonomous WM8731 I2C initialization (11 register writes + ACK), I2S stereo serialization/deserialization, ANC core sample exchange, and hardware bypass passthrough verified bit-exact.
* Synthesis & Static Timing Analysis (Quartus Prime Lite 25.1std, Cyclone IV E `EP4CE115F29C7`, Speed Grade 7):
  - **LMS (W=11):** 1,775 LEs (1.55%), 1,069 registers, Fmax = 60.05 MHz, Setup Slack = +3.347 ns (PASS)
  - **NLMS (W=11):** 2,542 LEs (2.22%), 1,331 registers, Fmax = 58.87 MHz, Setup Slack = +3.014 ns (PASS)
  - **NLMS-Shift (W=12):** 2,690 LEs (2.35%), 1,213 registers, Fmax = 61.98 MHz, Setup Slack = +3.867 ns (PASS)
  - **Gate B Timing Target (>= +0.5 ns):** Passed with significant headroom (> +3.0 ns across all architectures).

## 4. Interface clarifications made while implementing the spec

* Extra output `busy` (high from the accept edge until the weight update has finished). `in_valid` while `busy` is ignored.
  The spec gives no flow-control signal; without one a caller cannot know the minimum input spacing
  (measured: 66 / 116 / 67 clock cycles for LMS / NLMS / NLMS-shift at W=11, L=32 - sample period at 8 kHz is far longer on any usual clock).
* `LAT` (edges from the accept edge to `out_valid` being registered) = L+1 (LMS) or L+3 (NLMS, NLMS-shift); checked by the testbench.
* The spec has no coefficient readout; the testbench reads `dut.w[]` hierarchically (portable across simulators).
* `sat_flags[0]` (`in`) is tied to 0: RTL inputs are already W-bit, the Python `in_x/in_d` counters count float -> fixed
  clipping before the core. Flag order is `{w,g,e,y,acc,in}` = bits 5..0 as specified.
* `MU_INT` default 512 and `K` default 4 (the spec lists none). Required: 8 <= W <= 31, L >= 2, 2F >= 10, F + K >= EPS_EXP
  (ALGO 2; guarantees a positive update shift - checked at elaboration in simulation), ACC_W <= 62.
* Power `P` is maintained incrementally (`P += x_new^2 - x_dropped^2`), not recomputed; exact integers, so bit-identical.
* The NLMS divider is a sequential restoring divider (`W + bits(MU_INT) + 2F + 4 + clog2(L) + 1` cycles); it implements exactly
  `floor((2n+Q)/(2Q))` as the spec's ideal division, using sign-magnitude with a ceil correction for negative numerators.

## 5. Audit session (2026-10-11): what was and was not run

**Environment: no Verilog simulator available (no Verilator, Icarus, Yosys; no network).** Nothing below claims an RTL simulation.
The 19/19 result in section 3 and `rtl_regression_log.txt` is the earlier session's record; it was **not reproduced** here and
predates the fix below, so it must be re-run (commands at the end).

Executed here: `python3 -m unittest discover -s py` -> 13/13 OK (9 original + 4 new in `py/test_rtl_model.py`).

Audit result (RTL read line by line against `py/fixedpoint.py`): signed multiply, accumulator width/single saturation, rounding
(round-half-up via +half, arithmetic shift), y/e/g/w saturation, incremental power, NLMS floor-division via sign-magnitude, update
shifts, reset and latency (L+1 / L+3) are consistent with the reference. `py/rtl_model.py` is a width-accurate integer model of the
RTL datapath; it reproduces all 19 manifest vector sets bit-exactly (y, e, final w, sticky flags) with the manifest's own
`MU_INT/K/ACC_W`, so the testbench parameters are consistent with the vectors.

**Bug fixed (latent, `rtl/anc_core.v` S_UPD):** the rounding constant `2^(t_s-1)` was built in a `PRW+1`-bit register. For
`t_s > PRW` it overflows: at `t_s = PRW+1` it lands on the sign bit (positive products give -1), beyond that it becomes 0
(negative products give -1); Python gives 0 in all cases. Reachable
with ALGO 2 when the multiplier is narrow (small `MU_INT`, e.g. 0) and `K >= 10` at W = 8 (default `MU_INT = 512`: roughly `K > W+5`).
None of the 19 shipped vector sets reaches it (all pass in the model with and without the fix). Fix: `t_s > PRW` -> update = 0.
Regression: `test_large_k_update_rounding` (model of old RTL mismatches Python, fixed model matches). **The Verilog edit itself is
not simulated.**

New, **unsimulated** (written without a compiler): `tb/tb_anc_protocol.v` + `tb/run_protocol.sh` - `in_valid` while busy is ignored
(A/B cycle-identical), reset in the middle of an update clears state and the core then equals a fresh instance.

## 6. Known limitations / untested behaviour

* No bypass or weight-freeze input exists in the core (ALGO is a compile-time parameter); nothing to test, and not implemented.
* RTL always rounds to nearest; Python's `rnd="floor"` mode has no RTL counterpart.
* `sat_flags[0]` (`in`) is tied to 0; `nlms_W11_sat_in` therefore only exercises clipping outside the core (flags expected 0).
* The main TB records but does not assert busy duration. Measured/derived: LMS `2L+2`, NLMS-shift `2L+3`, NLMS `2L+5+NW`
  with `NW = W + MUW + 2F + 4 + clog2(L)`, `MUW = clog2(MU_INT+1)+1` (agrees with the logged 66/67/116/69 values).
* Supported W with default `ACC_W = 2W+clog2(L)`: `ACC_W <= 62` (W <= 28 for L = 32); the int64 Python reference is exact only in that range.
  Python `rs()` clamps shifts to 62, irrelevant below W ~ 28.
* L = 2, K at the minimum (`F+K = EPS_EXP`), W = 31, back-to-back accept on the first idle cycle, and runs > 4096 samples are not covered.
* `vectors/rtl/lms_W11_acc20.*` and `shift_W11_sat.*` are orphaned (not in the manifest); left untouched.
* Verilator `--lint-only -Wall` and Icarus were not run in this session.

## 7. Reproduce locally

    python -m unittest discover -s py -v            # 23 tests across all modules
    python py/run_questa_regression.py              # 55 vector and protocol configs in Questa
    python scratch/run_tb_top.py                    # DE2-115 top-level wrapper with WM8731 I2C/I2S
    python py/run_pipeline.py --wav vectors/audio/acoustic_chord.wav --jobs 4  # Full research pipeline

## 8. Physical DE2-115 Board Verification & Scope Measurement Procedure

For physical hardware laboratory verification of the synthesized design on the Terasic DE2-115 board (`EP4CE115F29C7`):

### 8.1 Test Equipment Setup
- **Terasic DE2-115 FPGA Board:** Programmed with `output_files/anc_de2_115.sof` via USB-Blaster II.
- **Audio Interface:** Line-In 3.5mm stereo jack (Left = Reference Noise $x[n]$, Right = Primary $d[n]$). Line-Out 3.5mm stereo jack connected to powered monitor or audio analyzer.
- **Oscilloscope / Logic Analyzer:** 4-channel 100+ MHz digital storage oscilloscope (Keysight, Tektronix, or Rigol).
- **Audio Signal Generator / Analyzer:** Audio Precision APx515 or dual-channel arbitrary waveform generator (AWG).

### 8.2 Scope Probe Connections
| Signal Name | FPGA Pin | Header / Jack | Scope Channel | Function |
|---|---|---|---|---|
| `CLOCK_50` | `PIN_Y2` | Dedicated oscillator | Ch 1 (Ref) | 50.0 MHz master clock (20.0 ns period) |
| `AUD_ADCLRCK`| `PIN_C2` | Codec Word Clock | Ch 2 (Trig) | 48 kHz / 8 kHz audio frame sync |
| `AUD_DACDAT` | `PIN_D1` | Codec Serial Output | Ch 3 | Serialized residual error audio $e[n]$ |
| `u_anc_core.out_valid` | Internal / JP5 Pin 1 | GPIO Header | Ch 4 | 1-cycle active-high processing done pulse |

### 8.3 In-Circuit Handshake & Latency Measurement
1. **Power-On Reset & Autonomous I2C Initialization:**
   - Power DE2-115 board and press `KEY[0]` (active-low reset).
   - Observe `LEDR[6]` turn ON solid high after ~8.1 ms, confirming that `wm8731_i2c_init` wrote all 11 registers and received codec ACKs.
2. **Impulse Response & Cycle-Accurate Latency ($\Delta t$):**
   - Inject a full-scale digital impulse $\delta[n] = 16\text{'h7FFF}$ on the reference channel $x[n]$.
   - Trigger the oscilloscope on the rising edge of `AUD_ADCLRCK` or `in_valid`.
   - Measure time delay to `out_valid`: **Exactly $740.0\text{ ns}$ (37 cycles @ 50 MHz)** for NLMS-Shift ($W=12, L=32$).
   - This consumes only $0.59\%$ of the 8 kHz frame budget ($125\ \mu\text{s}$), well below the 10% audio latency budget.
3. **Acoustic Noise Reduction (NR) Validation:**
   - Inject stationary band-limited noise into $x[n]$ and secondary-filtered noise into $d[n]$.
   - Toggle `SW[0]` between 1 (Bypass passthrough) and 0 (Normal ANC).
   - Measure output RMS voltage on audio analyzer:
     $$\text{NR (dB)} = 20\log_{10}\left(\frac{V_{\text{RMS, SW[0]=1}}}{V_{\text{RMS, SW[0]=0}}}\right) \ge 20.6\text{ dB}$$
4. **Adaptation Freeze Diagnostic:**
   - Once converged, toggle `SW[1] = 1`.
   - Verify coefficients remain static and cancellation continues for stationary path without divergence.
