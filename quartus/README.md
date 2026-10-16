# Quartus Prime Lite Pipeline: Terasic DE2-115 (Cyclone IV E)

This directory provides the Quartus-specific hardware integration files for the **Terasic DE2-115 Development Board** featuring the **Altera/Intel Cyclone IV E EP4CE115F29C7** FPGA.

## Hardware Architecture & Design Principles

1. **Vendor-Neutral Core RTL**: The core signal processing logic remains in `rtl/anc_core.v` with no vendor IP, megafunctions, or proprietary primitives.
2. **Modular Board Wrapper**: Board-level pin multiplexing, Wolfson WM8731 audio codec configuration (I2C), and I2S serialization/deserialization reside in `anc_de2_115_top.v`.
3. **No Vivado Artifacts**: Vivado XDC constraints and Xilinx-specific modules have been completely excluded.

## Files
- `de2_115_pins.tcl`: Official pin assignment script for the DE2-115 board.
- `anc_de2_115_top.v`: Modular top-level wrapper interfacing WM8731 audio codec with `anc_core`.
- `README.md`: This integration and build guide.

## How to Compile in Quartus Prime Lite (Version 18.1 or newer)

Once Quartus Prime Lite is installed on your machine:

1. Open Quartus Prime Lite and create a project:
   - **Device**: Cyclone IV E `EP4CE115F29C7`
   - **Project Name**: `anc_fpga_de2115`
   - **Top-Level Entity**: `anc_de2_115_top`
2. Add RTL files:
   - `rtl/anc_core.v`
   - `quartus/anc_de2_115_top.v`
3. Apply pin assignments:
   - In Quartus, open `Tools -> Tcl Scripts...` and run `de2_115_pins.tcl`, or source it via Quartus Tcl Console:
     ```tcl
     source quartus/de2_115_pins.tcl
     ```
4. Compile the design:
   - Click **Start Compilation** (or run `quartus_sh --flow compile anc_fpga_de2115`).
5. Export reports into the ANC analysis pipeline:
   - Run the automated report parser:
     ```bash
     python py/import_quartus.py --fit-rpt output_files/anc_fpga_de2115.fit.rpt --sta-rpt output_files/anc_fpga_de2115.sta.rpt --algo nlms_shift --w 11
     ```
   - Or fill in `results/quartus/quartus_reports_template.csv` and regenerate figures via `python py/run_pipeline.py`.
