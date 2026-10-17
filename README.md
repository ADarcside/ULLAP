# Adaptive Noise Cancellation (ANC) Research Project: LMS vs NLMS vs NLMS-Shift

**Target Platform:** Terasic DE2-115 Development Board (Intel/Altera Cyclone IV E `EP4CE115F29C7`) with Quartus Prime Lite.  
**Software Pipeline:** Platform-independent Python simulation, fixed-point modeling, golden vector generation, and research-quality visualization.

---

## 1. Directory Structure

| Directory | Content |
|---|---|
| `system_design/` | Comprehensive technical specifications: architecture (`architecture.md`), execution & research pipelines (`pipeline.md`), mathematical algorithms (`algorithm.md`), and Mermaid operational flowcharts (`flowchart.md`). |
| `py/` | Algorithm reference models (`algos.py`), fixed-point engine (`fixedpoint.py`), metrics (`metrics.py`), test scenarios (`signals.py`), pipeline runner (`run_pipeline.py`), visualization suite (`visualize.py`), Quartus report importer (`import_quartus.py`), verification suite (`verify_core.py`), and unit tests (`test_*.py`). |
| `rtl/` | `anc_core.v`: Portable, vendor-neutral Verilog core supporting LMS, NLMS, and NLMS-shift. No vendor IP or proprietary macros. |
| `quartus/` | DE2-115 board-specific pin assignments (`de2_115_pins.tcl`) and modular top-level codec wrapper (`anc_de2_115_top.v`). |
| `results/` | Unified experimental output: `raw/` (sample signals), `metrics/` (CSV tables, verification JSON), `plots/` (10 publication figures in 300 DPI PNG and vector PDF), `metadata/` (experiment configurations), `quartus/` (hardware report templates and parsed metrics). |
| `tb/` | Verilog self-checking testbench (`tb_anc_core.v`), test vector manifest (`manifest.txt`), and regression scripts. |
| `vectors/` | Golden `.vec` and `.w` test vectors for RTL verification; `vectors/audio/` contains test audio files (`acoustic_chord.wav`, `sine_sweep.wav`). |
| `docs/` | Research findings (`results.md`), verification record (`verification.md`), RTL interface spec (`rtl_interface.md`), and backward-compatible mirrors. |
| `archive/` | Reserved for the original effects processor (preserved untouched). |

---

## 2. System Design Specifications (`system_design/`)

Detailed hardware blueprints, cycle-accurate pipeline schedules, mathematical algorithm proofs, and operational flowcharts are compiled in [`system_design/`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/):

