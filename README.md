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
8. `fig8_resource_utilization`: FPGA Logic Elements (LEs) and embedded 9-bit multipliers.
9. `fig9_timing_comparison`: Maximum clock frequency ($F_{\max}$) and setup slack.
10. `fig10_performance_cost_tradeoff`: Cancellation quality (dB) vs FPGA resource cost.

---

## 5. Experimental Results & Validated Candidates

Recent simulation and extended verification runs (`results/research_summary.md`):

### Tuned Step Sizes ($\mu$)
- **LMS:** $\mu = 0.5009$
- **NLMS:** $\mu = 0.0464$
- **NLMS-Shift:** $\mu = 0.0625$ ($2^{-4}$, dividerless leading-one barrel shift)

### Performance Across Test Scenarios
| Scenario | Algorithm | Final NR (dB) | Whole-Run NR (dB) | Settling Time (ms) | Tracking Time (ms) | Overflows |
|---|---|---|---|---|---|---|
| **Stationary Noise** | LMS | 20.3 ± 0.6 | 15.2 | 1784 | n/a | 0 |
| **Stationary Noise** | NLMS | 20.7 ± 0.4 | 15.7 | 1791 | n/a | 0 |
| **Stationary Noise** | NLMS-Shift | 20.8 ± 0.5 | 15.5 | 1791 | n/a | 0 |
| **Path Switch ($t = 1.0\text{ s}$)** | LMS | 20.6 ± 0.3 | 12.0 | 722 | 706 | 0 |
| **Path Switch ($t = 1.0\text{ s}$)** | NLMS | 20.7 ± 0.2 | 11.8 | 698 | 690 | 0 |
| **Path Switch ($t = 1.0\text{ s}$)** | NLMS-Shift | 20.6 ± 0.3 | 11.6 | 694 | 674 | 0 |

### Selected Cyclone IV E Hardware Candidate
- **Selected Word-Length:** $W = 11$ bits ($F = 10$ fractional bits), Accumulator Width $\text{ACC\_W} = 27$ bits.
- **Fixed-Point NR:** $16.1\text{ dB}$ (Degradation vs. Float: $+0.46\text{ dB}$, **0 overflows**).
- **Arithmetic Architecture:** $2L+1$ multipliers, zero hardware dividers.
- **Extended Verification:** 9/9 verification tests passed in [`results/metrics/verification_summary.json`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/results/metrics/verification_summary.json).

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
