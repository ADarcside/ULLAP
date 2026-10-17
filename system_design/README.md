# System Design & Technical Specifications

This directory contains the comprehensive system engineering, architectural, algorithmic, and operational specifications for the **FPGA Adaptive Noise Cancellation (ANC)** project targeting the Terasic DE2-115 (Altera/Intel Cyclone IV E EP4CE115F29C7).

---

## Specification Documents

| Document | Topic | Description |
|---|---|---|
| [**`architecture.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/architecture.md) | **Hardware & System Architecture** | Board-level integration (WM8731 audio codec, I2S, I2C), single-multiplier DSP core datapath (`anc_core.v`), delay line and coefficient storage, parameter sizing, and Cyclone IV E FPGA resource utilization. |
| [**`pipeline.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/pipeline.md) | **Pipeline Specifications** | Multiplier 3-stage hardware pipeline, cycle-accurate multi-cycle execution schedule per audio sample ($LAT = L+3 / L+5$), and the complete 11-stage software simulation, characterization, and verification pipeline. |
| [**`algorithm.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/algorithm.md) | **Algorithms & Mathematics** | Mathematical derivations of LMS, NLMS, and NLMS-Shift (dividerless leading-one priority encoder + barrel shift), convergence bounds, stability proofs, and Q1.(W-1) fixed-point arithmetic rules. |
| [**`flowchart.md`**](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/system_design/flowchart.md) | **Operational Flowcharts** | Mermaid diagrams of top-level board initialization, ANC Core hardware FSM state transitions, algorithmic branch execution, fixed-point saturation/flag handling, and verification pipeline flow. |

---

## Directory Cross-References
- **RTL Source Code:** [`rtl/anc_core.v`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/rtl/anc_core.v), [`quartus/anc_de2_115_top.v`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/quartus/anc_de2_115_top.v)
- **Python Reference & Verification:** [`py/algos.py`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/py/algos.py), [`py/fixedpoint.py`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/py/fixedpoint.py), [`py/run_pipeline.py`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/py/run_pipeline.py), [`py/verify_core.py`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/py/verify_core.py)
- **Experimental Results & Plots:** [`results/research_summary.md`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/results/research_summary.md), [`results/plots/`](file:///c:/Users/Lenovo/OneDrive/Desktop/esa_proj/ULLAP/results/plots/)