- [**`architecture.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/architecture.md): Complete board-level and chip-level architecture for the Terasic DE2-115 with Intel Cyclone IV E `EP4CE115F29C7`, Wolfson WM8731 codec interface (I2S transceiver & autonomous I2C engine), single-multiplier time-multiplexed DSP core, and FPGA resource utilization.
- [**`pipeline.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/pipeline.md): Dual-pipeline specification detailing the cycle-accurate 3-stage hardware multiplier pipeline ($LAT = L+3$ for LMS, $L+5$ for NLMS/NLMS-Shift) and the 11-stage autonomous software characterization pipeline.
- [**`algorithm.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/algorithm.md): Mathematical derivations for LMS, NLMS, and NLMS-Shift, stability bounds ($0 < \mu < 2/\text{tr}(\mathbf{R})$), stability proof of the dividerless power-of-2 approximation ($\mu_{\text{eff}} \in [\mu/2, \mu)$), and signed $Q1.(W-1)$ fixed-point arithmetic rules.
- [**`flowchart.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/flowchart.md): Visual Mermaid flowcharts for system startup, `anc_core` FSM state transitions, algorithmic branch execution, and sticky saturation flag handling.
- [**`README.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/README.md): Index guide for the technical specifications folder.

---

## 3. Running Experiments & Reproducing Plots

### Installation
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run Unit Tests & RTL Verification
```bash
python -m unittest discover -s py -v
```
Executes all 23 unit tests, checking rounding, overflow flags, step-size normalization, vector roundtrip, protocol corner-cases, and extended verification.

### Run Full Experimental & Visualization Pipeline (Single Command)
```bash
# Fast smoke run (~1-2 minutes)
python py/run_pipeline.py --quick

# Full research study with real WAV audio
python py/run_pipeline.py --wav vectors/audio/acoustic_chord.wav --jobs 4
```

This single command automatically:
1. Tunes optimal step sizes ($\mu$) on an unseen seed across algorithms.
2. Evaluates floating-point performance across all 4 scenarios (`stationary`, `amp_steps`, `path_switch`, `wav`).
3. Executes a fixed-point bit-width sweep from 8 to 24 bits, calculating noise reduction (dB), degradation vs float, and SQNR.
4. Identifies optimal hardware candidate word-lengths and performs accumulator-width ablation.
5. Runs extended verification of the RTL reference model.
6. Generates all **10 publication-quality figures** as both high-resolution 300 DPI PNGs and vector PDFs in `results/plots/`.
7. Exports structured CSV tables to `results/metrics/` and raw signal `.npz` arrays to `results/raw/`.
8. Updates `docs/results.md` and `results/research_summary.md`.

---

## 4. Generated Visualizations (`results/plots/`)

All figures are exported as both high-res PNG (300 DPI) and vector PDF:
1. `fig1_convergence`: Convergence comparison across LMS, NLMS, and NLMS-shift.
2. `fig2_waveforms`: Time-domain waveforms (Primary $d[n]$, Reference $x[n]$, Clean $s[n]$, Residual $e[n]$).
3. `fig3_residual_error`: Residual error power ($10\log_{10} e^2$) over time vs baseline.
4. `fig4_tracking_response`: Dynamic adaptation before and after abrupt changes.
5. `fig5_noise_reduction_comparison`: Grouped bar chart comparing final and whole-run NR across scenarios.
6. `fig6_bitwidth_sweep`: Cancellation performance, float degradation, and SQNR vs word-length $W$.
7. `fig7_coef_trajectories`: Evolution of selected filter tap weights over time.
8. `fig8_resource_utilization`: FPGA Logic Elements (LEs) and dedicated registers across LMS, NLMS, and NLMS-Shift.
9. `fig9_timing_comparison`: Maximum clock frequency ($F_{\max}$) and setup slack (all architectures >= +3.0 ns PASS on Speed Grade 7).
10. `fig10_performance_cost_tradeoff`: Cancellation quality (dB) vs FPGA resource cost.
11. `fig11_latency_comparison`: Processing latency in clock cycles, processing time at 50 MHz, and share of 8 kHz audio budget (< 2%).

---

## 5. Experimental Results & Validated Candidates

Recent simulation and extended verification runs (`results/research_summary.md`):

### Tuned Step Sizes & Regularisation
- **LMS:** $\mu = 0.5009$ (Fixed step size)
- **NLMS:** $\mu = 0.1468$ ($\epsilon = 0.25$, restoring divider)
- **NLMS-Shift:** $K = 3$ ($\mu = 2^{-3} = 0.125$, $\text{EPS\_EXP} = 2$, dividerless leading-one barrel shift)

### Performance Across Test Scenarios (W=12, L=32)
| Scenario | Algorithm | Final NR (dB) | Whole-Run NR (dB) | Settling Time (ms) | Tracking Time (ms) | Overflows |
|---|---|---|---|---|---|---|
| **Stationary Noise** | LMS | 20.3 ± 0.6 | 15.2 | 1784 | n/a | 0 |
| **Stationary Noise** | NLMS | 21.3 ± 0.6 | 14.8 | 1786 | n/a | 0 |
| **Stationary Noise** | NLMS-Shift | **22.2 ± 0.4** | 13.2 | 1784 | n/a | **0** |
| **Amplitude Steps** | LMS | 18.9 ± 0.7 | 18.5 | 484 | 74 | 0 |
| **Amplitude Steps** | NLMS | 18.7 ± 0.2 | 18.9 | 465 | 198 | 0 |
| **Amplitude Steps** | NLMS-Shift | **24.2 ± 1.8** | 16.9 | 484 | 197 | **0** |
| **Path Switch ($t = 1.0\text{ s}$)** | LMS | 20.6 ± 0.3 | 12.0 | 722 | 706 | 0 |
| **Path Switch ($t = 1.0\text{ s}$)** | NLMS | 20.6 ± 0.3 | 11.3 | 708 | 678 | 0 |
| **Path Switch ($t = 1.0\text{ s}$)** | NLMS-Shift | **19.0 ± 0.5** | 9.5 | 722 | 705 | **0** |
| **Real Audio WAV** | NLMS-Shift | **5.5 ± 0.1** | 8.9 | 128 | n/a | **0** |
| **Acoustic Feedback** | NLMS-Shift | **4.3 ± 0.1** | 4.0 | 0 | n/a | **0** |

### Selected Cyclone IV E Hardware Synthesis (W=12, Speed Grade 7)
- **LMS (W=12):** 1,885 LEs (1.65%), 1,148 registers, 4 DSP mults, $F_{\max} = 59.90\text{ MHz}$, Setup Slack = **+3.305 ns (PASS)**.
- **NLMS (W=12):** 2,697 LEs (2.36%), 1,425 registers, 4 DSP mults, $F_{\max} = 61.72\text{ MHz}$, Setup Slack = **+3.798 ns (PASS)**.
- **NLMS-Shift (W=12):** 2,690 LEs (2.35%), 1,213 registers, 4 DSP mults, $F_{\max} = \mathbf{61.98\text{ MHz}}$, Setup Slack = $\mathbf{+3.867\text{ ns}}$ **(PASS)**.
- **Timing Closure (Gate B):** Full timing closure across all corners (Slow 85°C, Slow 0°C, Fast 0°C) with 0 unconstrained paths.
- **Latency & Audio Budget:** Output latency $LAT = 37$ cycles ($740\text{ ns}$ @ 50 MHz), 72 busy cycles per sample (**$1.15\%$ of 8 kHz audio budget**).
- **Verification Suite:** 18/18 Python unit tests PASSED, 55/55 Questa RTL simulation regression tests PASSED, top wrapper verified. Physical board test is marked **PENDING (manual)**.


---

## 6. Measurement Classification & Integrity

To preserve scientific rigor, all data is categorized by source:
- **Simulated (Software Reference)**: Algorithm performance, MSE, noise reduction (dB), and bit-width sweeps computed via Python reference models (`algos.py`, `fixedpoint.py`).
- **Synthesized / Fitted (Quartus Reports)**: Logic elements, combinational cells, dedicated registers, and embedded multipliers parsed directly from Quartus `.fit.rpt`.
- **Timing Analyzed (TimeQuest)**: $F_{\max}$ and setup slack extracted from Quartus `.sta.rpt` across operating corners (1200mV 85C / 0C).
- **Estimated (Quartus Power Analyzer)**: Thermal power dissipation.
- **Physical Measurements**: Physical board-level measurements using audio analyzers or oscilloscope on the DE2-115 board.

*Note: In the absence of Quartus compilation files, hardware figures are explicitly labeled as "UNAVAILABLE / PENDING" rather than fabricated.*

---

## 7. Integrating Quartus Compilation Results

When Quartus Prime Lite compiles the DE2-115 project:

1. **Automatic Report Parsing**:
   ```bash
   python py/import_quartus.py --fit-rpt output_files/anc_de2_115.fit.rpt --sta-rpt output_files/anc_de2_115.sta.rpt --algo nlms_shift --w 11
   ```
2. **Documented CSV Import**:
   Update `results/quartus/quartus_reports_template.csv` with measured synthesis values and run:
   ```bash
   python py/import_quartus.py --csv results/quartus/quartus_reports_template.csv
   ```
   Then re-run `python py/run_pipeline.py` to populate Figures 8, 9, and 10 with actual synthesis data.

---

## 8. Extending the Framework

- **Adding an Algorithm**: Add the algorithm definition to `py/algos.py` (float) and `py/fixedpoint.py` (integer model), register it in `ALGOS` in `py/experiment_config.py`, and implement corresponding RTL state handling in `rtl/anc_core.v`.
- **Adding a Test Scenario**: Add the scenario generator to `py/signals.py` under `make_scenario` and add its name to `SCENARIOS`.
