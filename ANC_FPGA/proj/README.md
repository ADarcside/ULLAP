# Adaptive Noise Cancellation (ANC) Research Project: LMS vs NLMS vs NLMS-Shift

**Target Platform:** Terasic DE2-115 Development Board (Intel/Altera Cyclone IV E `EP4CE115F29C7`) with Quartus Prime Lite.  
**Software Pipeline:** Platform-independent Python simulation, fixed-point modeling, golden vector generation, and research-quality visualization.

---

## 1. Directory Structure

| Directory | Content |
|---|---|
| `py/` | Algorithm reference models (`algos.py`), fixed-point engine (`fixedpoint.py`), metrics (`metrics.py`), test scenarios (`signals.py`), pipeline runner (`run_pipeline.py`), visualization suite (`visualize.py`), Quartus report importer (`import_quartus.py`), verification suite (`verify_core.py`), and unit tests (`test_*.py`). |
| `rtl/` | `anc_core.v`: Portable, vendor-neutral Verilog core supporting LMS, NLMS, and NLMS-shift. No vendor IP or proprietary macros. |
| `quartus/` | DE2-115 board-specific pin assignments (`de2_115_pins.tcl`) and modular top-level codec wrapper (`anc_de2_115_top.v`). |
| `results/` | Unified experimental output: `raw/` (sample signals), `metrics/` (CSV tables, verification JSON), `plots/` (10 publication figures in 300 DPI PNG and vector PDF), `metadata/` (experiment configurations), `quartus/` (hardware report templates and parsed metrics). |
| `tb/` | Verilog self-checking testbench (`tb_anc_core.v`), test vector manifest (`manifest.txt`), and regression scripts. |
| `vectors/` | Golden `.vec` and `.w` test vectors for RTL verification; `vectors/audio/` contains test audio files (`acoustic_chord.wav`, `sine_sweep.wav`). |
| `docs/` | Research findings (`results.md`), verification record (`verification.md`), RTL interface spec (`rtl_interface.md`), and backward-compatible mirrors. |
| `archive/` | Reserved for the original effects processor (preserved untouched). |

---

## 2. Running Experiments & Reproducing Plots

### Installation
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run Unit Tests & RTL Verification
```bash
python -m unittest discover -s py -v
```
Executes all 18 unit tests, checking rounding, overflow flags, step-size normalization, vector roundtrip, and extended verification.

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

## 3. Generated Visualizations (`results/plots/`)

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

## 4. Measurement Classification & Integrity

To preserve scientific rigor, all data is categorized by source:
- **Simulated (Software Reference)**: Algorithm performance, MSE, noise reduction (dB), and bit-width sweeps computed via Python reference models (`algos.py`, `fixedpoint.py`).
- **Synthesized / Fitted (Quartus Reports)**: Logic elements, combinational cells, dedicated registers, and embedded multipliers parsed directly from Quartus `.fit.rpt`.
- **Timing Analyzed (TimeQuest)**: $F_{\max}$ and setup slack extracted from Quartus `.sta.rpt` across operating corners (1200mV 85C / 0C).
- **Estimated (Quartus Power Analyzer)**: Thermal power dissipation.
- **Physical Measurements**: Physical board-level measurements using audio analyzers or oscilloscope on the DE2-115 board.

*Note: In the absence of Quartus compilation files, hardware figures are explicitly labeled as "UNAVAILABLE / PENDING" rather than fabricated.*

---

## 5. Integrating Quartus Compilation Results

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

## 6. Extending the Framework

- **Adding an Algorithm**: Add the algorithm definition to `py/algos.py` (float) and `py/fixedpoint.py` (integer model), register it in `ALGOS` in `py/experiment_config.py`, and implement corresponding RTL state handling in `rtl/anc_core.v`.
- **Adding a Test Scenario**: Add the scenario generator to `py/signals.py` under `make_scenario` and add its name to `SCENARIOS`.
